"""Inspect pinned public documentation/tree metadata, never acquire provider CSVs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup
import pandas as pd
import requests

from src.config import ROOT
from src.data.source_rights import require_source_use, SourceUseRestricted

COMMIT = 'da9227e1f42baf74561324290dbf1ad2e3c00edd'
REPO = 'salimt/football-datasets'
RAW = ROOT / 'data/raw/sources/football_datasets_metadata'
FOLDERS = ['player_performances', 'player_market_value', 'player_profiles',
           'transfer_history', 'team_competitions_seasons', 'team_details']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_items(html, prefix):
    """Read GitHub's embedded directory JSON; never follow provider/data links."""
    items = {}
    def visit(obj):
        if isinstance(obj, dict):
            for item in obj.get('items', []) if isinstance(obj.get('items'), list) else []:
                if isinstance(item, dict) and str(item.get('path', '')).startswith(prefix):
                    items[item['path']] = item
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)
    for script in BeautifulSoup(html, 'html.parser').find_all('script', {'type': 'application/json'}):
        try:
            visit(json.loads(script.string or script.get_text()))
        except ValueError:
            continue
    return list(items.values())


def run():
    previous = json.loads((ROOT / 'reports/kaggle_value_audit.json').read_text())
    preserved = dict(previous['preserved_inputs_sha256'])
    preserved.update(previous['outputs_sha256'])
    for name in ['reports/kaggle_value_audit.json', 'reports/kaggle_value_verification.json']:
        preserved[name] = sha(ROOT / name)
    for name, expected in preserved.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f'Existing evidence changed: {name}')
    urls = {
        'readme': f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/README.md',
        'schema_examples': f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/README_data.md',
        'advertised_licence': f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/LICENSE',
        'git_attributes': f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/.gitattributes',
        'root_tree': f'https://github.com/{REPO}/tree/{COMMIT}',
    }
    urls.update({folder: f'https://github.com/{REPO}/tree/{COMMIT}/datalake/transfermarkt/{folder}'
                 for folder in FOLDERS})
    RAW.mkdir(parents=True, exist_ok=True)
    def fetch(pair):
        name, url = pair
        receipt_path, body_path = RAW / (name + '.json'), RAW / (name + '.response')
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            if receipt['url'] != url or sha(body_path) != receipt['sha256']:
                raise ValueError(f'Changed metadata evidence: {name}')
            return name, receipt, body_path.read_text()
        response = requests.get(url, timeout=30)
        if len(response.content) > 2_000_000:
            raise ValueError('Unexpectedly large metadata response')
        if response.status_code != 200 and not (name == 'advertised_licence' and response.status_code == 404):
            response.raise_for_status()
        body_path.write_bytes(response.content)
        receipt = {'url': url, 'status': response.status_code,
                   'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                   'sha256': sha(body_path), 'bytes': len(response.content),
                   'body_path': str(body_path.relative_to(ROOT))}
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
        return name, receipt, response.text
    results = list(ThreadPoolExecutor(max_workers=3).map(fetch, urls.items()))
    evidence = {name: receipt for name, receipt, body in results}
    bodies = {name: body for name, receipt, body in results}
    for token in ['92,671', '1,878,719', '901,457', '1,101,440', '196,378', '2,175']:
        if token not in bodies['schema_examples']:
            raise ValueError(f'Advertised count absent from pinned documentation: {token}')
    inventory = []
    for folder in FOLDERS:
        found = tree_items(bodies[folder], f'datalake/transfermarkt/{folder}/')
        if not found:
            raise ValueError(f'No actual files found in category: {folder}')
        for item in found:
            inventory.append({'category': folder, 'path': item['path'],
                              'kind': item.get('contentType'), 'commit': COMMIT,
                              'file_content_inspected': False})
    inventory_path = ROOT / 'reports/football_datasets_file_inventory.csv'
    pd.DataFrame(inventory).to_csv(inventory_path, index=False)
    schema_rows = []
    # Separate README-advertised schema evidence from verified file contents.
    declared = {'gls_p90': 'goals / (minutes_played / 90)',
                'ast_p90': 'assists / (minutes_played / 90)',
                'ga_p90': '(goals + assists) / (minutes_played / 90)'}
    for feature in ['gls_p90', 'ast_p90', 'ga_p90', 'sh_p90', 'sot_p90',
                    'crs_p90', 'int_p90', 'tklw_p90', 'fls_p90', 'fld_p90', 'xg_p90', 'xag_p90']:
        schema_rows.append({'feature': feature,
                            'status': 'potentially_derivable_from_advertised_schema' if feature in declared else 'not_in_advertised_schema',
                            'derivation_if_verified': declared.get(feature),
                            'actual_file_coverage_verified': False, 'model_use_eligible': False})
    schema_path = ROOT / 'reports/football_datasets_feature_assessment.csv'
    pd.DataFrame(schema_rows).to_csv(schema_path, index=False)
    try:
        require_source_use('transfermarkt', 'repository data acquisition')
    except SourceUseRestricted as exc:
        block = str(exc)
    else:
        raise ValueError('Expected source-use guard absent; review policy before acquisition')
    root_items = tree_items(bodies['root_tree'], '')
    report = {'repository_url': f'https://github.com/{REPO}', 'commit': COMMIT,
              'status': 'metadata_inspected_provider_data_acquisition_blocked',
              'source': 'Transfermarkt according to repository documentation',
              'metadata_evidence': evidence, 'root_items': root_items,
              'advertised_license_path_status': evidence['advertised_licence']['status'],
              'license_verified': False, 'reviewed_provider_license_available': False,
              'source_use_guard_result': block,
              'advertised_counts_not_independently_verified': {
                  'player_profiles': 92671, 'player_performances': 1878719,
                  'player_market_values': 901457, 'player_transfer_histories': 1101440,
                  'teams_competitions_seasons': 196378, 'teams_details': 2175},
              'advertised_date_fields': {'values': 'date_unix (ISO dates in README example)',
                                         'transfers': 'date and date_unformatted',
                                         'profiles': 'Date of birth, Joined, Contract expires'},
              'readme_paths_differ_from_actual_tree': True,
              'github_access_verified': True, 'uploaded_zip_accessible': False,
              'uploaded_zip_blocker': 'Sediment download exceeds executor 32 MiB transfer limit',
              'provider_csv_files_downloaded': 0, 'provider_csv_rows_inspected': 0,
              'documentation_schema_and_samples_inspected': True,
              'git_lfs_paths_declared': [line.split()[0] for line in bodies['git_attributes'].splitlines()
                                         if 'filter=lfs' in line],
              'uploaded_archive_reference': {'file_id': 'file_000000003ac081f4964a00e682633cdb',
                                             'filename': 'football-datasets-main (1).zip',
                                             'sha256': None, 'contents_verified': False},
              'source_league_season_coverage_verified': False,
              'segunda_presence': 'unverified', 'la_liga_presence': 'unverified',
              'model_fitting_performed': False, 'budget_attachment_performed': False,
              'identity_approval_performed': False, 'synthetic_fallback_used': False,
              'preserved_input_sha256': preserved,
              'code_sha256': {'scripts/football_datasets_inventory.py': sha(Path(__file__))},
              'outputs_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [inventory_path, schema_path]},
              'limitations': ['README totals are claims, not measured coverage',
                              'Provider permission and repository licence unverified',
                              'No full-core tactical or xG/xAG fields in advertised performance schema',
                              'A historical event date is not original public availability evidence',
                              'README source paths differ from actual pinned file tree']}
    for name, expected in preserved.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f'Existing evidence changed during inspection: {name}')
    (ROOT / 'reports/football_datasets_assessment.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'commit': COMMIT,
                      'metadata_responses_verified': len(evidence),
                      'actual_csv_paths_confirmed': len(inventory),
                      'provider_csv_files_downloaded': 0,
                      'preserved_inputs_verified': len(preserved),
                      'licence_link_http_status': report['advertised_license_path_status']}, indent=2))


if __name__ == '__main__':
    run()
