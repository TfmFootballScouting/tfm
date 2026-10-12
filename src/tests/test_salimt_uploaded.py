"""Semantic checks against the retained real uploads; no training experiments."""
import pandas as pd
import pytest
from src.config import ROOT
from src.data.salimt_uploaded import normalize_profiles, normalize_values, identity_preview
from src.data.source_rights import require_model_data_use

RAW = ROOT / 'data/raw/sources/salimt_uploaded'


@pytest.fixture(scope='module')
def profiles():
    return pd.read_csv(RAW / 'player_profiles.csv', dtype={'player_id': str, 'current_club_id': str}, low_memory=False)


def test_profile_names_heights_and_dates_use_source_semantics(profiles):
    p = normalize_profiles(profiles)
    assert len(p) == 92671
    assert p.loc[p.source_player_id.eq('1'), 'player'].iloc[0] == 'Silvio Adzic'
    assert p.loc[p.source_player_id.eq('1'), 'height_cm'].isna().all()
    assert p.loc[p.source_player_id.eq('100011'), 'height_cm'].iloc[0] == 171
    assert p.height_raw_cm.eq(0).sum() == 18867
    assert p.date_of_birth.isna().sum() == 1006


def test_real_event_dates_do_not_invent_publication_or_prices():
    raw = pd.read_csv(RAW / 'player_market_value.csv', dtype={'player_id': str})
    v = normalize_values(raw, '2026-10-11T14:00:00Z')
    assert len(v) == 901429 and v.source_player_id.nunique() == 69441
    assert v.market_value_eur.equals(raw.value)
    assert v.reported_zero_value.sum() == 48009
    assert v.valuation_date.min() == pd.Timestamp('2003-12-14')
    assert v.valuation_date.max() == pd.Timestamp('2025-09-11')
    assert v.source_publication_known_at.isna().all()
    assert not v.historical_budget_eligible.any()


@pytest.mark.parametrize('damage', ['duplicate', 'missing_date', 'future_date', 'negative_amount'])
def test_invalid_valuation_keys_dates_or_amounts_fail(damage):
    raw = pd.read_csv(RAW / 'player_market_value.csv', dtype={'player_id': str}, nrows=2)
    if damage == 'duplicate':
        raw = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)
    elif damage == 'missing_date':
        raw.loc[0, 'date_unix'] = None
    elif damage == 'future_date':
        raw.loc[0, 'date_unix'] = '2027-01-01'
    else:
        raw.loc[0, 'value'] = -1
    with pytest.raises(ValueError):
        normalize_values(raw, '2026-10-11T14:00:00Z')


def test_preview_preserves_seasons_and_does_not_backfill_budget():
    fb = pd.read_parquet(ROOT / 'data/processed/real/collected_player_seasons.parquet')
    preview = pd.read_parquet(ROOT / 'data/processed/real/collected_salimt_identity_join_preview.parquet')
    assert len(fb) == len(preview) == 3378
    assert preview.observation_id.equals(fb.observation_id)
    assert preview.entity_id.equals(fb.entity_id) and preview.season.equals(fb.season)
    assert preview.salimt_source_player_id.notna().sum() == 2779
    assert preview.market_value_eur.equals(fb.market_value_eur)
    assert not preview.model_use_eligible.any()
    with pytest.raises(ValueError, match='Unreviewed'):
        require_model_data_use(preview)


def test_review_candidates_are_not_approved_and_conflicts_excluded():
    candidates = pd.read_parquet(ROOT / 'data/processed/real/collected_salimt_identity_candidates.parquet')
    assert candidates.birth_year_conflict.sum() == 6
    selected = candidates[candidates.supported_review_candidate]
    assert len(selected) == 1119
    assert not selected.source_player_id.duplicated().any() and not selected.fbref_id.duplicated().any()
    assert not selected.birth_year_conflict.any()
    assert selected.identity_match_status.eq('provisional_not_reviewed').all()
    assert not selected.use_authorized.any() and not selected.model_use_eligible.any()
