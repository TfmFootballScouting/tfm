"""Polite, conservative collection. No CAPTCHA or access-control bypass.

Breakout inspired source IDs, source-separated caching and season URL construction;
this implementation deliberately avoids its stealth browser and 403 retries.
"""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment

from src.config import ROOT
from src.data.provenance import snapshot

SEASONS = [f'{y}-{y+1}' for y in range(2020, 2026)]
CATEGORIES = {
    'fbref': ['standard', 'shooting', 'passing', 'defense', 'possession', 'misc'],
    'understat': ['players_xg_xa'],
    'transfermarkt': ['market_values', 'profiles', 'historical_valuations', 'transfer_history', 'fees'],
}
HOSTS = {'fbref': 'https://fbref.com', 'understat': 'https://understat.com',
         'transfermarkt': 'https://www.transfermarkt.com'}
UA = 'TFMScoutingResearch/1.0 (academic; cached; no access bypass)'


class AccessBlocked(RuntimeError):
    pass


class Client:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = UA
        self.robots = {}
        self.last = {}
        self.denied = {}
        self.cached = {}
        manifest = ROOT / 'data/raw/provenance.jsonl'
        if manifest.exists():
            for line in manifest.read_text().splitlines():
                item = json.loads(line)
                if item.get('http_status') == 200 and item.get('category') != 'robots':
                    self.cached[item['url']] = item

    def get(self, url, source, **metadata):
        host = urlsplit(url).netloc
        if host in self.denied:
            raise AccessBlocked(self.denied[host])
        if host not in self.robots:
            robots_url = HOSTS[source] + '/robots.txt'
            try:
                r = self.session.get(robots_url, timeout=25)
                self.last[host] = time.monotonic()
                snapshot(r.content, source, robots_url, http_status=r.status_code, category='robots')
                if r.status_code != 200:
                    self.denied[host] = f'robots.txt unavailable: HTTP {r.status_code}; policy unknown'
                    raise AccessBlocked(self.denied[host])
                parser = RobotFileParser()
                parser.parse(r.text.splitlines())
                self.robots[host] = parser
            except requests.RequestException as exc:
                self.denied[host] = f'Network/access error checking robots.txt: {exc}'
                raise AccessBlocked(self.denied[host]) from exc
        parser = self.robots[host]
        if not parser.can_fetch(UA, url):
            raise AccessBlocked('robots.txt disallows this path for the research client')
        if url in self.cached:
            record = self.cached[url]
            path = ROOT / record['path']
            if path.exists():
                import hashlib
                if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
                    raise ValueError('Raw cache checksum mismatch')
                return path.read_text(encoding='utf8'), record
        delay = max(3, parser.crawl_delay(UA) or 0)
        time.sleep(max(0, delay - (time.monotonic() - self.last.get(host, 0))))
        try:
            r = self.session.get(url, timeout=30)
            self.last[host] = time.monotonic()
            record = snapshot(r.content, source, url, http_status=r.status_code, **metadata)
            if r.status_code in (401, 403, 429):
                self.denied[host] = f'HTTP {r.status_code}; stop, no retry or bypass'
                raise AccessBlocked(self.denied[host])
            r.raise_for_status()
            if any(x in r.text.lower() for x in ('verify you are human', 'cf-chl-', 'captcha')):
                self.denied[host] = 'Access challenge; stop, no bypass'
                raise AccessBlocked(self.denied[host])
            self.cached[url] = record
            return r.text, record
        except requests.RequestException as exc:
            raise AccessBlocked(f'HTTP/network request failed: {exc}') from exc


def parse_understat(html):
    match = re.search(r"playersData\s*=\s*JSON\.parse\('((?:\\.|[^'])*)'\)", html)
    if not match:
        raise ValueError('playersData JSON absent; JavaScript-only response not bypassed')
    # Decode JS hex escapes without damaging UTF-8 names.
    raw = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), match[1])
    raw = raw.replace("\\'", "'")
    rows = json.loads(raw)
    if not isinstance(rows, list) or not rows:
        raise ValueError('Empty or malformed playersData')
    return pd.DataFrame(rows)


def parse_fbref(html, category):
    soup = BeautifulSoup(html, 'lxml')
    for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
        if '<table' in str(comment):
            soup.append(BeautifulSoup(str(comment), 'lxml'))
    table = soup.find('table', id='stats_' + category)
    if table is None:
        raise ValueError(f'stats_{category} table absent')
    rows = []
    for tr in table.select('tbody tr'):
        player = tr.find(['th', 'td'], attrs={'data-stat': 'player'})
        link = player.find('a', href=re.compile('/players/')) if player else None
        if not link:
            continue
        values = {c['data-stat']: c.get_text(strip=True) for c in tr.find_all(['th', 'td']) if c.get('data-stat')}
        values['source_player_id'] = link['href'].split('/players/')[1].split('/')[0]
        rows.append(values)
    if not rows:
        raise ValueError('No player rows parsed')
    return pd.DataFrame(rows)


def collect():
    client = Client()
    coverage = []
    root = ROOT / 'data/external'
    root.mkdir(parents=True, exist_ok=True)
    for source, cats in CATEGORIES.items():
        for league in ['La Liga', 'Segunda']:
            for season in SEASONS:
                for category in cats:
                    row = dict(source=source, league=league, season=season, category=category,
                               rows=0, status='unrun', reason='', retrieved_at=datetime.now(timezone.utc).isoformat())
                    if source == 'understat' and league == 'Segunda':
                        row.update(status='unavailable', reason='Understat does not cover Segunda')
                    elif source == 'transfermarkt':
                        row.update(status='unrun', reason='Historical player endpoints require validated dates/season membership; current snapshots are not history')
                        if category == 'market_values':
                            url = f"{HOSTS[source]}/{'laliga' if league == 'La Liga' else 'laliga2'}/marktwerte/wettbewerb/{'ES1' if league == 'La Liga' else 'ES2'}/saison_id/{season[:4]}"
                            row['url'] = url
                            try:
                                client.get(url, source, league=league, season=season, category='market_values_access_probe')
                                row.update(status='historical_unverified',reason='Response preserved; historical URL alone does not establish valuation effective date or historical roster')
                            except AccessBlocked as exc:
                                row.update(status='blocked', reason=str(exc))
                    else:
                        if source == 'understat':
                            url = f'{HOSTS[source]}/league/La_liga/{season[:4]}'
                        else:
                            comp = '12' if league == 'La Liga' else '17'
                            slug = 'La-Liga' if league == 'La Liga' else 'Segunda-Division'
                            section = '' if category == 'standard' else category + '/'
                            url = f'{HOSTS[source]}/en/comps/{comp}/{season}/{section}{season}-{slug}-Stats'
                        row['url'] = url
                        try:
                            html, record = client.get(url, source, league=league, season=season, category=category)
                            frame = parse_understat(html) if source == 'understat' else parse_fbref(html, category)
                            frame['source'] = source
                            frame['league'] = league
                            frame['season'] = season
                            frame['snapshot_sha256'] = record['sha256']
                            path = root / source / f'{league.replace(" ", "_")}_{season}_{category}.csv'
                            path.parent.mkdir(parents=True, exist_ok=True)
                            frame.to_csv(path, index=False)
                            row.update(status='collected', rows=len(frame), sha256=record['sha256'])
                        except AccessBlocked as exc:
                            row.update(status='blocked', reason=str(exc))
                        except (ValueError, KeyError) as exc:
                            row.update(status='parse_failed', reason=str(exc))
                    coverage.append(row)
    pd.DataFrame(coverage).to_csv(ROOT / 'reports/source_coverage.csv', index=False)
    return pd.DataFrame(coverage)


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(collect().groupby(['source', 'status']).size())
