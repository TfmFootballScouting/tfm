"""Audit observed transfer labels; never invent negatives or fit restricted data."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import ROOT
from src.data.provenance import sha256

INPUTS = {
    'gallery': 'data/processed/real/five_league_pipeline_core_gallery.parquet',
    'identities': 'data/processed/real/europe_review_candidates.parquet',
    'transfers': 'data/processed/real/collected_salimt_transfer_history.parquet',
}
NON_CLUBS = {'', 'without club', 'retired', 'unknown', 'career break', 'no club', 'no team', 'free agent', 'none', 'nan'}


def classify_events(transfers):
    events = transfers.copy()
    events['event_date'] = pd.to_datetime(events.transfer_date, format='%Y-%m-%d', errors='coerce')
    starts = pd.to_numeric(events.season_start_year, errors='raise').astype(int)
    lower = pd.to_datetime(starts.astype(str) + '-07-01')
    upper = pd.to_datetime((starts + 1).astype(str) + '-07-01')
    events['season_date_conflict'] = events.event_date.notna() & ~events.event_date.between(lower, upper, inclusive='left')
    origin = events.from_team_name.fillna('').astype(str).str.strip().str.casefold()
    destination = events.to_team_name.fillna('').astype(str).str.strip().str.casefold()
    from_id = events.from_team_id.fillna('').astype(str)
    to_id = events.to_team_id.fillna('').astype(str)
    clubs = ~origin.isin(NON_CLUBS) & ~destination.isin(NON_CLUBS) & from_id.ne('') & to_id.ne('')
    kind = pd.Series('other_or_unknown', index=events.index)
    kind.loc[events.transfer_type.eq('Transfer') & clubs & from_id.ne(to_id) & origin.ne(destination)] = 'permanent_club_change'
    kind.loc[events.transfer_type.eq('Transfer') & ~clubs] = 'non_club_or_unknown_transition'
    kind.loc[events.transfer_type.eq('Loan')] = 'loan'
    kind.loc[events.transfer_type.eq('Return from loan')] = 'loan_return'
    kind.loc[events.transfer_type.eq('Draft')] = 'draft'
    events['event_kind'] = kind
    events['event_date_usable'] = events.event_date.notna() & ~events.season_date_conflict
    # Retain raw evidence; duplicates must not inflate event counts.
    events = events.drop_duplicates(['player_id', 'transfer_date', 'from_team_id', 'to_team_id', 'transfer_type'])
    return events


def audit_cases(gallery, identities, events):
    cohort = gallery[gallery.season.isin(['2020-2021', '2021-2022', '2022-2023', '2023-2024'])].copy()
    if cohort.duplicated(['entity_id', 'season']).any():
        raise ValueError('Audit cohort needs one source identity per season')
    links = identities[identities.supported_review_candidate.fillna(False)][
        ['canonical_player_id_proposed', 'source_player_id']].copy()
    if links.canonical_player_id_proposed.duplicated().any() or links.source_player_id.duplicated().any():
        raise ValueError('Ambiguous identity proposals cannot define transfer cases')
    cohort = cohort.merge(links, left_on='entity_id', right_on='canonical_player_id_proposed',
                          how='left', validate='many_to_one', suffixes=('_fbref', '_tm'))
    needed = set(links.source_player_id.astype(str))
    relevant_events = events[events.player_id.astype(str).isin(needed)]
    groups = {str(key): value for key, value in relevant_events.groupby('player_id', sort=False)}
    rows = []
    for row in cohort.itertuples():
        cutoff = pd.Timestamp(f'{int(row.season[5:])}-06-30')
        end = cutoff + pd.DateOffset(years=1)
        player = getattr(row, 'source_player_id_tm')
        history = groups.get(str(player), events.iloc[:0])
        window = history[history.event_date.gt(cutoff) & history.event_date.le(end)]
        positive = window[window.event_date_usable & window.event_kind.eq('permanent_club_change')]
        if pd.isna(player):
            status = 'identity_unmapped'
        elif len(positive):
            status = 'reported_permanent_transfer_pending_review'
        else:
            status = 'no_recorded_permanent_transfer_followup_unknown'
        unresolved = history[(history.season_start_year.eq(cutoff.year) | history.event_date.between(cutoff, end)) &
                             ~history.event_date_usable]
        rows.append(dict(entity_id=row.entity_id, source_player_id_tm=player, season=row.season,
            league=row.league, prediction_date=cutoff, outcome_window_end=end, label_status=status,
            observed_positive_candidate=1 if len(positive) else pd.NA,
            permanent_events=len(positive), loan_events=int(window.event_kind.eq('loan').sum()),
            loan_return_events=int(window.event_kind.eq('loan_return').sum()),
            non_club_events=int(window.event_kind.eq('non_club_or_unknown_transition').sum()),
            unresolved_date_events=len(unresolved),
            identity_status='provisional_not_reviewed' if pd.notna(player) else 'unmapped',
            followup_completeness='not_independently_verified', verified_binary_target=pd.NA,
            model_use_eligible=False))
    result = pd.DataFrame(rows)
    result['observed_positive_candidate'] = result.observed_positive_candidate.astype('Int64')
    result['verified_binary_target'] = result.verified_binary_target.astype('Int64')
    return result


def main():
    output = ROOT / 'reports/transfer_likelihood'
    output.mkdir(parents=True, exist_ok=True)
    frames = {key: pd.read_parquet(ROOT / value) for key, value in INPUTS.items()}
    events = classify_events(frames['transfers'])
    cases = audit_cases(frames['gallery'], frames['identities'], events)
    local = ROOT / 'data/processed/real/transfer_likelihood_label_candidates.parquet'
    cases.to_parquet(local, index=False)
    coverage = cases.groupby(['season', 'league', 'label_status']).size().rename('cases').reset_index()
    coverage.to_csv(output / 'label_coverage.csv', index=False)
    events.groupby(['season', 'event_kind', 'event_date_usable']).size().rename('events').reset_index().to_csv(output / 'event_quality.csv', index=False)
    # Cohort-level counts only; names and per-player provider labels stay local.
    report = {'status': 'label_audit_complete_training_blocked',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'git_base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'script_sha256': sha256(ROOT / 'scripts/transfer_label_audit.py'),
        'prediction_definition': 'At June 30, reported permanent club-to-club change within the following 12 months',
        'cohort': 'Existing five-league core gallery, 2020/21 through 2023/24',
        'inputs': {key: {'path': value, 'sha256': sha256(ROOT / value)} for key, value in INPUTS.items()},
        'cases': len(cases), 'status_counts': cases.label_status.value_counts().to_dict(),
        'verified_positive_targets': 0, 'verified_negative_targets': 0, 'training_eligible_cases': 0,
        'source_event_rows': len(frames['transfers']), 'deduplicated_event_rows': len(events),
        'missing_or_unparsed_dates': int(events.event_date.isna().sum()),
        'source_season_date_conflicts': int(events.season_date_conflict.sum()),
        'local_case_output': {'path': str(local.relative_to(ROOT)), 'sha256': sha256(local)},
        'blocking_requirements': ['No independently verified no-transfer follow-up; absence is unknown, never zero',
            'Cross-source identities remain provisional, not approved',
            'Source-use restriction remains in force for model training',
            'Season/date conflicts need adjudication; exclude unresolved events from positive candidates',
            'Source publication dates are unknown; historical feature availability needs review'],
        'model_fitting_performed': False}
    (output / 'label_audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['cases', 'status_counts', 'training_eligible_cases', 'status']}, indent=2))


if __name__ == '__main__':
    main()
