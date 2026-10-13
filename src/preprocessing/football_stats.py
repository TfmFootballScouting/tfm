"""Offline preprocessing of retained real datasets, within the existing layout.

Raw inputs and the currently served legacy model/data remain unchanged. No global
imputation/scaling, new downloads, synthetic fallback or automatic name joins.
"""
import argparse
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.config import ROOT, MIN_MINUTES, FEATURE_COLS
from src.data.matching import normalize_name
from src.data.provenance import sha256
from src.scraping.transfermarkt import scorer_sample
from src.features.requirements import (ALL_COUNTS, BUDGET_COLUMNS, MODEL_CANDIDATE_FEATURES,
                                       feature_contract, style_coverage)

OBS_KEYS = ['source_player_id', 'league', 'season', 'team']
SEASON_KEYS = ['source_player_id', 'league', 'season']
NULL_TEXT = {'', '-', 'NA', 'N/A', 'nan', 'None', '<NA>'}
SPLITS = {'2020-2021': 'train', '2021-2022': 'train', '2022-2023': 'train',
          '2023-2024': 'validation', '2024-2025': 'holdout', '2025-2026': 'partial_monitoring'}
CORE_SPLITS = {'2020-2021': 'train', '2021-2022': 'train', '2022-2023': 'validation',
               '2023-2024': 'holdout', '2024-2025': 'sparse_monitoring', '2025-2026': 'partial_monitoring'}


def clean_text(series):
    return series.astype('string').str.strip().replace(list(NULL_TEXT), pd.NA)


def numeric(series, *, low=None, high=None):
    text = clean_text(series)
    values = pd.to_numeric(text, errors='coerce').astype(float)
    invalid = (text.notna() & values.isna()) | (values.notna() & (~np.isfinite(values)))
    if low is not None:
        invalid |= values.notna() & values.lt(low)
    if high is not None:
        invalid |= values.notna() & values.gt(high)
    return values.mask(invalid), int(invalid.sum())


def stable_id(*values):
    return hashlib.sha256(json.dumps([str(v) for v in values], ensure_ascii=False).encode()).hexdigest()[:24]


def check_keys(frame, keys):
    if frame[keys].isna().any().any():
        raise ValueError(f'Missing identity keys: {keys}')
    if frame.duplicated(keys).any():
        raise ValueError(f'Conflicting duplicate keys: {keys}')


def add_rates(frame):
    out = frame.copy()
    out['nineties'] = out.minutes / 90
    denominator = out.nineties.where(out.nineties > 0)
    out['ga'] = out.gls + out.ast
    for column in ALL_COUNTS:
        out[column + '_p90'] = out[column] / denominator
    out['pass_completion_pct'] = (100 * out.passes_completed / out.passes_attempted.where(out.passes_attempted > 0))
    out['minutes_eligible'] = out.minutes.ge(MIN_MINUTES)
    out['complete_core_features'] = out[FEATURE_COLS].notna().all(axis=1)
    out['baseline_candidate'] = (out.minutes_eligible & out.pos_main.isin(['DF', 'MF', 'FW'])
                                 & out.gls_p90.notna() & out.ast_p90.notna())
    out['tactical_proxy_candidate'] = out.baseline_candidate & out.complete_core_features
    out['experiment_split'] = out.season.map(SPLITS)
    out['core_proxy_split'] = out.season.map(CORE_SPLITS)
    out['historical_candidate'] = out.baseline_candidate & out.experiment_split.ne('partial_monitoring')
    out['age_filter_supported'] = out.age.notna()
    out['budget_filter_supported'] = False
    out['quality_outlier'] = (out.minutes.gt(3420) | out.gls_p90.gt(3) | out.sh_p90.gt(15))
    out['quality_inconsistent_counts'] = out.sot.gt(out.sh) | out.passes_completed.gt(out.passes_attempted)
    return out


def normalize_fbref(frame):
    out = frame.copy()
    required = set(OBS_KEYS + ['player', 'pos', 'minutes', 'gls', 'ast', 'source'])
    if not required <= set(out):
        raise ValueError(f'Missing FBref schema: {sorted(required - set(out))}')
    if out.source.astype(str).str.contains('demo|synthetic', case=False).any():
        raise ValueError('Synthetic observations cannot enter collected-data preprocessing')
    if out.source.isna().any() or not out.source.isin(['fbref', 'fbref_worldfootballr']).all():
        raise ValueError('FBref normalization requires a known FBref source')
    for column in OBS_KEYS + ['player', 'pos', 'nation']:
        out[column] = clean_text(out[column])
    if not out.season.str.fullmatch(r'20\d{2}-20\d{2}').all() or not out.season.map(lambda s: int(s[5:]) == int(s[:4]) + 1).all():
        raise ValueError('Invalid consecutive season label')
    exact_removed = int(out.duplicated().sum())
    out = out.drop_duplicates().copy()
    check_keys(out, OBS_KEYS)
    issues = []
    out['age_source_text'] = clean_text(out['age']) if 'age' in out else pd.NA
    age = out.age_source_text.str.extract(r'^(\d+)(?:-\d+)?$', expand=False)
    out['age'], invalid = numeric(age, low=14, high=50)
    invalid += int((out.age_source_text.notna() & age.isna()).sum())
    issues.append(dict(table='fbref_club_seasons', field='age', invalid_values_nulled=invalid))
    for column in ['minutes', 'mp', 'birth_year'] + ALL_COUNTS:
        original = out[column] if column in out else pd.Series(pd.NA, index=out.index, dtype='string')
        out[column], invalid = numeric(original, low=0)
        if column in ALL_COUNTS and column not in ('xg', 'xag', 'xa'):
            fractional = out[column].notna() & (out[column] - out[column].round()).abs().gt(1e-8)
            invalid += int(fractional.sum())
            out.loc[fractional, column] = np.nan
        issues.append(dict(table='fbref_club_seasons', field=column, invalid_values_nulled=invalid))
    out['pos_main'] = out.pos.str.split(',').str[0].str.strip().str.upper()
    out.loc[~out.pos_main.isin(['GK', 'DF', 'MF', 'FW']), 'pos_main'] = pd.NA
    out['entity_id'] = 'fbref:' + out.source_player_id
    out['observation_id'] = out.apply(lambda r: stable_id('fbref', *(r[c] for c in OBS_KEYS)), axis=1)
    out['player_id'] = out.observation_id.map(lambda value: int(value[:13], 16))
    for column in ['date_of_birth', 'height_cm', 'foot'] + BUDGET_COLUMNS:
        out[column] = pd.NA
    out['age_reference'] = 'source-reported season age; birth year does not establish DOB'
    out['partial_season'] = out.season.eq('2025-2026')
    out['knowledge_date'] = pd.NaT
    out['ml_use_status'] = 'candidate_secondary_archive_rights_not_independently_verified'
    out = add_rates(out).sort_values(OBS_KEYS).reset_index(drop=True)
    if out.observation_id.duplicated().any() or out.player_id.duplicated().any():
        raise ValueError('Observation ID collision')
    return out, issues, exact_removed


def aggregate_player_seasons(clubs):
    """Sum compatible club stints; a missing stint makes its season total missing."""
    check_keys(clubs, OBS_KEYS)
    rows = []
    for key, group in clubs.groupby(SEASON_KEYS, sort=True):
        base = group.iloc[0].to_dict()
        for column in ['minutes', 'mp'] + ALL_COUNTS:
            base[column] = group[column].sum(min_count=len(group))
        teams = sorted(group.team.unique())
        base['clubs'] = json.dumps(teams, ensure_ascii=False)
        base['club_count'] = len(teams)
        base['team'] = teams[0] if len(teams) == 1 else f'{len(teams)} clubs'
        base['observation_id'] = stable_id('fbref_player_season', *key)
        base['player_id'] = int(base['observation_id'][:13], 16)
        for column in ['player', 'age', 'birth_year', 'nation']:
            values = group[column].dropna().unique()
            base[column] = values[0] if len(values) == 1 else pd.NA
        base['metadata_conflict'] = any(group[c].dropna().nunique() > 1 for c in ['player', 'age', 'birth_year', 'nation'])
        position_minutes = group.groupby('pos_main', dropna=True).minutes.sum().sort_values(ascending=False)
        base['pos_main'] = position_minutes.index[0] if len(position_minutes) else pd.NA
        positions = sorted({token.strip() for value in group.pos.dropna() for token in value.split(',')})
        base['pos'] = ','.join(positions) if positions else pd.NA
        rows.append(base)
    out = pd.DataFrame(rows)
    for column in ALL_COUNTS + ['minutes', 'mp', 'age', 'birth_year']:
        out[column] = pd.to_numeric(out[column], errors='coerce')
    out = add_rates(out).sort_values(SEASON_KEYS).reset_index(drop=True)
    check_keys(out, SEASON_KEYS)
    check_keys(out, ['player_id'])
    return out


def normalize_shots(frame):
    out = frame.copy().drop_duplicates()
    for column in ['shot_id', 'source_player_id', 'season', 'player', 'home_team', 'away_team']:
        out[column] = clean_text(out[column])
    check_keys(out, ['shot_id'])
    out['match_id'] = pd.to_numeric(out.match_id, errors='raise').astype('Int64').astype('string')
    side = clean_text(out.h_a).combine_first(clean_text(out.home_away))
    if not side.isin(['h', 'a']).all():
        raise ValueError('Unknown Understat shot-side schema; cannot infer shooter club')
    out['team'] = out.home_team.where(side.eq('h'), out.away_team)
    out['league'] = 'La Liga'
    out['match_datetime'] = pd.to_datetime(out.date, errors='coerce')
    out['timestamp_timezone'] = 'provider_unspecified'
    issues = []
    for column, lower, upper in [('X', 0, 1), ('Y', 0, 1), ('xG', 0, 1), ('minute', 0, 150)]:
        out[column], invalid = numeric(out[column], low=lower, high=upper)
        issues.append(dict(table='understat_shots', field=column, invalid_values_nulled=invalid))
    out['goal'] = out.result.eq('Goal').astype(int)
    out['own_goal'] = out.result.eq('OwnGoal').astype(int)
    out['attacking_shot'] = ~out.result.eq('OwnGoal')
    # Excluding an own-goal event is not imputing a missing attacking estimate.
    out['attacking_xg'] = out.xG.where(out.attacking_shot, 0.0)
    out = out.sort_values(['season', 'match_id', 'shot_id']).reset_index(drop=True)
    keys = ['source_player_id', 'season', 'team']
    summaries = out.groupby(keys, sort=True).agg(
        player=('player', 'first'), recorded_shot_events=('shot_id', 'size'), shots=('attacking_shot', 'sum'), goals=('goal', 'sum'),
        own_goals=('own_goal', 'sum'), xg=('attacking_xg', lambda s: s.sum(min_count=len(s))),
        matches_with_shot_records=('match_id', 'nunique'), first_match=('match_datetime', 'min'),
        last_match=('match_datetime', 'max')).reset_index()
    summaries['league'] = 'La Liga'
    summaries['source'] = 'understat'
    summaries['minutes'] = np.nan
    summaries['coverage_note'] = 'shooters only; no exposure, assists or xA; source estimates remain separate'
    summaries['partial_season'] = summaries.season.eq('2025-2026')
    return out, summaries, issues


def normalize_valuations(frame):
    out = frame.copy().drop_duplicates()
    out['player'] = clean_text(out.player_name)
    out['team'] = clean_text(out.squad)
    out['source_player_id'] = clean_text(out.source_player_id)
    out['date_of_birth'] = pd.to_datetime(out.player_dob, errors='coerce')
    out['height_cm'], invalid_height = numeric(out.player_height_mtrs, low=1.4, high=2.2)
    out['height_cm'] *= 100
    out['foot'] = clean_text(out.player_foot)
    out['source_age'], invalid_age = numeric(out.player_age, low=14, high=50)
    out['market_value_eur'], invalid_value = numeric(out.player_market_value_euro, low=0)
    out['currency'] = 'EUR'
    out['valuation_date'] = pd.NaT
    out['valuation_known_at'] = pd.NaT
    out['budget_filter_supported'] = False
    out['profile_asof_date'] = pd.NaT
    out['conflicting_observation'] = out.duplicated(['source_player_id', 'team', 'season'], keep=False)
    record_columns = sorted(out.columns)
    out['record_id'] = out.apply(lambda r: stable_id(*(r[c] for c in record_columns)), axis=1)
    check_keys(out, ['record_id'])
    out = out.sort_values(['source_player_id', 'season', 'team']).reset_index(drop=True)
    return out, [dict(table='transfermarkt_profiles_valuations', field=c, invalid_values_nulled=n)
                 for c, n in [('height_cm', invalid_height), ('source_age', invalid_age), ('market_value_eur', invalid_value)]]


def normalize_transfers(frame):
    exact_removed = int(frame.duplicated().sum())
    out = frame.drop_duplicates().copy()
    out['source_player_id'] = clean_text(out.source_player_id)
    out['from_club'] = out.club_2.where(out.transfer_type.eq('Arrivals'), out.team_name)
    out['to_club'] = out.team_name.where(out.transfer_type.eq('Arrivals'), out.club_2)
    if not out.transfer_type.isin(['Arrivals', 'Departures']).all():
        raise ValueError('Unexpected transfer direction')
    out['fee_eur'], invalid = numeric(out.transfer_fee, low=0)
    out['fee_zero_unverified'] = out.fee_eur.eq(0)
    out['transfer_date'] = pd.NaT
    out['known_at'] = pd.NaT
    movement_keys = ['source_player_id', 'season', 'window', 'from_club', 'to_club']
    out['potential_movement_id'] = out.apply(lambda r: stable_id(*(r[c] for c in movement_keys)), axis=1)
    out['movement_record_count'] = out.groupby('potential_movement_id').potential_movement_id.transform('size')
    record_columns = sorted(out.columns)
    out['record_id'] = out.apply(lambda r: stable_id(*(r[c] for c in record_columns)), axis=1)
    check_keys(out, ['record_id'])
    out['event_status'] = 'candidate_movement_without_verified_date; not a validated transfer label'
    out = out.sort_values(['season', 'source_player_id', 'window', 'from_club', 'to_club', 'transfer_type']).reset_index(drop=True)
    return out, exact_removed, [dict(table='transfermarkt_transfers', field='fee_eur', invalid_values_nulled=invalid)]


def identity_candidates(clubs, shooters, valuations, mapping):
    """Make review queues, never enrich performance rows using unapproved names."""
    fb = clubs[['source_player_id', 'player', 'birth_year']].drop_duplicates('source_player_id').copy()
    fb['name_key'] = fb.player.map(normalize_name)
    us = shooters[['source_player_id', 'player']].drop_duplicates('source_player_id').copy()
    us['name_key'] = us.player.map(normalize_name)
    candidates = fb.merge(us, on='name_key', suffixes=('_fb', '_us'))
    candidates = candidates[candidates.name_key.ne('')]
    def contexts(frame):
        if not {'team', 'season'} <= set(frame):
            return {}
        aliases = {'betis': 'realbetis', 'huesca': 'sdhuesca'}
        return {pid: {(aliases.get(normalize_name(r.team), normalize_name(r.team)), r.season)
                      for r in group.itertuples()} for pid, group in frame.groupby('source_player_id')}
    fb_contexts, us_contexts = contexts(clubs), contexts(shooters)
    rows = []
    for r in candidates.itertuples():
        overlap = fb_contexts.get(r.source_player_id_fb, set()) & us_contexts.get(r.source_player_id_us, set())
        rows.append(dict(left_source='fbref', left_id=r.source_player_id_fb, right_source='understat',
                 right_id=r.source_player_id_us, left_name=r.player_fb, right_name=r.player_us,
                 status='review_required', evidence='normalized name; club/season corroboration is not approval; DOB unavailable',
                 overlapping_club_seasons=len(overlap),
                 ambiguous=bool((candidates.source_player_id_fb == r.source_player_id_fb).sum() > 1
                                or (candidates.source_player_id_us == r.source_player_id_us).sum() > 1)))
    pairs = mapping[['fbref_id', 'transfermarkt_id']].dropna().drop_duplicates()
    relevant = pairs[pairs.fbref_id.isin(fb.source_player_id)].copy()
    people = valuations[['source_player_id', 'player', 'date_of_birth']].drop_duplicates('source_player_id')
    relevant = relevant.merge(fb, left_on='fbref_id', right_on='source_player_id', how='left').drop(columns='source_player_id')
    relevant = relevant.merge(people, left_on='transfermarkt_id', right_on='source_player_id', how='left', suffixes=('_fb', '_tm'))
    for r in relevant.itertuples():
        ambiguous = (pairs.fbref_id.eq(r.fbref_id).sum() > 1 or pairs.transfermarkt_id.eq(r.transfermarkt_id).sum() > 1)
        mismatch = pd.notna(r.birth_year) and pd.notna(r.date_of_birth) and int(r.birth_year) != r.date_of_birth.year
        rows.append(dict(left_source='fbref', left_id=r.fbref_id, right_source='transfermarkt', right_id=r.transfermarkt_id,
                         left_name=r.player_fb, right_name=r.player_tm,
                         status='conflicting_birth_year' if mismatch else 'review_required',
                         evidence='upstream source-ID mapping; unreviewed locally', ambiguous=bool(ambiguous),
                         ml_use_status='restricted_pending_explicit_license'))
    return pd.DataFrame(rows).sort_values(['left_source', 'left_id', 'right_source', 'right_id']).reset_index(drop=True)


def approved_matches(path, candidates):
    columns = ['left_source', 'left_id', 'right_source', 'right_id', 'reviewer', 'evidence', 'reviewed_at']
    if not path.exists():
        return pd.DataFrame(columns=columns)
    reviewed = pd.read_csv(path, dtype='string')
    if not set(columns) <= set(reviewed):
        raise ValueError('Reviewed mapping schema is incomplete')
    if reviewed[columns].isna().any().any() or reviewed[columns].apply(lambda s: s.str.strip().eq('').any()).any():
        raise ValueError('Reviewed mappings need explicit identities, reviewer, evidence and timestamp')
    for _, group in reviewed.groupby(['left_source', 'right_source']):
        if group.left_id.duplicated().any() or group.right_id.duplicated().any():
            raise ValueError('Reviewed identity mappings must be one-to-one per source pair')
    keys = columns[:4]
    merged = reviewed.merge(candidates[keys+['status']], on=keys, how='left', validate='one_to_one')
    if merged.status.isna().any() or merged.status.eq('conflicting_birth_year').any():
        raise ValueError('Reviewed mapping absent from candidates or has conflicting birth year')
    pd.to_datetime(merged.reviewed_at, errors='raise', utc=True)
    return reviewed


def quality_tables(tables):
    inventory, missingness = [], []
    for name, frame in tables.items():
        inventory.append(dict(table=name, rows=len(frame), columns=len(frame.columns), exact_duplicates=int(frame.duplicated().sum())))
        for column in frame:
            missingness.append(dict(table=name, field=column, missing=int(frame[column].isna().sum()),
                                    missing_fraction=float(frame[column].isna().mean()) if len(frame) else None))
    return pd.DataFrame(inventory), pd.DataFrame(missingness)


def data_dictionary(tables):
    units = dict(minutes='minutes', mp='appearances', age='years (source season age)',
                 source_age='years (as-of not verified)', birth_year='calendar year',
                 height_cm='centimetres', market_value_eur='EUR; effective date unknown',
                 fee_eur='upstream parsed EUR; zero semantics unverified',
                 currency='ISO currency code', X='normalized pitch coordinate [0,1]',
                 Y='normalized pitch coordinate [0,1]', xG='Understat expected goals per shot',
                 minute='match minute', nineties='minutes / 90',
                 pass_completion_pct='completed / attempted passes × 100')
    for column in ALL_COUNTS:
        units[column] = 'expected event total' if column in ('xg','xag','xa') else 'event count'
        units[column+'_p90'] = 'events / 90 minutes; unknown exposure or count stays missing'
    descriptions = dict(
        ga='Gls + Ast; missing propagates; exclude redundant G+A from model features',
        xag='FBref expected assisted goals; not interchangeable with Understat xA',
        xa='Expected assists; unavailable in the retained FBref/shot datasets',
        team='Actual club at stint grain; N clubs label at aggregated multi-club grain',
        clubs='JSON list of source-reported clubs; not a current-club claim',
        baseline_candidate='450+ minutes, known outfield position, measured goals and assists',
        tactical_proxy_candidate='Baseline candidate with all ten core features observed',
        historical_candidate='Baseline candidate outside partial 2025/26; not an as-of validation claim',
        budget_filter_supported='False: no approved dated as-of valuations are attached',
        quality_outlier='Review flag, not automatic clipping/removal',
        own_goal='Own-goal event; excluded from attacking shot/goal totals',
        attacking_xg='Underlying shot xG excluding own-goal events; real missing attacking xG propagates',
        recorded_shot_events='All provider shot records including own goals',
        shots='At shooter grain, attacking shots excluding own goals',
        matches_with_shot_records='Distinct matches with retained events; not player appearances',
        potential_movement_id='Grouping of source ID, season, window and from/to clubs; exact transfer date unverified',
        fee_zero_unverified='A numeric source zero does not independently verify a free transfer',
        input_snapshot_sha256='SHA-256 of normalized input file; original raw asset lineage is in the manifest',
        knowledge_date='Unknown historical publication time; cannot establish strict as-of availability',
        ml_use_status='Retained source-use status; separate from data completeness',
        status='Identity proposal status; no name-only automatic approval',
        overlapping_club_seasons='Corroborating source club/season pairs, not verified identity')
    records = []
    for table, frame in tables.items():
        for column in frame:
            records.append(dict(table=table, field=column, dtype=str(frame[column].dtype),
                unit=units.get(column, 'ISO/source timestamp' if 'date' in column or column in ('known_at','first_match','last_match')
                               else 'identifier/text/boolean; source-specific' ),
                description=descriptions.get(column, 'Required core per-90 scouting feature' if column in FEATURE_COLS
                                             else 'Retained provider field or audited metadata; original source definition applies'),
                missing_policy='Unknown retained; no global imputation',
                model_candidate=column in MODEL_CANDIDATE_FEATURES))
    return pd.DataFrame(records)


def run():
    folder = ROOT / 'data/external/worldfootballr'
    output = ROOT / 'data/processed/real'
    output.mkdir(parents=True, exist_ok=True)
    reports = ROOT / 'reports'
    paths = {name: folder / (name + '.parquet') for name in ['fbref_player_seasons', 'understat_shots',
             'transfermarkt_valuations', 'transfermarkt_transfers', 'player_mapping']}
    paths.update(current_market=ROOT/'data/external/transfermarkt/current_market_sample.csv',
                 current_profiles=ROOT/'data/external/transfermarkt/current_profiles_sample.csv',
                 legacy_raw=ROOT/'data/raw/players_raw.csv',
                 archive_manifest=ROOT/'reports/worldfootballr_sources.json')
    access_path = ROOT/'reports/uploaded_scraper_access.json'
    scorer_record = next(row['record'] for row in json.loads(access_path.read_text())
                         if row['source'] == 'transfermarkt' and 'record' in row)
    paths['segunda_scorer_raw'] = ROOT/scorer_record['path']
    if sha256(paths['segunda_scorer_raw']) != scorer_record['sha256']:
        raise ValueError('Retained Segunda response checksum mismatch')
    review_path = output / 'identity_matches_reviewed.csv'
    if review_path.exists():
        paths['identity_matches_reviewed'] = review_path
    inputs = {name: dict(path=path.relative_to(ROOT).as_posix(), sha256=sha256(path)) for name, path in paths.items()}
    frames = {name: pd.read_parquet(path) for name, path in paths.items() if path.suffix == '.parquet'}
    clubs, issues, fb_removed = normalize_fbref(frames['fbref_player_seasons'])
    clubs['source_snapshot'] = inputs['fbref_player_seasons']['path']
    clubs['input_snapshot_sha256'] = inputs['fbref_player_seasons']['sha256']
    seasons = aggregate_player_seasons(clubs)
    shots, shooters, shot_issues = normalize_shots(frames['understat_shots'])
    valuations, valuation_issues = normalize_valuations(frames['transfermarkt_valuations'])
    transfers, transfer_removed, transfer_issues = normalize_transfers(frames['transfermarkt_transfers'])
    candidates = identity_candidates(clubs, shooters, valuations, frames['player_mapping'])
    reviewed = approved_matches(review_path, candidates)
    scorers = scorer_sample(paths['segunda_scorer_raw'].read_bytes(), '2024-2025')
    scorers['snapshot_sha256'] = scorer_record['sha256']
    scorers['retrieved_at'] = scorer_record['retrieved_at']
    scorers['historical_model_candidate'] = False
    tables = dict(collected_player_club_seasons=clubs, collected_player_seasons=seasons,
                  collected_baseline_candidates=seasons[seasons.historical_candidate].copy(),
                  collected_tactical_candidates=seasons[seasons.tactical_proxy_candidate & ~seasons.partial_season].copy(),
                  collected_understat_shots=shots, collected_understat_shooters=shooters,
                  collected_profiles_valuations=valuations, collected_transfers=transfers,
                  collected_segunda_scorer_sample=scorers,
                  identity_candidates=candidates, identity_matches_approved=reviewed)
    for name, table in tables.items():
        table.to_parquet(output / f'{name}.parquet', index=False)
    # Current samples have no historical dates and are never appended to history.
    for name in ['current_market', 'current_profiles']:
        frame = pd.read_csv(paths[name], dtype={'source_player_id': 'string'})
        if 'date_of_birth' in frame:
            frame['date_of_birth'] = pd.to_datetime(frame.date_of_birth, errors='coerce')
        for column in ['market_value_eur', 'age', 'height_cm']:
            if column in frame:
                frame[column], invalid = numeric(frame[column], low=0)
                issues.append(dict(table='collected_'+name, field=column, invalid_values_nulled=invalid))
        if 'foot' in frame:
            frame['foot'] = clean_text(frame.foot)
        if 'valuation_date' in frame:
            frame['valuation_date'] = pd.to_datetime(frame.valuation_date, errors='coerce')
        frame['valuation_known_at'] = pd.NaT
        frame['ml_use_status'] = 'restricted_pending_explicit_license'
        frame['budget_filter_supported'] = False
        tables['collected_'+name] = frame
        frame.to_parquet(output / f'collected_{name}.parquet', index=False)
    inventory, missingness = quality_tables(tables)
    data_dictionary(tables).to_csv(reports/'collected_data_dictionary.csv', index=False)
    inventory.to_csv(reports/'collected_inventory.csv', index=False)
    missingness.to_csv(reports/'collected_missingness.csv', index=False)
    pd.DataFrame(issues + shot_issues + valuation_issues + transfer_issues).to_csv(reports/'collected_invalid_values.csv', index=False)
    pd.DataFrame(feature_contract()).to_csv(reports/'mandatory_features.csv', index=False)
    pd.DataFrame(style_coverage(seasons)).to_csv(reports/'collected_style_coverage.csv', index=False)
    availability = []
    for season, group in seasons.groupby('season'):
        for record in feature_contract():
            field = record['feature']
            availability.append(dict(season=season, feature=field, role=record['role'], rows=len(group),
                                     observed=int(group[field].notna().sum()), missing_fraction=float(group[field].isna().mean())))
    pd.DataFrame(availability).to_csv(reports/'mandatory_feature_coverage.csv', index=False)
    seasons.groupby(['season', 'pos_main'], dropna=False).agg(rows=('observation_id','size'),
        minutes_eligible=('minutes_eligible','sum'), baseline_candidates=('historical_candidate','sum'),
        tactical_candidates=('tactical_proxy_candidate','sum'), multi_club=('club_count',lambda s:int(s.gt(1).sum())),
        outliers=('quality_outlier','sum')).reset_index().to_csv(reports/'collected_season_position_coverage.csv', index=False)
    legacy = pd.read_csv(paths['legacy_raw'])
    legacy.groupby(['source','league','season']).size().rename('rows').reset_index().assign(
        use='preserved_only; synthetic excluded and overlapping legacy rows not pooled').to_csv(reports/'collected_legacy_exclusions.csv', index=False)
    code_paths = ['src/preprocessing/football_stats.py', 'src/features/requirements.py', 'src/config.py',
                  'src/data/matching.py', 'src/scraping/transfermarkt.py']
    code_hashes = {path: sha256(ROOT/path) for path in code_paths}
    fingerprint = hashlib.sha256(json.dumps(dict(inputs=inputs, code=code_hashes, min_minutes=MIN_MINUTES), sort_keys=True).encode()).hexdigest()
    manifest = dict(dataset_version=fingerprint, generated_at=datetime.now(timezone.utc).isoformat(),
        tags=dict(owner='tfm-team', project='tfm-scouting', dataset_kind='real_collected_source_separated', environment_python=platform.python_version()),
        inputs=inputs, code_hashes=code_hashes,
        source_snapshots=json.loads(paths['archive_manifest'].read_text()),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        git_source_dirty=bool(subprocess.check_output(['git','status','--porcelain','--','src','scripts','tests','requirements.txt','requirements.lock.txt'],cwd=ROOT,text=True).strip()),
        parameters=dict(min_minutes=MIN_MINUTES, imputation='none', scaling='none; fit on training only',
                        transfer_aggregation='sum complete stint counts; unknown propagates', chronological_splits=SPLITS),
        core_proxy_splits=CORE_SPLITS,
        outputs={name:dict(rows=len(frame),path=(output/f'{name}.parquet').relative_to(ROOT).as_posix(),
                           sha256=sha256(output/f'{name}.parquet')) for name,frame in tables.items()},
        exact_duplicates_removed=dict(fbref=fb_removed, transfermarkt_transfers=transfer_removed),
        identities=dict(candidate_pairs=len(candidates),approved_pairs=len(reviewed),automatic_name_joins=0),
        final_model_retrained=False, existing_model_dataset_changed=False,
        limitations=['No complete real Segunda data', '2025/26 partial snapshot excluded from historical candidates',
                     'No dated eligible budget values', 'Cross-source names remain review candidates',
                     'Archive knowledge timestamps unavailable; season splits are not strict historical as-of proof',
                     'GK-specific features absent; goalkeepers excluded from outfield candidates',
                     'Broad styles are statistical proxies, not validated tactical roles'])
    (reports/'collected_preprocessing.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(inventory.to_string(index=False))
    print('Dataset version:',fingerprint)
    return manifest


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    run()
