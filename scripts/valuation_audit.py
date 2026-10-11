"""Audit retained price/date/identity evidence offline, without fitting models."""
import hashlib
import json
import platform
import re
import subprocess

import pandas as pd
import pyreadr
from bs4 import BeautifulSoup

from src.config import ROOT, SEASONS
from src.data.provenance import sha256
from src.data.valuations import (audit_retained_values, consolidate_header_evidence,
    current_profile_identity_candidates, header_valuation_evidence, select_recorded_values)
from src.preprocessing.collected import data_dictionary


def verified_inputs():
    manifest = json.loads((ROOT/'reports/collected_preprocessing.json').read_text())
    identity = json.loads((ROOT/'reports/identity_resolution.json').read_text())
    previous = json.loads((ROOT/'reports/collected_validation_results.json').read_text())
    original = json.loads((ROOT/'reports/collected_model_verification.json').read_text())
    preserved = {**previous['preserved_input_hashes'], **original['preserved_application_and_raw_files']}
    for info in previous['experiments'].values():
        preserved.update(info['output_files'])
    for name in ['collected_model_notebook_execution', 'collected_validation_notebook_execution']:
        record = json.loads((ROOT/f'reports/{name}.json').read_text())
        preserved[record['notebook']] = record['sha256']
    for name in ['collected_preprocessing', 'identity_resolution', 'collected_model_results',
                 'collected_validation_results', 'source_rights']:
        path = f'reports/{name}.json'
        preserved[path] = sha256(ROOT/path)
    for record in identity['outputs'].values():
        preserved[record['path']] = record['sha256']
    tables = {name: pd.read_parquet(ROOT/manifest['outputs'][name]['path']) for name in [
        'collected_profiles_valuations', 'collected_current_market', 'collected_player_seasons']}
    tables['identity_crosswalk_proposed'] = pd.read_parquet(ROOT/identity['outputs']['identity_crosswalk_proposed']['path'])
    tables['identity_match_trials'] = pd.read_parquet(ROOT/identity['outputs']['identity_match_trials']['path'])
    provenance = ROOT/'data/raw/provenance.jsonl'
    preserved[provenance.relative_to(ROOT).as_posix()] = sha256(provenance)
    snapshots = []
    seen = set()
    for line in provenance.read_text().splitlines():
        item = json.loads(line)
        if item.get('source') == 'transfermarkt' and item.get('http_status') == 200 and item.get('category') in [
                'profiles', 'historical_valuations', 'transfer_history'] and item['sha256'] not in seen:
            path = (ROOT/item['path']).resolve()
            if not path.is_relative_to(ROOT/'data/raw/sources'):
                raise ValueError('Raw evidence path escapes retained source directory')
            snapshots.append(item); seen.add(item['sha256'])
            preserved[item['path']] = item['sha256']
    for path, expected in preserved.items():
        if sha256(ROOT/path) != expected:
            raise ValueError(f'Changed source/model/provenance evidence: {path}')
    return manifest, identity, tables, snapshots, preserved


def run():
    manifest, identity, tables, snapshots, preserved = verified_inputs()
    records, page_audit = [], []
    for snapshot in snapshots:
        html = (ROOT/snapshot['path']).read_text()
        soup = BeautifulSoup(html, 'lxml')
        graph = soup.select_one('tm-market-value-development-graph-extended')
        try:
            record = header_valuation_evidence(html, snapshot)
            records.append(record)
            status, reason = 'explicit_current_value_date_parsed', 'Header last-update date; no historical series inferred'
        except ValueError as exc:
            status, reason = 'unsupported_header', str(exc)
        page_audit.append(dict(source_player_id=str(snapshot['source_player_id']),
            category=snapshot['category'], snapshot_sha256=snapshot['sha256'],
            header_status=status, reason=reason,
            history_component_present=graph is not None,
            historical_series_extracted=False))
    evidence = pd.DataFrame(records)
    if evidence.empty:
        raise ValueError('No explicit dated header evidence; do not invent valuations')
    dated = consolidate_header_evidence(evidence)
    current_candidates = current_profile_identity_candidates(dated, tables['collected_player_seasons'])
    archive = tables['collected_profiles_valuations']
    current = tables['collected_current_market'].copy()
    current['record_id'] = [hashlib.sha256(f'{r.snapshot_sha256}|{r.source_player_id}'.encode()).hexdigest()[:24]
                            for r in current.itertuples()]
    audited = audit_retained_values(archive, current, dated, tables['identity_crosswalk_proposed'])
    # A supported name/year proposal is audit evidence, not a reviewed identity.
    proposed = current_candidates[current_candidates.proposal_status.eq('current_name_birth_year_supported')]
    if proposed.source_player_id.duplicated().any():
        raise ValueError('Current profile candidate is ambiguous')
    candidate_map = proposed.set_index('source_player_id').canonical_player_id
    mask = audited.dataset.eq('current_market_sample') & audited.source_player_id.isin(candidate_map.index)
    audited.loc[mask, 'canonical_player_id'] = audited.loc[mask, 'source_player_id'].map(candidate_map)
    audited.loc[mask, 'identity_match_status'] = 'provisional_not_reviewed'
    # Recompute blocking explanation after adding current-only audit proposals.
    audited['valuation_blockers'] = [json.dumps(
        (['amount_missing_or_invalid'] if not r.amount_present else [])+
        (['effective_or_known_at_date_missing'] if not r.explicit_dates_present else [])+
        (['identity_not_reviewed'] if pd.notna(r.canonical_player_id) else ['identity_unmatched'])+
        ['source_use_restricted']) for r in audited.itertuples()]
    cutoff_rows, coverage = [], []
    for season in SEASONS:
        cutoff = pd.Timestamp(season[5:]+'-06-30', tz='UTC')
        dates_ok = audited.explicit_dates_present & audited.valuation_date.le(cutoff) & audited.valuation_known_at.le(cutoff)
        selected = select_recorded_values(audited, cutoff)
        cutoff_rows.append(dict(season=season, cutoff=cutoff.isoformat(),
            recorded_amount_rows=int(audited.amount_present.sum()),
            explicit_date_rows=int(audited.explicit_dates_present.sum()),
            dated_and_observed_by_cutoff_rows=int(dates_ok.sum()), eligible_person_values=len(selected)))
        fb = tables['collected_player_seasons']
        fb_season = fb[fb.season.eq(season)]
        values = audited[audited.dataset.eq('season_labelled_archive') & audited.season.eq(season)]
        ids = set(values.canonical_player_id.dropna())
        ids_with_amount = set(values.loc[values.amount_present, 'canonical_player_id'].dropna())
        coverage.append(dict(source='transfermarkt_archive', league='La Liga', season=season,
            source_records=len(values), source_people=int(values.source_player_id.nunique()),
            recorded_amount_rows=int(values.amount_present.sum()),
            explicit_date_rows=int(values.explicit_dates_present.sum()),
            fbref_player_seasons=len(fb_season), fbref_people_with_proposed_value_context=int(fb_season.entity_id.isin(ids).sum()),
            fbref_people_with_proposed_nonmissing_value=int(fb_season.entity_id.isin(ids_with_amount).sum()),
            verified_identity_links=0, eligible_budget_attachments=0))
        coverage.append(dict(source='transfermarkt_archive', league='Segunda', season=season,
            source_records=0, source_people=0, recorded_amount_rows=0, explicit_date_rows=0,
            fbref_player_seasons=0, fbref_people_with_proposed_value_context=0,
            fbref_people_with_proposed_nonmissing_value=0, verified_identity_links=0, eligible_budget_attachments=0))
    coverage = pd.DataFrame(coverage)
    latest = tables['identity_match_trials']
    latest = latest[latest.right_source.eq('transfermarkt') & latest.season_cutoff.eq(identity['latest_cutoff'])].copy()
    latest = latest.rename(columns={'left_id': 'fbref_source_player_id', 'right_id': 'valuation_source_player_id'})
    latest['identity_match_status'] = 'provisional_not_reviewed'
    latest['human_review_completed'] = False
    # Inspect the preserved raw R object, not merely the normalized date columns.
    raw_snapshot = next(item for item in manifest['source_snapshots'] if item['category'] == 'valuations')
    raw = next(iter(pyreadr.read_r(str(ROOT/raw_snapshot['path'])).values()))
    raw_date_fields = [field for field in raw if any(word in field.lower() for word in ['date', 'dob', 'contract', 'season'])]
    valuation_date_fields = [field for field in raw if re.search(r'(?:valuation|market.*value).*(?:date|time)|known.*at|last.*update', field, re.I)]
    if valuation_date_fields:
        raise ValueError('Additional raw valuation date fields need explicit interpretation before reporting missing dates')
    date_field_audit = pd.DataFrame([dict(raw_field=field, raw_dtype=str(raw[field].dtype),
        nonmissing_raw_rows=int(raw[field].notna().sum()),
        role='Birth date' if field == 'player_dob' else 'Club joining date' if field == 'date_joined'
        else 'Contract end date' if field == 'contract_expiry' else 'Season label',
        establishes_valuation_effective_date=False, establishes_valuation_known_at=False) for field in raw_date_fields])
    outputs = dict(collected_valuation_record_audit=audited,
        collected_valuation_header_evidence=evidence, collected_dated_valuation_evidence=dated,
        collected_current_value_identity_candidates=current_candidates)
    paths = []
    for name, frame in outputs.items():
        path = ROOT/f'data/processed/real/{name}.parquet'
        frame.to_parquet(path, index=False); paths.append(path)
    csvs = dict(valuation_record_audit=audited, valuation_header_page_audit=pd.DataFrame(page_audit),
        valuation_dated_current_evidence=dated, valuation_current_identity_candidates=current_candidates,
        valuation_identity_review_queue=latest, valuation_source_season_coverage=coverage,
        valuation_cutoff_eligibility=pd.DataFrame(cutoff_rows), valuation_raw_date_fields=date_field_audit)
    for name, frame in csvs.items():
        path = ROOT/f'reports/{name}.csv'
        frame.to_csv(path, index=False); paths.append(path)
    dictionary = data_dictionary(outputs)
    descriptions = dict(valuation_date='Explicit source-header last-update date for two current values; never a season-derived date',
        valuation_known_at='Conservative first retained header observation; original historical publication date is not proved',
        requested_league_context='Source request context; not independently verified current player league membership',
        canonical_player_id='FBref person ID from a provisional audit proposal; not reviewed approval',
        amount_present='Finite nonnegative source-reported monetary amount exists',
        explicit_dates_present='Both explicit effective date and conservative observation date exist',
        identity_match_status='Unmatched or provisional; never auto-approved',
        eligible_for_historical_budget='False: incomplete dates, identity review and/or source-use authorization',
        use_authorized='False for retained restricted source assets',
        valuation_blockers='JSON list of independent missing-evidence/use reasons',
        value_kind='Source-reported market assessment, not actual transfer fee',
        evidence_snapshot_hashes='JSON list of corroborating raw header snapshots; repeats are not new price events')
    dictionary['description'] = dictionary.field.map(descriptions).fillna(dictionary.description)
    dictionary_path = ROOT/'reports/valuation_audit_dictionary.csv'
    dictionary.to_csv(dictionary_path, index=False); paths.append(dictionary_path)
    code_paths = ['src/data/valuations.py', 'scripts/valuation_audit.py', 'src/data/source_rights.py',
                  'src/scraping/transfermarkt.py', 'scripts/verify_valuation_audit.py']
    code = {path: sha256(ROOT/path) for path in code_paths}
    version = hashlib.sha256(json.dumps(dict(inputs=preserved, code=code), sort_keys=True).encode()).hexdigest()
    result = dict(dataset_version=version, base_dataset_version=manifest['dataset_version'],
        identity_dataset_version=identity['dataset_version'],
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        git_source_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain', '--', 'src', 'scripts', 'tests'], cwd=ROOT, text=True).strip()),
        tags=dict(owner='tfm-team', project='tfm-scouting', dataset_kind='retained_valuation_evidence_audit_not_ml_training',
                  environment=f'Python {platform.python_version()} / {platform.system()}'),
        code_hashes=code, preserved_input_hashes=preserved, outputs={path.relative_to(ROOT).as_posix(): sha256(path) for path in paths},
        archive_rows=len(archive), archive_people=int(archive.source_player_id.nunique()),
        archive_nonmissing_values=int(archive.market_value_eur.notna().sum()),
        archive_missing_values=int(archive.market_value_eur.isna().sum()),
        raw_archive_columns=list(raw.columns), archive_valuation_date_fields_present=bool(valuation_date_fields),
        archive_multi_record_person_season_rows=int(archive.duplicated(['source_player_id','season'], keep=False).sum()),
        archive_person_season_conflicting_values=int(archive.groupby(['source_player_id','season']).market_value_eur.nunique().gt(1).sum()),
        current_sample_rows=len(current), parsed_header_observations=len(evidence), distinct_dated_current_values=len(dated),
        current_profile_supported_identity_candidates=int(current_candidates.proposal_status.eq('current_name_birth_year_supported').sum()),
        verified_identity_links=0, eligible_budget_attachments=0, models_retrained=False,
        source_or_existing_processed_files_changed=False, new_downloads=0,
        cutoff_eligibility=cutoff_rows,
        limitations=['Season labels, DOB, club-joining dates and contract dates do not establish valuation effective dates',
                     'Two dated current values were observed in October 2026; neither is eligible at target-season cutoffs',
                     'Name/birth-year proposals remain unreviewed and their accuracy is not measured',
                     'A requested Segunda URL does not establish current Segunda membership of every listed player',
                     'Retained source-use restrictions remain; this audit does not authorize training or redistribution',
                     'No estimated prices or transfer fees were generated'])
    for path, expected in preserved.items():
        if sha256(ROOT/path) != expected:
            raise ValueError(f'Audit modified preserved evidence: {path}')
    (ROOT/'reports/valuation_audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Archive:', len(archive), 'rows;', result['archive_nonmissing_values'], 'recorded values; effective dates absent')
    print('New offline date evidence:', len(dated), 'current values from', len(evidence), 'corroborating page headers')
    print(pd.DataFrame(cutoff_rows).to_string(index=False))
    return result


if __name__ == '__main__':
    run()
