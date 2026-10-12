"""Reported-value screening after ranking; no valuation fields enter models."""
import json

import numpy as np
import pandas as pd

from src.config import ROOT
from src.data.identity import club_key
from src.data.matching import normalize_name
from src.data.provenance import sha256
from src.data.source_rights import RESTRICTED


def load_budget_inputs():
    manifest = json.loads((ROOT / 'models/real/runtime_manifest.json').read_text())
    frames = []
    for item in [manifest['optional_budget']['values'], manifest['optional_budget']['candidates'],
                 manifest['outputs']['player_seasons']]:
        path = ROOT / item['path']
        if sha256(path) != item['sha256']:
            raise ValueError('Optional valuation, identity or history checksum changed')
        frames.append(pd.read_parquet(path))
    return tuple(frames)


def candidate_links(players, candidates, fbref):
    """Use existing source IDs, or unique name+club+season bridge for legacy rows."""
    supported = candidates[candidates.supported_review_candidate][
        ['canonical_player_id_proposed', 'source_player_id']].copy()
    if supported.canonical_player_id_proposed.duplicated().any() or supported.source_player_id.duplicated().any():
        raise ValueError('Ambiguous supported identity candidates')
    direct = players[['observation_id', 'entity_id']].merge(supported,
        left_on='entity_id', right_on='canonical_player_id_proposed', how='inner', validate='many_to_one')
    direct['price_match_basis'] = 'upstream_ID_exact_name_birth_year_provisional'
    remaining = players[~players.observation_id.isin(direct.observation_id)].copy()
    for frame in [remaining, fbref := fbref.copy()]:
        frame['name_key'] = frame.player.map(normalize_name)
        frame['club_key'] = frame.team.map(club_key)
    keys = ['name_key', 'club_key', 'season', 'league']
    left = remaining[~remaining.duplicated(keys, keep=False)]
    right = fbref[fbref.club_count.eq(1) & ~fbref.duplicated(keys, keep=False)]
    bridge = left[['observation_id'] + keys].merge(right[['entity_id'] + keys], on=keys, validate='one_to_one')
    bridge = bridge.merge(supported, left_on='entity_id', right_on='canonical_player_id_proposed', validate='many_to_one')
    bridge['price_match_basis'] = 'legacy_unique_name_club_season_to_FBref_plus_upstream_name_birth_year_provisional'
    columns = ['observation_id', 'source_player_id', 'price_match_basis']
    links = pd.concat([direct[columns], bridge[columns]], ignore_index=True)
    # A source identity cannot price several distinct model identities in one season.
    conflicts = links.merge(players[['observation_id', 'entity_id', 'season']], on='observation_id', validate='one_to_one')
    bad = conflicts.groupby(['source_player_id', 'season']).entity_id.transform('nunique').gt(1)
    return links[~bad.to_numpy()].reset_index(drop=True)


def attach_reported_values(ranking, links, values, cutoff):
    """Latest reported effective date <= cutoff, not historical known-at proof."""
    t = pd.to_datetime(cutoff, errors='raise')
    if pd.isna(t): raise ValueError('A valuation cutoff date is required')
    t = t.tz_localize(None) if t.tzinfo else t
    if links.observation_id.duplicated().any(): raise ValueError('Duplicate observation links')
    if values.duplicated(['source_player_id', 'valuation_date']).any():
        raise ValueError('Ambiguous player-date valuations')
    selected = values[values.source_player_id.isin(links.source_player_id) & values.valuation_date.le(t)].copy()
    # Select the latest record first: a latest zero/unknown cannot inherit an older positive value.
    selected = selected.sort_values(['valuation_date', 'source_player_id']).drop_duplicates('source_player_id', keep='last')
    packet = links.merge(selected[['source_player_id', 'market_value_eur', 'valuation_date']],
                         on='source_player_id', how='left', validate='many_to_one')
    packet = packet.rename(columns={'source_player_id': 'price_source_player_id',
        'market_value_eur': 'reported_market_value_eur', 'valuation_date': 'reported_valuation_date'})
    result = ranking.merge(packet, on='observation_id', how='left', validate='one_to_one')
    positive = result.reported_market_value_eur.gt(0) & np.isfinite(result.reported_market_value_eur)
    result['reported_value_status'] = np.select(
        [result.price_source_player_id.isna(), result.reported_valuation_date.isna(),
         result.reported_market_value_eur.eq(0), positive],
        ['unmatched', 'no_record_on_or_before_cutoff', 'reported_zero_ambiguous', 'reported_positive'], default='invalid_or_unknown')
    result['reported_value_screenable'] = positive
    result['reported_value_source'] = 'Transfermarkt via uploaded salimt dataset'
    result['price_identity_status'] = np.where(result.price_source_player_id.notna(), 'provisional_not_reviewed', 'unmatched')
    result['reported_value_kind'] = 'reported_market_assessment_not_transfer_fee'
    result['reported_valuation_cutoff'] = t
    result['historical_budget_eligible'] = False
    result['source_publication_known_at'] = pd.NaT
    result['ml_use_status'] = RESTRICTED
    result['model_use_eligible'] = False
    return result


def screen_budget(ranking, max_budget_million):
    amount = float(max_budget_million)
    if not np.isfinite(amount) or amount < 0: raise ValueError('Budget must be finite and nonnegative')
    return ranking[ranking.reported_value_screenable & ranking.reported_market_value_eur.le(amount * 1_000_000)].copy()
