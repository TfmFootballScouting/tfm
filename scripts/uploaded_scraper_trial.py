"""Audit the uploaded toolkit and retained access evidence; no stealth/cookies.

The optional new-source probe runs only after network settings are applied.
Transfermarkt data acquisition is disabled by its observed terms of use.
"""
import argparse
import ast
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from src.config import ROOT
from src.data.provenance import snapshot, sha256
from src.data.source_rights import TERMS_URL, TERMS_SHA256, RESTRICTED
from src.scraping.collect import Client, HOSTS, UA, AccessBlocked

UPLOAD_SHA256 = '8a47e63169071bcd8c1d2bc27929fb2c681e977bc6ee542a02d4f3b88a0afda1'
NEW_HOSTS = {
    'sofascore': 'https://www.sofascore.com',
    'whoscored': 'https://1xbet.whoscored.com',
    'opta': 'https://dataviz.theanalyst.com',
}
NEW_TARGETS = {
    'sofascore': '/api/v1/unique-tournament/54/seasons',
    'whoscored': '/matches/1946104/live/england-league-cup-2025-2026-tottenham-doncaster',
    'opta': '/opta-power-rankings/league-meta.json',
}


def audit_archive(path):
    if sha256(path) != UPLOAD_SHA256:
        raise ValueError('Uploaded toolkit checksum differs from reviewed archive')
    modules = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            member = Path(name)
            if member.is_absolute() or '..' in member.parts:
                raise ValueError('Unsafe archive path')
            if member.suffix != '.py':
                continue
            content = archive.read(name)
            tree = ast.parse(content)
            imports = sorted({node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} |
                             {item.name for node in ast.walk(tree) if isinstance(node, ast.Import) for item in node.names})
            modules.append(dict(path=member.relative_to(member.parts[0]).as_posix(),
                                sha256=hashlib.sha256(content).hexdigest(), syntax='valid', imports=imports))
        data_files = [name for name in archive.namelist()
                      if Path(name).suffix.lower() in ('.csv', '.parquet', '.rds', '.json', '.xlsx')]
    return dict(archive_sha256=UPLOAD_SHA256, python_modules=modules,
                bundled_data_files=data_files, execution='static AST inspection; original main routines were not executed')


def scorer_evidence(html, year):
    """Inspect a pre-policy-check sample without exporting player statistics."""
    soup = BeautifulSoup(html, 'lxml')
    label = f'{year % 100:02d}/{(year+1) % 100:02d}'
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    selected = soup.select_one('select[name=saison_id] option[selected]')
    if 'LaLiga2' not in title or label not in title or selected is None or selected.get('value') != str(year):
        raise ValueError('Requested Segunda season is not confirmed in the returned page')
    table = soup.select_one('table.items')
    if table is None:
        raise ValueError('Scorer table absent')
    headers = [node.get_text(' ', strip=True) or next(iter(node.select('[title]')), {}).get('title', '')
               for node in table.select('thead th')]
    ids = []
    for row in table.select(':scope > tbody > tr'):
        link = row.find('a', href=re.compile(r'/profil/spieler/\d+'))
        if link:
            ids.append(re.search(r'/spieler/(\d+)', link['href'])[1])
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Missing or duplicate player IDs in sample')
    advertised = [int(match[1]) for link in soup.select('.tm-pagination a[href]')
                  if (match := re.search(r'/page/(\d+)', link['href']))]
    return dict(title=title, verified_season=f'{year}-{year+1}', league='Segunda',
                sample_rows=len(ids), headers=headers, advertised_pages=max(advertised, default=1),
                pages_fetched=1, coverage='goalscorers first page; not all players or a complete season',
                ml_use_status=RESTRICTED, player_statistics_exported=False,
                age_warning='Age (today) column is not historical age; do not use as historical feature')


def probe_new_source(source):
    """One policy request per host, then at most one allowed diagnostic GET."""
    base = NEW_HOSTS[source]
    url = base + NEW_TARGETS[source]
    entry = dict(source=source, url=url, observed_at=datetime.now(timezone.utc).isoformat())
    client = Client()
    try:
        response = client.session.get(base + '/robots.txt', timeout=25)
        record = snapshot(response.content, source, base + '/robots.txt',
                          http_status=response.status_code, category='robots_uploaded_trial')
        entry['robots_record'] = record
        if response.status_code != 200:
            raise AccessBlocked(f'robots.txt unavailable: HTTP {response.status_code}; policy unknown')
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        if not parser.can_fetch(UA, url):
            raise AccessBlocked('robots.txt disallows diagnostic path')
        if source == 'whoscored':
            entry.update(status='out_of_scope_example', reason='Uploaded example is an English cup match; no match requested')
            return entry
        import time
        HOSTS[source] = base
        client.robots[base.split('//')[1]] = parser
        client.last[base.split('//')[1]] = time.monotonic()
        body, record = client.get(url, source, category='uploaded_toolkit_trial_diagnostic')
        payload = json.loads(body)
        entry.update(status='raw_diagnostic_only', record=record,
                     payload_type=type(payload).__name__, reason='Endpoint response is not complete historical player coverage')
    except (AccessBlocked, requests.RequestException, ValueError) as exc:
        reason = str(exc)
        entry.update(status='environment_network_blocked' if isinstance(exc, requests.exceptions.ProxyError)
                     or 'Tunnel connection failed' in reason else 'blocked_or_parse_failed', reason=reason)
    return entry


def run(path, probe=False):
    audit = audit_archive(path)
    raw = ROOT / 'data/raw/sources/uploaded_toolkit' / f'{UPLOAD_SHA256}.zip'
    if not raw.exists():
        snapshot(path.read_bytes(), 'uploaded_toolkit',
                 'sediment://file_00000000bc18820a9a089759e834829e', suffix='.zip',
                 category='user_supplied_reference_code', file_name=path.name)
    if sha256(raw) != UPLOAD_SHA256:
        raise ValueError('Retained uploaded archive checksum mismatch')
    records = [json.loads(line) for line in (ROOT / 'data/raw/provenance.jsonl').read_text().splitlines()]
    terms = next(r for r in records if r['sha256'] == TERMS_SHA256)
    if sha256(ROOT / terms['path']) != TERMS_SHA256:
        raise ValueError('Terms evidence checksum mismatch')
    sample = next(r for r in records if r.get('category') == 'uploaded_toolkit_trial'
                  and r.get('source') == 'transfermarkt' and r.get('http_status') == 200)
    if sha256(ROOT / sample['path']) != sample['sha256']:
        raise ValueError('Sample evidence checksum mismatch')
    audit['transfermarkt_evidence'] = dict(record=sample, **scorer_evidence((ROOT / sample['path']).read_bytes(), 2024))
    audit['rights'] = dict(source='transfermarkt', status=RESTRICTED, terms_url=TERMS_URL,
                          terms_record=terms, section='11.1',
                          quote='The User is not permitted to access or copy the Digital Content using bots, spiders, screen scraping or other automated processes.',
                          ml_quote='The user is also prohibited from using the digital content for the training or development of artificial intelligence (AI), including language models, machine learning, neural networks or other AI systems.',
                          reviewed_provider_license_available=False)
    access_path = ROOT / 'reports/uploaded_scraper_access.json'
    access = json.loads(access_path.read_text())
    if probe:
        access = [row for row in access if row['source'] not in NEW_HOSTS]
        access.extend(probe_new_source(source) for source in NEW_HOSTS)
        access_path.write_text(json.dumps(access, indent=2) + '\n')
    audit.update(access=access, generated_at=datetime.now(timezone.utc).isoformat(),
                 model_retrained=False, final_experiments_run=False,
                 original_network_and_browser_routines_executed=False,
                 safe_adaptations='Fixed research UA, source-ID/season checks, bounded requests, retained raw evidence; no cookies or stealth')
    (ROOT / 'reports/uploaded_scraper_trial.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(f'{len(audit["python_modules"])} modules parsed; {len(audit["bundled_data_files"])} bundled datasets')
    print(f'Segunda sample: {audit["transfermarkt_evidence"]["sample_rows"]} rows; ML use restricted by terms')
    print('No models trained; no synthetic fallback')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ROOT / 'data/raw/sources/uploaded_toolkit' / f'{UPLOAD_SHA256}.zip')
    parser.add_argument('--probe-new-sources', action='store_true', help='Only after network settings are applied; stop on denials')
    args = parser.parse_args()
    run(args.archive, args.probe_new_sources)
