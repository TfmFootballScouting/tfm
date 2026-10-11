"""Unit edge cases and functional budget screening on real retained values."""
import json

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.app.budget import attach_reported_values, screen_budget, candidate_links, load_budget_inputs
from src.config import ROOT, MODELS_DIR
from src.models.recommend import PlayerRecommender
from src.data.source_rights import require_model_data_use, SourceUseRestricted


def test_reported_date_unknown_and_latest_zero_no_backfill():
    # Small unit fixtures exercise date/zero semantics; not experiment data.
    ranking = pd.DataFrame({'observation_id': ['a', 'b', 'c'], 'affinity': [1., .8, .5]})
    links = pd.DataFrame({'observation_id': ['a', 'b'], 'source_player_id': ['1', '2'], 'price_match_basis': ['provisional'] * 2})
    values = pd.DataFrame({'source_player_id': ['1', '1', '2'], 'market_value_eur': [100000., 0., 500000.],
                          'valuation_date': pd.to_datetime(['2023-06-01', '2024-06-01', '2025-06-01'])})
    early = attach_reported_values(ranking, links, values, '2023-06-30')
    assert screen_budget(early, 1).observation_id.tolist() == ['a']
    later = attach_reported_values(ranking, links, values, '2024-06-30')
    assert later.reported_value_status.tolist() == ['reported_zero_ambiguous', 'no_record_on_or_before_cutoff', 'unmatched']
    assert screen_budget(later, 1).empty
    assert later.source_publication_known_at.isna().all()
    assert not later.historical_budget_eligible.any()
    with pytest.raises(SourceUseRestricted): require_model_data_use(later)
    with pytest.raises(ValueError): screen_budget(later, float('nan'))


def test_ambiguous_links_and_values_fail():
    ranking = pd.DataFrame({'observation_id': ['a']})
    links = pd.DataFrame({'observation_id': ['a', 'a'], 'source_player_id': ['1', '2']})
    values = pd.DataFrame({'source_player_id': ['1'], 'market_value_eur': [10.], 'valuation_date': pd.to_datetime(['2024-01-01'])})
    with pytest.raises(ValueError, match='Duplicate observation'): attach_reported_values(ranking, links, values, '2024-12-31')
    with pytest.raises(ValueError, match='Ambiguous player-date'):
        attach_reported_values(ranking, links.iloc[:1], pd.concat([values, values]), '2024-12-31')


def test_real_links_and_filtering_leave_model_features_unchanged():
    values, candidates, profiles = load_budget_inputs()
    rec = PlayerRecommender.load(MODELS_DIR / 'recommender.joblib')
    before = rec.players.copy(deep=True)
    links = candidate_links(rec.players, candidates, profiles)
    assert links.observation_id.is_unique
    assert len(links) > 0
    results = attach_reported_values(rec.players, links, values, '2025-09-11')
    chosen = screen_budget(results, 1)
    assert len(chosen) > 0
    assert chosen.reported_market_value_eur.between(1, 1_000_000).all()
    assert chosen.reported_valuation_date.le(pd.Timestamp('2025-09-11')).all()
    pd.testing.assert_frame_equal(rec.players, before)
    for _, row in chosen.iterrows():
        latest = values[(values.source_player_id == row.price_source_player_id) & values.valuation_date.le(pd.Timestamp('2025-09-11'))].sort_values('valuation_date').iloc[-1]
        assert row.reported_market_value_eur == latest.market_value_eur
        assert row.reported_valuation_date == latest.valuation_date


def test_real_app_budget_filter_refreshes_and_exports(monkeypatch, tmp_path):
    monkeypatch.setenv('TFM_EVENT_LOG', str(tmp_path / 'budget_events.jsonl'))
    app = AppTest.from_file(str(ROOT / 'src/app/streamlit_app.py'), default_timeout=40).run()
    assert not app.exception and not app.error
    next(item for item in app.checkbox if item.label == 'Filtrar por valor de mercado').check().run()
    assert not app.exception
    next(item for item in app.number_input if item.label == 'Presupuesto máximo (M€)').set_value(1.0).run()
    results = app.session_state['last_result']
    assert len(results) > 0
    assert results.reported_market_value_eur.gt(0).all()
    assert results.reported_market_value_eur.le(1_000_000).all()
    assert results.price_identity_status.eq('provisional_not_reviewed').all()
    assert not results.historical_budget_eligible.any()
    assert any('publicación' in item.value for item in app.caption)
    next(item for item in app.button if item.label == '🔍 Buscar jugadores').click().run()
    assert not app.exception
    events = [json.loads(line) for line in (tmp_path / 'budget_events.jsonl').read_text().splitlines()]
    assert events[0]['attributes']['reported_value_budget_million'] == 1.0
    next(item for item in app.checkbox if item.label == 'Filtrar por valor de mercado').uncheck().run()
    assert not app.exception
    assert app.session_state['last_filters'][5] is None
