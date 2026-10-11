"""Audit four retained uploads; inaccessible TXT files are never substituted."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pandas as pd

from src.config import ROOT
from src.data.source_rights import RESTRICTED
from src.data.salimt_uploaded import normalize_profiles, normalize_values, propose_identities, identity_preview

RAW = ROOT / 'data/raw/sources/salimt_uploaded'
OUT = ROOT / 'data/processed/real'
FILE_IDS = {
    'team_details': 'file_00000000e2748210a8a2ba3d40b7df73',
    'team_competitions_seasons': 'file_000000006ac0820aaeee935144866dc3',
    'player_market_value': 'file_0000000051408210b8470d807790d192',
    'player_profiles': 'file_000000009f688243a036f40206d757aa',
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(paths=None):
    prior = json.loads((ROOT / 'reports/football_datasets_assessment.json').read_text())
    preserved = dict(prior['preserved_input_sha256'])
    preserved.update(prior['outputs_sha256'])
    for name in ['reports/football_datasets_assessment.json', 'reports/football_datasets_verification.json']:
        preserved[name] = sha(ROOT / name)
    for name, expected in preserved.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f'Previous evidence changed: {name}')
    RAW.mkdir(parents=True, exist_ok=True)
    receipt_path = RAW / 'receipt.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
    else:
        if not paths:
            raise ValueError('Supply four exact uploaded paths on first run')
        receipt = {'first_preserved_at_utc': datetime.now(timezone.utc).isoformat(),
                   'claimed_source_repository': 'https://github.com/salimt/football-datasets',
                   'source_commit_verified_for_uploads': False,
                   'licence_supplied': False, 'files': {}}
    tables = {}
    for name, file_id in FILE_IDS.items():
        target = RAW / (name + '.csv')
        if paths:
            incoming = Path(paths[name])
            if target.exists() and sha(target) != sha(incoming):
                raise ValueError(f'Retained raw bytes changed: {name}')
            if incoming.resolve() != target.resolve():
                shutil.copyfile(incoming, target)
        if not target.exists():
            raise ValueError(f'Raw upload missing: {name}')
        if target.read_bytes()[:120].startswith(b'version https://git-lfs.github.com/spec/v1'):
            raise ValueError(f'Git LFS pointer instead of CSV: {name}')
        expected = receipt['files'].get(name)
        if expected and sha(target) != expected['sha256']:
            raise ValueError(f'Raw checksum mismatch: {name}')
        receipt['files'][name] = {'file_id': file_id, 'sha256': sha(target),
                                  'path': str(target.relative_to(ROOT)), 'bytes': target.stat().st_size}
        tables[name] = pd.read_csv(target, low_memory=False,
                                   dtype={'player_id': str, 'club_id': str, 'current_club_id': str})
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    p = normalize_profiles(tables['player_profiles'])
    v = normalize_values(tables['player_market_value'], receipt['first_preserved_at_utc'])
    if not set(v.source_player_id) <= set(p.source_player_id):
        raise ValueError('Orphan valuation source IDs')
    s = tables['team_competitions_seasons']
    if s.competition_id.fillna('').ne(s.season_league_competition_id.fillna('')).any() or s.season_id.ne(s.season_league_season_id).any():
        raise ValueError('Competition/season context disagreement requires review')
    spain = s[s.competition_id.isin(['ES1', 'ES2']) & s.season_id.between(2020, 2025)].copy()
    if spain.duplicated(['club_id', 'competition_id', 'season_id']).any():
        raise ValueError('Ambiguous Spain team-season key')
    spain['season'] = spain.season_id.map(lambda year: f'{year}-{year+1}')
    spain['league'] = spain.competition_id.map({'ES1': 'La Liga', 'ES2': 'Segunda División'})
    spain['partial_season'] = spain.season_id.eq(2025)
    teams = tables['team_details'].copy()
    if teams.club_id.isna().any() or teams.club_id.duplicated().any():
        raise ValueError('Team details IDs must be unique')
    fb = pd.read_parquet(OUT / 'collected_player_seasons.parquet')
    mapping = pd.read_parquet(ROOT / 'data/external/worldfootballr/player_mapping.parquet')
    candidates = propose_identities(p, fb, mapping)
    for frame in [p, v, teams, spain, candidates]:
        frame['original_source'] = 'Transfermarkt.com'
        frame['source'] = 'salimt_user_uploaded_transfermarkt'
        frame['ml_use_status'] = RESTRICTED
        frame['use_authorized'] = False
        frame['model_use_eligible'] = False
        frame['first_observed_at_utc'] = pd.Timestamp(receipt['first_preserved_at_utc'])
        if 'identity_match_status' not in frame:
            frame['identity_match_status'] = 'unmatched'
    preview = identity_preview(fb, p, candidates)
    frames = {'profiles': p, 'values': v, 'team_details': teams, 'spain_team_seasons': spain,
              'identity_candidates': candidates, 'identity_join_preview': preview}
    outputs = {}
    for name, frame in frames.items():
        path = OUT / f'collected_salimt_{name}.parquet'
        frame.to_parquet(path, index=False)
        outputs[str(path.relative_to(ROOT))] = sha(path)
    # Corroborate earlier upload dates without changing its immutable evidence.
    old = pd.read_parquet(OUT / 'collected_kaggle_value_history.parquet')
    agreement = []
    for date_col in ['valuation_date_reported', 'valuation_date_one_day_earlier_hypothesis']:
        matched = old.merge(v[['source_player_id', 'valuation_date', 'market_value_eur']],
                             left_on=['source_player_id', date_col], right_on=['source_player_id', 'valuation_date'],
                             validate='one_to_one', suffixes=('_kaggle', '_salimt'))
        agreement.append({'kaggle_date_column': date_col, 'matched_date_rows': len(matched),
                          'equal_amount_rows': int(matched.market_value_eur_kaggle.eq(matched.market_value_eur_salimt).sum()),
                          'source_people': matched.source_player_id.nunique(),
                          'independent_provider_truth_verified': False})
    coverage = []
    for league, competition in [('La Liga', 'ES1'), ('Segunda División', 'ES2')]:
        for start in range(2020, 2026):
            selected = spain[spain.competition_id.eq(competition) & spain.season_id.eq(start)]
            for category in ['team_season_membership', 'player_performance', 'transfer_events', 'historical_profiles', 'historical_valuations']:
                observed = category == 'team_season_membership'
                coverage.append({'source': 'salimt_upload', 'league': league, 'season': f'{start}-{start+1}',
                                 'category': category, 'rows_observed': len(selected) if observed else None,
                                 'teams_observed': selected.club_id.nunique() if observed else None,
                                 'min_team_matches': selected.season_total_matches.min() if observed else None,
                                 'max_team_matches': selected.season_total_matches.max() if observed else None,
                                 'status': ('partial_2025_26' if start == 2025 else 'reported_team_season_records') if observed else
                                           ('upload_transfer_limit_blocked' if category in ['player_performance', 'transfer_events'] else 'historical_league_or_availability_unverified'),
                                 'model_use_eligible': False})
    for start in range(2020, 2026):
        selected = v[v.valuation_date.ge(f'{start}-07-01') & v.valuation_date.lt(f'{start+1}-07-01')]
        coverage.append({'source': 'salimt_upload', 'league': 'unassigned_global', 'season': f'{start}-{start+1}',
                         'category': 'valuation_events', 'rows_observed': len(selected),
                         'source_people': selected.source_player_id.nunique(),
                         'status': 'dated_records_without_historical_league_membership', 'model_use_eligible': False})
    for name, frame in [('coverage', pd.DataFrame(coverage)), ('date_corroboration', pd.DataFrame(agreement))]:
        path = ROOT / f'reports/salimt_uploaded_{name}.csv'
        frame.to_csv(path, index=False)
        outputs[str(path.relative_to(ROOT))] = sha(path)
    definitions = pd.read_csv(ROOT / 'reports/collected_data_dictionary.csv').drop_duplicates('field').set_index('field').description.to_dict()
    descriptions = {
        'source_player_id': 'Transfermarkt source person ID; not approved canonical identity.',
        'player_raw': 'Original profile name including source ID suffix.', 'player': 'Name with only its matching trailing source-ID annotation removed.',
        'date_of_birth_raw': 'Original ISO profile DOB string.', 'date_of_birth': 'Strictly parsed profile DOB, not a price date.',
        'birth_year': 'Year derived from DOB; identity evidence, no availability inference.',
        'height_raw_cm': 'Uploaded numeric height in cm; zero is an unknown sentinel.', 'height_cm': 'Positive finite height in cm; zero/nonfinite is missing.',
        'position_source': 'Provider position prose, retained without invented tactical labels.',
        'current_club_id': 'Current profile club ID; never historical stint membership.',
        'current_club_name': 'Current profile club text; never historical stint membership.',
        'main_position': 'Provider broad position group.', 'profile_temporal_scope': 'Current attributes with unknown original observation/publication time.',
        'valuation_date_raw': 'Original date_unix CSV field; actually ISO calendar text.',
        'valuation_date': 'Parsed uploader-reported event date; not primary-provider verified.',
        'market_value_eur': 'Reported EUR market assessment; not a transfer fee or project estimate.',
        'currency': 'EUR according to repository schema; original CSV has no currency column.',
        'reported_zero_value': 'Explicit reported zero with unverified semantics.',
        'valuation_known_at': 'First local retained receipt; does not establish past public availability.',
        'source_publication_known_at': 'Unknown original public availability timestamp.',
        'date_evidence_status': 'ISO event-date evidence from retained upload.',
        'historical_budget_eligible': 'False: no reviewed identity/use authorization and original availability unknown.',
        'source': 'Retained salimt upload route.', 'original_source': 'Uploader/repository-declared Transfermarkt provider.',
        'ml_use_status': 'Existing provider restriction retained.', 'use_authorized': 'False: no reviewed use licence supplied.',
        'model_use_eligible': 'False: isolated evidence, not a final model dataset.',
        'first_observed_at_utc': 'Local receipt UTC time, not source publication.',
        'identity_match_status': 'Unmatched or provisional_not_reviewed; no approvals.',
        'canonical_player_id_proposed': 'Proposed FBref-anchored person ID, not an approved mapping.',
        'fbref_id': 'FBref person ID from retained upstream map.', 'transfermarkt_id': 'Transfermarkt ID from retained upstream map.',
        'normalized_name_agreement': 'Profile name matches a retained FBref name alias.',
        'birth_year_agreement': 'Profile DOB year equals all known FBref birth years for this person.',
        'birth_year_conflict': 'Profile DOB year conflicts with retained FBref birth-year set.',
        'source_id_ambiguous': 'Multiple FBref candidates for one source ID.', 'fbref_id_ambiguous': 'Multiple source candidates for one FBref ID.',
        'supported_review_candidate': 'Name/year agreement and unambiguous upstream ID pair; still unreviewed.',
        'evidence_temporal_scope': 'Current profile/upstream-map evidence, not historical decision-time proof.',
        'mapping_source': 'Transfermarkt mapping attribution; blocks preview model use.',
        'partial_season': '2025/26 records are observed incomplete snapshots.',
    }
    dictionary = []
    for name, frame in frames.items():
        for column in frame:
            key = column.removeprefix('salimt_')
            desc = descriptions.get(key, definitions.get(key))
            if desc is None:
                desc = ('Provider-reported team-season field: ' if name == 'spain_team_seasons' else 'Provider-reported team detail: ') + key.replace('_', ' ') + '; retain source semantics and missingness.'
            dictionary.append({'table': name, 'field': column, 'dtype': str(frame[column].dtype),
                               'description': ('Provisional source-prefixed profile evidence: ' if column.startswith('salimt_') else '') + desc,
                               'model_use_eligible': False})
    path = ROOT / 'reports/salimt_uploaded_dictionary.csv'
    pd.DataFrame(dictionary).to_csv(path, index=False)
    outputs[str(path.relative_to(ROOT))] = sha(path)
    for name, expected in preserved.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f'Previous evidence changed during audit: {name}')
    summary = {'profiles': len(p), 'valuation_records': len(v), 'valuation_people': v.source_player_id.nunique(),
               'team_details': len(teams), 'global_team_seasons': len(s), 'spain_target_team_seasons': len(spain),
               'height_zero_sentinels': int(p.height_raw_cm.eq(0).sum()), 'dob_missing': int(p.date_of_birth.isna().sum()),
               'reported_zero_valuations': int(v.reported_zero_value.sum()),
               'valuation_date_range': [str(v.valuation_date.min().date()), str(v.valuation_date.max().date())],
               'global_exact_team_season_duplicates': int(s.duplicated().sum()),
               'global_duplicate_club_competition_season_rows': int(s.duplicated(['club_id', 'competition_id', 'season_id']).sum()),
               'identity_candidate_pairs': len(candidates), 'supported_review_pairs': int(candidates.supported_review_candidate.sum()),
               'birth_year_conflict_pairs': int(candidates.birth_year_conflict.sum()),
               'preview_rows': len(preview), 'preview_profile_attached_rows': int(preview.salimt_source_player_id.notna().sum()),
               'approved_identity_links': 0, 'eligible_historical_budgets': 0,
               'models_retrained': 0, 'transfer_and_performance_payloads_inspected': False}
    report = {'status': 'four_uploads_audited_review_only_join_prepared', 'receipt': receipt, 'summary': summary,
              'date_corroboration': agreement, 'outputs_sha256': outputs, 'preserved_input_sha256': preserved,
              'dataset_version': hashlib.sha256(json.dumps(receipt['files'], sort_keys=True).encode()).hexdigest(),
              'blocked_uploads': {'transfer_history.txt': '32 MiB executor transfer limit; content uninspected',
                                  'player_performances.txt': '32 MiB executor transfer limit; content uninspected'},
              'raw_counts_differ_from_readme': {'values': [901457, len(v)], 'team_seasons': [196378, len(s)]},
              'git_source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'git_source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
              'code_sha256': {n: sha(ROOT / n) for n in ['src/data/salimt_uploaded.py', 'scripts/salimt_uploaded_audit.py']},
              'limitations': ['licence and original availability unknown', 'no approved cross-source identities',
                              'team coverage is not player-statistics coverage', '2025/26 partial',
                              'valuation events have no historical club/league field',
                              'date agreement across derivative copies is not independent provider validation']}
    (ROOT / 'reports/salimt_uploaded_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in FILE_IDS:
        parser.add_argument('--' + key.replace('_', '-'), type=Path)
    args = vars(parser.parse_args())
    supplied = {k: v for k, v in args.items() if v is not None}
    if supplied and set(supplied) != set(FILE_IDS):
        parser.error('Provide all four upload paths together')
    run(supplied or None)
