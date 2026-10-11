"""Verify offline uploaded-file audit, replay, unchanged inputs and test evidence."""
import hashlib
import json
from datetime import datetime, timezone
from xml.etree import ElementTree

import pandas as pd

from src.config import ROOT
from src.data.kaggle_values import read_archive, audit_tables
from scripts.kaggle_value_audit import ARCHIVE_SHA256, RAW


def run():
    manifest = json.loads((ROOT / 'reports/kaggle_value_audit.json').read_text())
    for field in ['members_sha256', 'outputs_sha256', 'preserved_inputs_sha256', 'code_sha256']:
        for name, expected in manifest[field].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    assert hashlib.sha256((RAW / (ARCHIVE_SHA256 + '.zip')).read_bytes()).hexdigest() == ARCHIVE_SHA256
    receipt = json.loads((RAW / 'receipt.json').read_text())
    assert receipt == manifest['receipt']
    p, h, dictionary, raw = read_archive(RAW / (ARCHIVE_SHA256 + '.zip'), ARCHIVE_SHA256)
    p, h, checks, diagnostics = audit_tables(p, h, receipt['first_inspected_at_utc'])
    for name, frame in [('profiles', p), ('history', h), ('summary_consistency', checks)]:
        stored = pd.read_parquet(ROOT / f'data/processed/real/collected_kaggle_value_{name}.parquet')
        # Parquet normalizes object-column NA sentinels to None; compare missing
        # semantics consistently without loosening checks on observed values.
        for column in frame.select_dtypes(include='object'):
            frame[column] = frame[column].where(frame[column].notna(), None)
            stored[column] = stored[column].where(stored[column].notna(), None)
        pd.testing.assert_frame_equal(frame, stored)
    for key, value in diagnostics.items():
        # JSON represents integer-valued dictionary keys as strings.
        assert json.loads(json.dumps(value)) == manifest['diagnostics'][key], key
    coverage = pd.read_csv(ROOT / 'reports/kaggle_value_coverage.csv')
    assert len(coverage) == 36
    assert coverage.historical_budget_eligible_rows.eq(0).all()
    assert coverage.loc[coverage.league_label.eq('Segunda División'), 'valuation_rows_reported_date'].eq(0).all()
    for table in ['identity_review', 'upstream_identity_candidates']:
        packet = pd.read_parquet(ROOT / f'data/processed/real/collected_kaggle_value_{table}.parquet')
        assert packet.identity_match_status.eq('provisional_not_reviewed').all()
        assert not packet.historical_budget_eligible.any() and not packet.model_use_eligible.any()
        assert not packet.source_use_authorized.any()
    definitions = pd.read_csv(ROOT / 'reports/kaggle_value_dictionary.csv')
    for table in ['profiles', 'history', 'summary_consistency', 'identity_review', 'upstream_identity_candidates']:
        frame = pd.read_parquet(ROOT / f'data/processed/real/collected_kaggle_value_{table}.parquet')
        assert set(definitions.loc[definitions.table.eq(table), 'column']) == set(frame), table
    xml = ElementTree.parse(ROOT / 'reports/kaggle_value_tests.xml')
    suites = list(xml.getroot().iter('testsuite'))
    counts = {k: sum(int(s.get(k, 0)) for s in suites) for k in ['tests', 'failures', 'errors', 'skipped']}
    assert counts['tests'] > 68 and not any(counts[k] for k in ['failures', 'errors', 'skipped'])
    names = [x.get('name') for x in xml.getroot().iter('testcase')]
    assert 'test_real_uploaded_dates_are_preserved_and_quarantined' in names
    report = {'status': 'passed', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'dataset_version': manifest['dataset_version'], 'tests': counts,
              'preserved_files_verified': len(manifest['preserved_inputs_sha256']),
              'outputs_verified': len(manifest['outputs_sha256']),
              'raw_zip_and_four_members_verified': True,
              'normalized_tables_replayed': ['profiles', 'history', 'summary_consistency'],
              'approved_identity_links': 0, 'eligible_historical_budget_records': 0,
              'model_training_performed': False, 'synthetic_fallback_used': False,
              'limitations': ['provider use licence absent', 'one-day date discrepancy unresolved',
                             'historical public availability unknown', 'biased current-league sample',
                             'source authenticity not independently verified']}
    (ROOT / 'reports/kaggle_value_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
