"""Source-separated uploaded histories and review-only season-aware enrichment."""
import hashlib
import json

import numpy as np
import pandas as pd

from src.data.source_rights import RESTRICTED

COUNTS = ['nb_in_group', 'nb_on_pitch', 'goals', 'assists', 'own_goals',
          'subed_in', 'subed_out', 'yellow_cards', 'second_yellow_cards',
          'direct_red_cards', 'penalty_goals', 'goals_conceded', 'clean_sheets']


def numeric_reported(series):
    """Invalid, fractional count and negative values remain unknown, not zero."""
    values = pd.to_numeric(series, errors='coerce')
    valid = values.ge(0) & np.isfinite(values) & values.mod(1).eq(0)
    return values.where(valid), series.notna() & ~valid


def clean_performances(raw, profiles):
    out = raw.copy()
    for column in COUNTS + ['minutes_played']:
        out[column + '_raw'] = out[column]
        out[column], out[column + '_invalid'] = numeric_reported(out[column])
    out['minutes_unknown_for_appearance'] = out.nb_on_pitch.gt(0) & out.minutes_played.isna()
    out['count_inconsistency'] = (out.nb_on_pitch.gt(out.nb_in_group) |
                                 out.penalty_goals.gt(out.goals) |
                                 (out.nb_on_pitch.eq(0) & (out.goals.gt(0) | out.minutes_played.gt(0))))
    out['performance_outlier'] = (out.minutes_played.gt(6000) | out.goals.gt(60) |
                                  out.assists.gt(60))
    out['league'] = out.competition_id.map({'ES1': 'La Liga', 'ES2': 'Segunda División'})
    context = profiles[['source_player_id', 'player', 'date_of_birth', 'height_cm',
                        'position_source', 'main_position', 'foot']].rename(
                            columns={'source_player_id': 'player_id',
                                     'player': 'profile_player', 'main_position': 'profile_main_position'})
    if context.player_id.isna().any() or context.player_id.duplicated().any():
        raise ValueError('Profile source IDs must be unique')
    out = out.merge(context, on='player_id', how='left', validate='many_to_one')
    out['profile_context_status'] = 'current_snapshot_not_historical_role'
    return out


def aggregate_seasons(stints):
    """All stints participate; a missing stint prevents a complete season rate."""
    records = []
    for key, group in stints.groupby(['player_id', 'season', 'league'], sort=True):
        row = dict(zip(['source_player_id', 'season', 'league'], key))
        row.update(club_count=group.team_id.nunique(),
                   clubs=json.dumps(sorted(group.team_id.dropna().unique().tolist())),
                   club_names=json.dumps(sorted(group.team_name.dropna().unique().tolist())),
                   source_row_numbers=json.dumps(group.source_row_number.tolist()),
                   season_start_year=int(group.season_start_year.iloc[0]))
        for column in COUNTS + ['minutes_played']:
            row[column] = group[column].sum(min_count=len(group))
            row[column + '_missing_stints'] = int(group[column].isna().sum())
        row['count_inconsistency'] = bool(group.count_inconsistency.any())
        row['performance_outlier'] = bool(group.performance_outlier.any())
        row['profile_player'] = group.profile_player.iloc[0]
        row['position_source'] = group.position_source.iloc[0]
        row['profile_context_status'] = 'current_snapshot_not_historical_role'
        cutoff = pd.Timestamp(f'{row["season_start_year"]+1}-06-30')
        dob = pd.to_datetime(group.date_of_birth.iloc[0])
        row['age_at_season_end'] = ((cutoff.year - dob.year -
            ((cutoff.month, cutoff.day) < (dob.month, dob.day))) if pd.notna(dob) and dob <= cutoff else np.nan)
        row['ga'] = row['goals'] + row['assists']
        for source, dest in [('goals', 'gls_p90'), ('assists', 'ast_p90'), ('ga', 'ga_p90')]:
            row[dest] = row[source] * 90 / row['minutes_played'] if row['minutes_played'] > 0 else np.nan
        row['minutes_eligible'] = bool(row['minutes_played'] >= 450)
        row['partial_season'] = row['season_start_year'] == 2025
        row['original_source'] = 'Transfermarkt.com'
        row['ml_use_status'] = RESTRICTED
        row['model_use_eligible'] = False
        row['source_publication_known_at'] = pd.NaT
        records.append(row)
    return pd.DataFrame(records)


def clean_transfers(raw):
    """Deduplicate exact original fields only; preserve duplicate lineage."""
    out = raw.copy()
    fields = ['player_id', 'season_name', 'transfer_date', 'from_team_id', 'from_team_name',
              'to_team_id', 'to_team_name', 'transfer_type', 'value_at_transfer', 'transfer_fee']
    out['source_event_id'] = out[fields].apply(lambda row: hashlib.sha256(
        json.dumps(row.where(row.notna(), None).tolist(), ensure_ascii=False).encode()).hexdigest()[:24], axis=1)
    lineage = out.groupby('source_event_id').source_row_number.agg(list).map(json.dumps)
    out = out.drop_duplicates(fields).copy()
    out['source_row_numbers'] = out.source_event_id.map(lineage)
    out['transfer_date_raw'] = out.transfer_date
    out['transfer_date'] = pd.to_datetime(out.transfer_date, format='%Y-%m-%d', errors='coerce')
    out['transfer_date_invalid'] = out.transfer_date_raw.notna() & out.transfer_date.isna()
    for column in ['transfer_fee', 'value_at_transfer']:
        out[column + '_raw'] = out[column]
        out[column + '_reported'], out[column + '_invalid'] = numeric_reported(out[column])
        out[column + '_zero_ambiguous'] = out[column + '_reported'].eq(0)
    out['fee_semantics'] = np.where(out.transfer_fee_reported.gt(0),
                                  'positive_numeric_reported', 'unknown_or_zero_not_verified_free')
    out['currency_verification'] = 'claimed_source_EUR_not_independently_verified'
    out['date_season_inconsistent'] = (out.transfer_date.lt(pd.to_datetime(out.season_start_year.astype(str) + '-07-01')) |
        out.transfer_date.gt(pd.to_datetime((out.season_start_year + 1).astype(str) + '-06-30')))
    out['model_use_eligible'] = False
    return out.reset_index(drop=True)


def merge_review_only(fbref, seasons, candidates):
    pairs = candidates[candidates.supported_review_candidate][
        ['canonical_player_id_proposed', 'source_player_id']].copy()
    if pairs.source_player_id.duplicated().any() or pairs.canonical_player_id_proposed.duplicated().any():
        raise ValueError('Ambiguous cross-source identity candidates')
    packet = seasons.merge(pairs, on='source_player_id', how='inner', validate='many_to_one')
    packet = packet.rename(columns={column: 'salimt_' + column for column in packet
                                   if column not in ['canonical_player_id_proposed', 'season', 'league']})
    out = fbref.merge(packet, left_on=['entity_id', 'season', 'league'],
                     right_on=['canonical_player_id_proposed', 'season', 'league'],
                     how='left', validate='one_to_one')
    if len(out) != len(fbref) or not out.observation_id.is_unique:
        raise ValueError('Enrichment changed base observation grain')
    out['identity_match_status'] = np.where(out.salimt_source_player_id.notna(),
                                           'provisional_not_reviewed', 'unmatched')
    out['mapping_source'] = 'Transfermarkt.com'
    out['ml_use_status'] = RESTRICTED
    out['model_use_eligible'] = False
    return out
