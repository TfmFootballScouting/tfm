"""Source-separated uploaded histories and review-only season-aware enrichment."""
import hashlib
import json

import numpy as np
import pandas as pd

from src.data.source_rights import RESTRICTED
from src.config import FEATURE_COLS

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
        for feature in FEATURE_COLS:
            if feature not in row:
                row[feature] = np.nan
        row['missing_advanced_features_reason'] = 'not_collected_by_uploaded_source'
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


def field_description(column):
    """Dictionary definitions for additions; base FBref definitions remain separate."""
    if column.startswith('salimt_'):
        meaning, unit = field_description(column[len('salimt_'):])
        return 'Provisional source-prefixed addition: ' + meaning, unit
    if column.endswith('_raw'):
        return 'Original uploaded text before numeric/date parsing; not overwritten by cleaning.', 'source text'
    if column.endswith('_missing_stints'):
        return 'Number of club stints missing this measurement; any missing stint makes its season total unknown.', 'club stints'
    if column.endswith('_invalid'):
        return 'Original nonempty value rejected by numeric nonnegative-integer or ISO-date validation.', 'boolean'
    if column.endswith('_p90'):
        return 'Events per 90 using complete aggregated source minutes; absent advanced measurements remain null.', 'events / 90 minutes'
    meanings = {
        'source_player_id': ('Transfermarkt player ID; joins only within this source unless a mapping is reviewed.', 'source identifier'),
        'player_id': ('Transfermarkt ID in source tables; numeric FBref surrogate ID in integration_review.', 'identifier'),
        'season': ('Consecutive football season YYYY-YYYY; never a price timestamp.', 'season'),
        'league': ('League derived from source competition ID, not current club metadata.', 'league name'),
        'source_event_id': ('SHA-256 prefix of ten original transfer fields; exact duplicate event identity.', '24 hex characters'),
        'source_row_numbers': ('JSON list of original payload row numbers retained through aggregation/deduplication.', 'JSON record indices'),
        'clubs': ('JSON sorted source club IDs for this player-league-season.', 'JSON source identifiers'),
        'club_names': ('JSON sorted reported clubs for this player-league-season.', 'JSON source names'),
        'club_count': ('Distinct source clubs contributing to the aggregated league-season.', 'clubs'),
        'minutes_played': ('Observed source minutes; all club stints must be known for a complete season total.', 'minutes'),
        'minutes_eligible': ('Complete observed aggregate minutes >=450; not source-use permission.', 'boolean'),
        'age_at_season_end': ('Completed years from reported DOB to June 30 of the second season year; not historical role proof.', 'years'),
        'ga': ('Source goals plus assists, unknown if either count is unknown; excluded from fitting as redundant.', 'events'),
        'report_cutoff': ('June 30 season-end boundary used for backward-only reported-price association.', 'ISO date'),
        'reported_value_date': ('Uploader reported effective date of associated valuation; original publication time unknown.', 'ISO date'),
        'reported_value_eur_not_budget': ('Most recent reported amount on/before report_cutoff; unknown licence/publication makes it audit-only.', 'reported EUR'),
        'historical_budget_eligible': ('Always false; no authorized, reviewed and known-at historical budget assigned.', 'boolean'),
        'transfer_fee_reported': ('Parsed nonnegative numeric reported transfer fee, distinct from market value; units not independently verified.', 'claimed source EUR'),
        'value_at_transfer_reported': ('Parsed reported market value associated with transfer; distinct from transaction fee.', 'claimed source EUR'),
        'transfer_date': ('Reported ISO transfer event date; not publication date or successful-outcome evidence.', 'ISO date'),
        'date_season_inconsistent': ('Transfer date outside July 1–June 30 source-season window; retained for offseason/source-label review.', 'boolean'),
        'count_inconsistency': ('Appearances exceed squad inclusion, penalty goals exceed total, or zero appearances with positive minutes/goals.', 'boolean'),
        'performance_outlier': ('Conservative review flag: >6000 minutes or >60 goals/assists in a league-season stint; no row removal.', 'boolean'),
        'position_source': ('Current uploaded position label; historical positions are unverified.', 'source category'),
        'source_publication_known_at': ('Unknown original publication timestamp, retained null.', 'UTC timestamp'),
        'first_observed_at_utc': ('First local preservation time; not proof of historical availability.', 'UTC timestamp'),
        'model_use_eligible': ('Always false for source enrichment until existing source/identity gates are resolved.', 'boolean'),
        'original_source': ('Underlying Transfermarkt provider provenance, retained through joins.', 'provider name'),
    }
    if column in meanings:
        return meanings[column]
    if column in COUNTS:
        return 'Reported ' + column.replace('_', ' ') + '; nonnegative integer, complete-stint aggregation only.', 'events/appearances'
    if column.endswith('_zero_ambiguous') or column == 'zero_value_ambiguous':
        return 'Reported numeric zero retained without inferring free transfer or zero true market value.', 'boolean'
    return 'Source-reported or audit metadata: ' + column.replace('_', ' ') + '; source scope and restrictions retained.', 'text/field-specific'
