"""Reproducible offline inspection of the user-uploaded Kaggle candidate."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pandas as pd

from src.config import ROOT
from src.data.kaggle_values import read_archive, audit_tables, PREFIX
from src.data.matching import normalize_name
from src.data.identity import club_key

ARCHIVE_SHA256 = 'edb88617d152526f042e2ede9992a86ae58518a2953baf6117bcba1e5cc5b3fd'
RAW = ROOT / 'data/raw/sources/kaggle_transfer_values'
OUT = ROOT / 'data/processed/real'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(upload=None):
    previous = json.loads((ROOT / 'reports/kaggle_transfer_value_assessment.json').read_text())
    preserved = dict(previous['preserved_input_sha256'])
    audit = json.loads((ROOT / 'reports/valuation_audit.json').read_text())
    preserved.update(audit['preserved_input_hashes'])
    for path, item in audit['outputs'].items():
        preserved[path] = item
    for path, expected in preserved.items():
        if sha(ROOT / path) != expected:
            raise ValueError(f'Existing evidence changed: {path}')
    source = Path(upload) if upload else RAW / (ARCHIVE_SHA256 + '.zip')
    profiles, history, dictionary, raw = read_archive(source, ARCHIVE_SHA256)
    RAW.mkdir(parents=True, exist_ok=True)
    saved = RAW / (ARCHIVE_SHA256 + '.zip')
    if saved.exists() and sha(saved) != ARCHIVE_SHA256:
        raise ValueError('Retained raw archive changed')
    if source.resolve() != saved.resolve():
        shutil.copyfile(source, saved)
    receipt_path = RAW / 'receipt.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt['archive_sha256'] != ARCHIVE_SHA256:
            raise ValueError('Receipt belongs to a different archive')
    else:
        receipt = {'archive_sha256': ARCHIVE_SHA256,
                   'first_inspected_at_utc': datetime.now(timezone.utc).isoformat(),
                   'uploaded_file_id': 'file_00000000206481f4915e8f8eec84f9dc',
                   'received_filename': 'archive.zip',
                   'claimed_dataset_url': previous['dataset_url'],
                   'kaggle_version': None, 'licence_supplied': False,
                   'delivery': 'user_upload_not_network_download'}
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    member_hashes = {}
    for name, payload in raw.items():
        target = RAW / name
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = hashlib.sha256(payload).hexdigest()
        if target.exists() and sha(target) != expected:
            raise ValueError(f'Retained raw member changed: {name}')
        target.write_bytes(payload)
        member_hashes[str(target.relative_to(ROOT))] = expected
    clean_profiles, clean_history, consistency, diagnostics = audit_tables(
        profiles, history, receipt['first_inspected_at_utc'])
    # Keep source IDs. Reuse only existing proposals for a review packet, never an approved join.
    crosswalk = pd.read_parquet(OUT / 'identity_crosswalk_proposed.parquet')
    latest = crosswalk[crosswalk.right_source.eq('transfermarkt') &
                       crosswalk.season_cutoff.eq('2025-2026')].copy()
    packet = latest.merge(clean_profiles[['source_player_id', 'name', 'league_name']],
                          left_on='right_id', right_on='source_player_id', validate='one_to_one')
    packet['uploaded_name_agrees_with_existing_right_name'] = [
        normalize_name(a) in {normalize_name(alias.strip()) for alias in b.split('|')}
        for a, b in zip(packet.name, packet.right_name)]
    packet['identity_match_status'] = 'provisional_not_reviewed'
    packet['model_use_eligible'] = False
    packet['historical_budget_eligible'] = False
    packet['source_use_authorized'] = False
    packet['original_source'] = 'Transfermarkt.com'
    packet['ml_use_status'] = clean_profiles.ml_use_status.iloc[0]
    diagnostics['existing_identity_proposal_overlap_players'] = len(packet)
    diagnostics['overlap_uploaded_name_agreement_players'] = int(packet.uploaded_name_agrees_with_existing_right_name.sum())
    diagnostics['existing_proposal_overlap_by_current_league_label'] = packet.league_name.value_counts().to_dict()
    # The upstream mapping contains additional IDs absent from the older TM
    # season archive. Keep all candidate pairs, including ambiguous IDs.
    mapping = pd.read_parquet(ROOT / 'data/external/worldfootballr/player_mapping.parquet')
    fb = pd.read_parquet(OUT / 'collected_player_seasons.parquet')
    candidates = mapping[mapping.fbref_id.isin(fb.source_player_id)][['fbref_id', 'transfermarkt_id']]
    candidates = candidates.drop_duplicates().merge(
        clean_profiles[['source_player_id', 'name', 'league_name']],
        left_on='transfermarkt_id', right_on='source_player_id', validate='many_to_one')
    names = fb.groupby('source_player_id').player.apply(lambda x: set(x.dropna().map(normalize_name)))
    club_sets = fb.groupby('source_player_id').clubs.apply(
        lambda x: {club_key(c) for v in x for c in json.loads(v)})
    history_clubs = clean_history.groupby('source_player_id').club.apply(lambda x: set(x.map(club_key)))
    candidates['normalized_name_agreement'] = [normalize_name(r.name) in names[r.fbref_id]
                                                for r in candidates.itertuples()]
    candidates['any_retained_history_club_overlap'] = [
        bool(club_sets[r.fbref_id] & history_clubs[r.source_player_id]) for r in candidates.itertuples()]
    candidates['source_id_ambiguous'] = candidates.groupby('source_player_id').fbref_id.transform('nunique').gt(1)
    candidates['fbref_id_ambiguous'] = candidates.groupby('fbref_id').source_player_id.transform('nunique').gt(1)
    candidates['canonical_player_id_proposed'] = 'fbref:' + candidates.fbref_id
    candidates['identity_match_status'] = 'provisional_not_reviewed'
    candidates['club_evidence_period_status'] = 'all_retained_dates_not_asof_decision_evidence'
    for column in ['source_use_authorized', 'historical_budget_eligible', 'model_use_eligible']:
        candidates[column] = False
    candidates['original_source'] = 'Transfermarkt.com'
    candidates['ml_use_status'] = clean_profiles.ml_use_status.iloc[0]
    diagnostics['upstream_mapping_candidate_pairs'] = len(candidates)
    diagnostics['upstream_mapping_candidate_source_players'] = candidates.source_player_id.nunique()
    diagnostics['upstream_mapping_candidate_la_liga_players'] = candidates.loc[
        candidates.league_name.eq('La Liga'), 'source_player_id'].nunique()
    diagnostics['upstream_mapping_ambiguous_source_players'] = candidates.loc[
        candidates.source_id_ambiguous, 'source_player_id'].nunique()
    diagnostics['upstream_mapping_name_and_club_supported_source_players'] = candidates.loc[
        candidates.normalized_name_agreement & candidates.any_retained_history_club_overlap &
        ~candidates.source_id_ambiguous & ~candidates.fbref_id_ambiguous, 'source_player_id'].nunique()
    diagnostics['new_identity_approvals'] = 0
    diagnostics['dictionary_undocumented_profile_columns'] = sorted(set(profiles) - set(dictionary.column))
    files = {}
    for name, frame in [('profiles', clean_profiles), ('history', clean_history),
                        ('summary_consistency', consistency), ('identity_review', packet),
                        ('upstream_identity_candidates', candidates)]:
        path = OUT / f'collected_kaggle_value_{name}.parquet'
        frame.to_parquet(path, index=False)
        files[str(path.relative_to(ROOT))] = sha(path)
    joined = clean_history.merge(clean_profiles[['source_player_id', 'league_name']],
                                on='source_player_id', validate='many_to_one')
    rows = []
    for league in sorted(set(clean_profiles.league_name) | {'Segunda División'}):
        subset = joined[joined.league_name.eq(league)]
        for start in range(2020, 2026):
            lower, upper = pd.Timestamp(f'{start}-07-01'), pd.Timestamp(f'{start+1}-07-01')
            selected = subset[subset.valuation_date_reported.ge(lower) & subset.valuation_date_reported.lt(upper)]
            earlier = subset[subset.valuation_date_one_day_earlier_hypothesis.ge(lower) &
                             subset.valuation_date_one_day_earlier_hypothesis.lt(upper)]
            rows.append({'source': 'kaggle_upload_declared_Transfermarkt',
                         'league_label': league, 'season': f'{start}-{start+1}',
                         'league_basis': 'current_export_player_listing_not_historical_membership',
                         'valuation_rows_reported_date': len(selected),
                         'valuation_rows_one_day_earlier_hypothesis': len(earlier),
                         'source_players': selected.source_player_id.nunique(),
                         'historical_budget_eligible_rows': 0,
                         'statistics_available': False, 'transfer_fees_available': False,
                         'coverage_status': 'no_listed_players' if not len(subset) else 'selected_player_sample_unresolved_dates'})
    coverage_path = ROOT / 'reports/kaggle_value_coverage.csv'
    pd.DataFrame(rows).to_csv(coverage_path, index=False)
    files[str(coverage_path.relative_to(ROOT))] = sha(coverage_path)
    dict_path = ROOT / 'reports/kaggle_value_dictionary.csv'
    descriptions = dictionary.set_index('column').description.to_dict()
    extra = {
        'source_player_id': 'Uploader-declared Transfermarkt person ID, not a cross-source canonical ID.',
        'valuation_date_raw': 'Unmodified history CSV date string (DD/MM/YYYY).',
        'valuation_date_reported': 'Strictly parsed history date; systematically disagrees with summary by one day.',
        'valuation_date_one_day_earlier_hypothesis': 'Reported date minus one day; audit hypothesis only, not a verified correction.',
        'valuation_date': 'Unresolved effective date: null; never inferred from summary or title.',
        'valuation_known_at': 'First local inspection UTC time; does not establish earlier public availability.',
        'source_publication_known_at': 'Unknown original public availability time: null.',
        'position_clean': 'Null: price strings corrupt the exported position column.',
        'current_club_clean': 'Null: systemic extraction corruption; history club is retained separately.',
        'historical_budget_eligible': 'False; dates, identity approval and use authorization remain unresolved.',
        'model_use_eligible': 'False; quarantined provider-derived evidence.',
        'source_use_authorized': 'False; no reviewed provider use licence supplied.',
        'reported_year_month_agree': 'Whether parsed history date agrees with redundant year/month fields.',
        'earlier_hypothesis_year_month_agree': 'Whether one-day-earlier hypothesis agrees with redundant year/month fields.',
        'market_value_eur': 'Uploader-reported market assessment in EUR, not verified fee or estimated price.',
        'amount_valid': 'Finite nonnegative numeric amount; does not certify correctness.',
        'currency': 'EUR as declared by file column names and value-display strings.',
        'date_quality_status': 'Unresolved systematic summary/history date disagreement.',
        'source': 'User-uploaded Kaggle candidate, with declared provider retained.',
        'original_source': 'Transfermarkt.com according to uploaded summary; not independently verified.',
        'first_observed_at_utc': 'Earliest preserved local inspection receipt; not source publication time.',
        'provenance_status': 'Uploader declaration, no upstream verification or Kaggle version supplied.',
        'ml_use_status': 'Existing provider restriction preserved pending explicit reviewed licence.',
        'identity_match_status': 'Unmatched in source tables; provisional_not_reviewed in review packet.',
        'position_reported_invalid': 'True when exported position contains a euro price.',
        'current_club_equals_nationality': 'Diagnostic equality, not club membership.',
        'profile_quality_status': 'Exported position and current-club fields quarantined.',
        'data_source': 'Uploader-declared original provider; omitted from uploaded dictionary.',
        'dataset_built_at': 'Uploader-declared build date, not independently verified publication.',
        'value_eur': 'History market assessment in EUR as reported by uploader.',
        'value_display': 'History formatted euro amount as reported by uploader.',
        'club': 'History club label; membership/source correctness not independently verified.',
        'age_at_date': 'Uploader age at valuation date; not a confirmed date of birth.',
        'year': 'Uploader redundant valuation year; disagrees with 24 reported date years.',
        'month': 'Uploader redundant 1-based month; part of systematic date inconsistency.',
        'player_id': 'Uploader Transfermarkt source person ID; retained in summary consistency, not canonical.',
        'history_points': 'Count of supplied history rows for this source person.',
        'first_history_date': 'Minimum parsed reported history date, not a verified effective date.',
        'last_history_date': 'Maximum parsed reported history date, not a verified effective date.',
        'history_peak_eur': 'Maximum supplied history amount in EUR.',
        'first_summary_to_history_days': 'First reported history date minus first summary date, in days.',
        'last_summary_to_history_days': 'Last reported history date minus last summary date, in days.',
        'left_source': 'FBref identity source in existing proposal.',
        'left_id': 'FBref source person ID in existing proposal.',
        'right_source': 'Transfermarkt identity source in existing proposal.',
        'right_id': 'Transfermarkt source person ID in existing proposal.',
        'season_cutoff': 'Latest retained proposal evidence-season cutoff; not public availability proof.',
        'left_name': 'FBref name aliases separated by | in existing proposal.',
        'right_name': 'Transfermarkt name aliases separated by | in existing proposal.',
        'exact_name': 'Normalized alias name agreement in existing proposal.',
        'name_similarity': 'Heuristic string similarity in existing proposal, not probability.',
        'overlapping_club_seasons': 'Existing proposal count of shared league/club/season contexts.',
        'birth_year_agreement': 'Existing proposal comparable birth-year agreement; upload supplies no DOB.',
        'birth_year_conflict': 'Existing proposal birth-year conflict flag.',
        'profile_conflict': 'Existing proposal incompatible profile metadata flag.',
        'upstream_id_mapping': 'Existing proposal supported by published but unreviewed ID mapping.',
        'evidence_score': 'Existing heuristic evidence points, not matching accuracy.',
        'left_margin': 'Existing score gap over competing right-source candidates.',
        'right_margin': 'Existing score gap over competing FBref candidates.',
        'proposal_status': 'Existing supported/review/conflict proposal status, no identity approval.',
        'evidence': 'JSON of original proposal evidence; retained unchanged.',
        'canonical_player_id': 'Existing proposed FBref-anchored person ID, unreviewed.',
        'unstable_across_cutoffs': 'Existing proposal changes FBref partner across evidence cutoffs.',
        'uploaded_name_agrees_with_existing_right_name': 'Uploaded name agrees with at least one normalized existing name alias.',
        'fbref_id': 'FBref source ID from retained published mapping.',
        'transfermarkt_id': 'Transfermarkt source ID from retained published mapping.',
        'normalized_name_agreement': 'Uploaded name agrees with at least one retained FBref name alias.',
        'any_retained_history_club_overlap': 'Any normalized club shared across all retained dates; not historical as-of evidence.',
        'source_id_ambiguous': 'One uploaded source ID maps to multiple FBref IDs in candidate packet.',
        'fbref_id_ambiguous': 'One FBref ID maps to multiple uploaded source IDs in candidate packet.',
        'canonical_player_id_proposed': 'FBref-anchored proposed person ID, never an approved join.',
        'club_evidence_period_status': 'Club overlap uses all retained dates; cannot establish decision-time evidence.',
    }
    dictionary_rows = []
    for name, frame in [('profiles', clean_profiles), ('history', clean_history),
                        ('summary_consistency', consistency), ('identity_review', packet),
                        ('upstream_identity_candidates', candidates)]:
        for column in frame:
            desc = extra.get(column, descriptions.get(column))
            if desc is None:
                raise ValueError(f'Missing dictionary definition: {column}')
            dictionary_rows.append({'table': name, 'column': column, 'dtype': str(frame[column].dtype),
                                    'description': desc,
                                    'source': 'local_audit' if column in extra else 'uploaded_dictionary',
                                    'historical_training_warning': 'Career/current aggregates contain later observations; not historical predictors.' if name == 'profiles' else 'Unresolved dates, source use and identity; not model eligible.'})
    pd.DataFrame(dictionary_rows).to_csv(dict_path, index=False)
    files[str(dict_path.relative_to(ROOT))] = sha(dict_path)
    for path, expected in preserved.items():
        if sha(ROOT / path) != expected:
            raise ValueError(f'Existing evidence mutated: {path}')
    manifest = {'status': 'uploaded_archive_inspected_quarantined', 'archive_sha256': ARCHIVE_SHA256,
                'receipt': receipt, 'members_sha256': member_hashes,
                'csv_parquet_parity': 'all values agree after string ID and empty-string missing normalization within 1e-12 numeric tolerance',
                'diagnostics': diagnostics, 'outputs_sha256': files,
                'preserved_inputs_sha256': preserved,
                'dataset_version': hashlib.sha256(json.dumps(member_hashes, sort_keys=True).encode()).hexdigest(),
                'licence_status': 'not_supplied_unverified', 'real_data_authenticity': 'uploader_declared_not_independently_verified',
                'historical_club_league_membership_verified': False,
                'new_downloads': 0, 'new_models_trained': 0, 'estimated_values_generated': 0,
                'git_source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'git_source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
                'code_sha256': {s: sha(ROOT / s) for s in ['src/data/kaggle_values.py', 'scripts/kaggle_value_audit.py']}}
    (ROOT / 'reports/kaggle_value_audit.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(diagnostics, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uploaded-archive', type=Path)
    run(parser.parse_args().uploaded_archive)
