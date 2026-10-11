"""Normalize retained uploads and propose identities without approving joins."""
import re
import numpy as np
import pandas as pd
from src.data.matching import normalize_name
from src.data.source_rights import RESTRICTED


def normalize_profiles(raw):
    if raw.player_id.isna().any() or raw.player_id.duplicated().any():
        raise ValueError('Profile IDs must be nonmissing and unique')
    out = raw[['player_id', 'player_name', 'date_of_birth', 'height', 'position',
               'main_position', 'foot', 'current_club_id', 'current_club_name']].copy()
    out = out.rename(columns={'player_id': 'source_player_id', 'player_name': 'player_raw',
                              'height': 'height_raw_cm', 'position': 'position_source'})
    out['player'] = [re.sub(r'\s*\(' + re.escape(str(pid)) + r'\)\s*$', '', str(name)).strip()
                     for pid, name in zip(out.source_player_id, out.player_raw)]
    out['date_of_birth_raw'] = out.date_of_birth
    out['date_of_birth'] = pd.to_datetime(out.date_of_birth, format='%Y-%m-%d', errors='raise')
    out['birth_year'] = out.date_of_birth.dt.year.astype('Int64')
    height = pd.to_numeric(out.height_raw_cm, errors='coerce')
    out['height_cm'] = height.where(height.gt(0) & np.isfinite(height))
    out['profile_temporal_scope'] = 'current_profile_unknown_source_observation_time'
    return out


def normalize_values(raw, receipt_time):
    if raw.player_id.isna().any() or raw.duplicated(['player_id', 'date_unix']).any():
        raise ValueError('Valuation source ID/date keys must be present and unique')
    out = raw.rename(columns={'player_id': 'source_player_id', 'date_unix': 'valuation_date_raw',
                              'value': 'market_value_eur'}).copy()
    out['valuation_date'] = pd.to_datetime(out.valuation_date_raw, format='%Y-%m-%d', errors='raise')
    if out.valuation_date.isna().any():
        raise ValueError('Missing valuation event date')
    amounts = pd.to_numeric(out.market_value_eur, errors='coerce')
    if amounts.isna().any() or (~np.isfinite(amounts)).any() or amounts.lt(0).any():
        raise ValueError('Invalid market assessment amount')
    out['currency'] = 'EUR'
    out['reported_zero_value'] = amounts.eq(0)
    stamp = pd.Timestamp(receipt_time)
    if stamp.tzinfo is None:
        raise ValueError('Receipt time must include timezone')
    if out.valuation_date.gt(stamp.tz_convert('UTC').tz_localize(None)).any():
        raise ValueError('Valuation event date follows receipt')
    out['market_value_eur'] = amounts
    out['valuation_known_at'] = stamp.tz_convert('UTC')
    out['source_publication_known_at'] = pd.Series(pd.NaT, index=out.index, dtype='datetime64[ns, UTC]')
    out['date_evidence_status'] = 'ISO_event_date_from_uploaded_CSV_not_primary_verified'
    out['historical_budget_eligible'] = False
    return out


def propose_identities(profiles, fbref, mapping):
    pairs = mapping[['fbref_id', 'transfermarkt_id']].dropna().drop_duplicates()
    pairs = pairs[pairs.fbref_id.isin(fbref.source_player_id)].merge(
        profiles[['source_player_id', 'player', 'date_of_birth', 'birth_year']],
        left_on='transfermarkt_id', right_on='source_player_id', validate='many_to_one')
    names = fbref.groupby('source_player_id').player.apply(lambda s: set(s.dropna().map(normalize_name)))
    years = fbref.groupby('source_player_id').birth_year.apply(lambda s: set(s.dropna().astype(int)))
    pairs['normalized_name_agreement'] = [normalize_name(r.player) in names[r.fbref_id]
                                          for r in pairs.itertuples()]
    pairs['birth_year_agreement'] = [pd.notna(r.birth_year) and years[r.fbref_id] == {int(r.birth_year)}
                                     for r in pairs.itertuples()]
    pairs['birth_year_conflict'] = [pd.notna(r.birth_year) and bool(years[r.fbref_id]) and
                                    years[r.fbref_id] != {int(r.birth_year)} for r in pairs.itertuples()]
    pairs['source_id_ambiguous'] = pairs.groupby('source_player_id').fbref_id.transform('nunique').gt(1)
    pairs['fbref_id_ambiguous'] = pairs.groupby('fbref_id').source_player_id.transform('nunique').gt(1)
    pairs['supported_review_candidate'] = (pairs.normalized_name_agreement & pairs.birth_year_agreement &
                                           ~pairs.source_id_ambiguous & ~pairs.fbref_id_ambiguous)
    pairs['canonical_player_id_proposed'] = 'fbref:' + pairs.fbref_id
    pairs['identity_match_status'] = 'provisional_not_reviewed'
    pairs['evidence_temporal_scope'] = 'retained_source_mapping_and_current_profile_not_asof_proof'
    return pairs


def identity_preview(fbref, profiles, candidates):
    selected = candidates[candidates.supported_review_candidate]
    packet = selected[['canonical_player_id_proposed', 'source_player_id']].merge(
        profiles, on='source_player_id', validate='one_to_one')
    packet = packet.rename(columns={c: 'salimt_' + c for c in packet if c != 'canonical_player_id_proposed'})
    out = fbref.merge(packet, left_on='entity_id', right_on='canonical_player_id_proposed',
                      how='left', validate='many_to_one')
    if len(out) != len(fbref) or out.observation_id.duplicated().any():
        raise ValueError('Preview changed FBref observation grain')
    out['identity_match_status'] = np.where(out.salimt_source_player_id.notna(),
                                           'provisional_not_reviewed', 'unmatched')
    out['mapping_source'] = 'Transfermarkt.com'
    out['ml_use_status'] = RESTRICTED
    out['model_use_eligible'] = False
    return out
