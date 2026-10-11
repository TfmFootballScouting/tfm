"""Verify the offline valuation audit, preserved inputs and actual test outcomes."""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.config import ROOT
from src.data.provenance import sha256
from src.data.valuations import header_valuation_evidence, select_recorded_values


def run():
    audit = json.loads((ROOT/'reports/valuation_audit.json').read_text())
    for records in [audit['preserved_input_hashes'], audit['code_hashes'], audit['outputs']]:
        for path, expected in records.items():
            if sha256(ROOT/path) != expected:
                raise ValueError('Changed valuation audit evidence: '+path)
    observations = pd.read_parquet(ROOT/'data/processed/real/collected_valuation_header_evidence.parquet')
    dated = pd.read_parquet(ROOT/'data/processed/real/collected_dated_valuation_evidence.parquet')
    values = pd.read_parquet(ROOT/'data/processed/real/collected_valuation_record_audit.parquet')
    candidates = pd.read_parquet(ROOT/'data/processed/real/collected_current_value_identity_candidates.parquet')
    provenance = {r['sha256']: r for r in [json.loads(line) for line in (ROOT/'data/raw/provenance.jsonl').read_text().splitlines()]
                  if r.get('category') in ['profiles', 'historical_valuations', 'transfer_history'] and r.get('http_status') == 200}
    for observation in observations.itertuples():
        record = provenance[observation.snapshot_sha256]
        parsed = header_valuation_evidence((ROOT/record['path']).read_text(), record)
        for key in ['source_player_id', 'market_value_eur', 'valuation_date', 'valuation_known_at']:
            if getattr(observation, key) != parsed[key]:
                raise ValueError('Raw-header replay differs: '+key)
    if len(observations) != audit['parsed_header_observations'] or len(dated) != audit['distinct_dated_current_values']:
        raise ValueError('Header observation/event counts disagree')
    if len(values) != audit['archive_rows']+audit['current_sample_rows']:
        raise ValueError('Valuation audit row count changed')
    archived = values[values.dataset.eq('season_labelled_archive')]
    source = pd.read_parquet(ROOT/'data/processed/real/collected_profiles_valuations.parquet')
    paired = archived.merge(source[['record_id','market_value_eur']], on='record_id', suffixes=('_audit','_source'), validate='one_to_one')
    if len(paired) != len(source) or not np.allclose(paired.market_value_eur_audit, paired.market_value_eur_source, equal_nan=True):
        raise ValueError('Recorded archive amounts were modified')
    if archived.valuation_date.notna().any() or archived.valuation_known_at.notna().any():
        raise ValueError('Current dates leaked into historical archive records')
    if values.eligible_for_historical_budget.any() or values.identity_verified.any() or values.use_authorized.any():
        raise ValueError('Unsupported eligibility or approval claimed')
    if candidates.eligible_for_attachment.any() or not candidates.identity_match_status.eq('provisional_not_reviewed').all():
        raise ValueError('Current matching proposals incorrectly approved')
    for record in audit['cutoff_eligibility']:
        if len(select_recorded_values(values, record['cutoff'])) != record['eligible_person_values']:
            raise ValueError('As-of eligibility replay differs')
        dates = values.explicit_dates_present & values.valuation_date.le(pd.Timestamp(record['cutoff'])) & values.valuation_known_at.le(pd.Timestamp(record['cutoff']))
        if dates.sum() != record['dated_and_observed_by_cutoff_rows']:
            raise ValueError('Date-only availability count differs')
    counts = {key: sum(int(suite.attrib.get(key, 0)) for suite in ET.parse(ROOT/'reports/valuation_audit_tests.xml').getroot().iter('testsuite'))
              for key in ['tests','failures','errors','skipped']}
    if not counts['tests'] or any(counts[key] for key in ['failures','errors','skipped']):
        raise ValueError('Required tests did not complete successfully')
    result = dict(status='passed', checked_at=datetime.now(timezone.utc).isoformat(),
        dataset_version=audit['dataset_version'], source_git_commit=audit['git_commit'], source_dirty=audit['git_source_dirty'],
        preserved_input_files=len(audit['preserved_input_hashes']), verified_output_files=len(audit['outputs']),
        replayed_raw_header_observations=len(observations), distinct_dated_current_values=len(dated),
        archived_amounts_unchanged=True, no_current_dates_backfilled=True,
        approved_identity_links=0, historical_budget_attachments=0, estimated_prices_generated=0,
        new_downloads=0, model_fitting_performed=False, tests=counts,
        historical_transfer_success_validated=False)
    (ROOT/'reports/valuation_audit_verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    run()
