"""Check raw preservation, dictionary, review-only joins, real tests and replay."""
from datetime import datetime, timezone
import json
from xml.etree import ElementTree
import pandas as pd
from src.config import ROOT
from src.data.salimt_uploaded import normalize_profiles, normalize_values
from scripts.salimt_uploaded_audit import RAW, sha


def run():
    report = json.loads((ROOT / 'reports/salimt_uploaded_audit.json').read_text())
    for group in ['preserved_input_sha256', 'outputs_sha256', 'code_sha256']:
        for name, expected in report[group].items():
            assert sha(ROOT / name) == expected, name
    receipt = json.loads((RAW / 'receipt.json').read_text())
    assert receipt == report['receipt']
    for item in receipt['files'].values():
        assert sha(ROOT / item['path']) == item['sha256']
    p = normalize_profiles(pd.read_csv(RAW / 'player_profiles.csv', dtype={'player_id': str, 'current_club_id': str}, low_memory=False))
    v = normalize_values(pd.read_csv(RAW / 'player_market_value.csv', dtype={'player_id': str}), receipt['first_preserved_at_utc'])
    for name, expected in [('profiles', p), ('values', v)]:
        actual = pd.read_parquet(ROOT / f'data/processed/real/collected_salimt_{name}.parquet')
        actual = actual[list(expected)].copy()
        for column in expected.select_dtypes(include='object'):
            expected[column] = expected[column].where(expected[column].notna(), None)
            actual[column] = actual[column].where(actual[column].notna(), None)
        pd.testing.assert_frame_equal(actual, expected)
    dictionary = pd.read_csv(ROOT / 'reports/salimt_uploaded_dictionary.csv')
    names = ['profiles', 'values', 'team_details', 'spain_team_seasons', 'identity_candidates', 'identity_join_preview']
    for name in names:
        table = pd.read_parquet(ROOT / f'data/processed/real/collected_salimt_{name}.parquet')
        assert set(table) == set(dictionary.loc[dictionary.table.eq(name), 'field']), name
        assert not table.model_use_eligible.any()
    coverage = pd.read_csv(ROOT / 'reports/salimt_uploaded_coverage.csv')
    clubs = coverage[coverage.category.eq('team_season_membership')]
    assert len(clubs) == 12
    assert clubs.loc[clubs.league.eq('La Liga'), 'teams_observed'].eq(20).all()
    assert clubs.loc[clubs.league.eq('Segunda División'), 'teams_observed'].eq(22).all()
    for category in ['player_performance', 'transfer_events']:
        assert coverage.loc[coverage.category.eq(category), 'rows_observed'].isna().all()
    fb = pd.read_parquet(ROOT / 'data/processed/real/collected_player_seasons.parquet')
    preview = pd.read_parquet(ROOT / 'data/processed/real/collected_salimt_identity_join_preview.parquet')
    for key in ['observation_id', 'player_id', 'entity_id', 'season', 'team', 'market_value_eur']:
        pd.testing.assert_series_equal(fb[key], preview[key])
    xml = ElementTree.parse(ROOT / 'reports/salimt_uploaded_tests.xml')
    suites = list(xml.getroot().iter('testsuite'))
    counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
    assert counts['tests'] > 74 and not any(counts[k] for k in ['failures', 'errors', 'skipped'])
    assert any('test_preview_preserves_seasons' in t.get('name', '') for t in xml.getroot().iter('testcase'))
    result = {'status': 'passed', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'dataset_version': report['dataset_version'], 'tests': counts,
              'raw_uploads_verified': 4, 'old_inputs_preserved': len(report['preserved_input_sha256']),
              'outputs_verified': len(report['outputs_sha256']), 'source_tables_replayed': ['profiles', 'values'],
              'fbref_observation_grain_preserved': True, 'historical_prices_backfilled': False,
              'approved_identities': 0, 'model_training_performed': False,
              'blocked_uploads': report['blocked_uploads'], 'limitations': report['limitations']}
    (ROOT / 'reports/salimt_uploaded_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    run()
