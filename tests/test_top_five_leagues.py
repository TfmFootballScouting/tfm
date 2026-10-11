import json
import numpy as np
import pandas as pd
import pytest
from scipy.spatial.distance import cdist
from streamlit.testing.v1 import AppTest
from src.config import ROOT
from src.app.leagues import LEAGUES, load_top_five_service, league_evaluation
from scripts.top_five_leagues import dominant_league_gallery


def test_real_gallery_coverage_unique_entities_and_frozen_transforms():
    for name in ['core','offensive']:
        service=load_top_five_service(name)
        mean=service.model.artifacts.scaler.mean_.copy()
        median=service.model.artifacts.imputer.statistics_.copy()
        assert set(service.gallery.league)==set(LEAGUES)
        assert not service.gallery.duplicated(['entity_id','season']).any()
        assert not service.gallery.partial_season.any()
        assert service.available_seasons[0]==('2023-2024' if name=='core' else '2024-2025')
        rec=service.for_season(service.available_seasons[0])
        assert rec.players.entity_id.is_unique and rec.players.player_id.is_unique
        for league in LEAGUES: assert rec.players.league.eq(league).sum()>300
        reference=int(rec.players[rec.players.league.eq('Premier League')].index[0])
        matches=rec.similar_players(rec.players.iloc[reference].player_id,top_n=5)
        expected=cdist(rec.X[reference:reference+1],rec.X)[0]
        indices=rec.players.set_index('player_id').index.get_indexer(matches.player_id)
        np.testing.assert_allclose(matches.distance,expected[indices])
        np.testing.assert_array_equal(service.model.artifacts.scaler.mean_,mean)
        np.testing.assert_array_equal(service.model.artifacts.imputer.statistics_,median)
        metrics=league_evaluation(name)
        assert set(metrics.league)==set(LEAGUES) and metrics.mrr.between(0,1).all()
        assert metrics.query_season.lt(metrics.evaluation_season).all()
        assert service.model.players.season.max()<metrics.evaluation_season.min()


def test_cross_league_transfer_keeps_dominant_observation_without_blending():
    frame=pd.read_parquet(ROOT/'data/processed/real/top_five_player_seasons.parquet')
    transferred=frame[frame.duplicated(['entity_id','season'],keep=False)]
    assert len(transferred)>0
    gallery=dominant_league_gallery(transferred)
    assert not gallery.duplicated(['entity_id','season']).any()
    for row in gallery.itertuples():
        actual=transferred[transferred.entity_id.eq(row.entity_id)&transferred.season.eq(row.season)]
        assert row.minutes==actual.minutes.max()
        assert row.observation_id in actual.observation_id.tolist()
        assert row.gls==actual[actual.observation_id.eq(row.observation_id)].gls.iloc[0]


def test_app_all_leagues_filters_similarity_reset_and_plain_clone(monkeypatch,tmp_path):
    monkeypatch.setenv('TFM_EVENT_LOG',str(tmp_path/'league_events.jsonl'))
    # A fresh clone has no private uploads: keep ordinary five-league recommendations working.
    import streamlit as st
    import src.app.budget as budget
    def unavailable(): raise FileNotFoundError('Private uploads excluded from Git')
    monkeypatch.setattr(budget,'load_budget_inputs',unavailable)
    st.cache_data.clear()
    try:
        app=AppTest.from_file(str(ROOT/'src/app/streamlit_app.py'),default_timeout=60).run()
        assert not app.exception and not app.error
        assert next(s for s in app.selectbox if s.label=='Mercado de scouting').value=='Cinco grandes ligas'
        league=next(s for s in app.selectbox if s.label=='Liga')
        assert set(league.options)=={'Todas',*LEAGUES}
        assert next(c for c in app.checkbox if c.label=='Filtrar por valor de mercado').disabled
        for name in LEAGUES:
            next(s for s in app.selectbox if s.label=='Liga').select(name).run()
            ranking=app.session_state['last_result']
            assert not app.exception and len(ranking)>0
            assert ranking.league.eq(name).all()
            next(b for b in app.button if b.label=='🔍 Buscar similares').click().run()
            assert not app.exception
            similarities=app.session_state['similar_result']
            assert len(similarities)>0 and similarities.league.eq(name).all()
        next(s for s in app.slider if s.label=='Edad máxima').set_value(20).run()
        next(b for b in app.button if b.label=='Restablecer filtros').click().run()
        assert not app.exception
        assert next(s for s in app.selectbox if s.label=='Liga').value=='Todas'
        assert next(s for s in app.slider if s.label=='Edad máxima').value==32
        next(s for s in app.selectbox if s.label=='Modelo de scouting').select('Ofensivo').run()
        assert not app.exception
        assert next(s for s in app.selectbox if s.label=='Temporada observada').value=='2024-2025'
    finally: st.cache_data.clear()


def test_scenario_league_constraint_and_scope_invalidation(monkeypatch,tmp_path):
    monkeypatch.setenv('TFM_EVENT_LOG',str(tmp_path/'scenario.jsonl'))
    app=AppTest.from_file(str(ROOT/'src/app/streamlit_app.py'),default_timeout=60).run()
    next(s for s in app.selectbox if s.label=='Liga').select('Premier League').run()
    next(s for s in app.selectbox if s.label=='Plantilla de requisitos').select('Ataque vertical').run()
    next(b for b in app.button if b.label=='Ejecutar escenario').click().run()
    assert not app.exception
    result=app.session_state['scenario_result']
    # Existing links may supply no eligible prices here; never invent a fallback.
    assert result['shortlist'].league.eq('Premier League').all()
    assert 'target_league' in result['funnel'].stage.tolist()
    next(s for s in app.selectbox if s.label=='Mercado de scouting').select('La Liga').run()
    assert not app.exception
    assert 'scenario_case' not in app.session_state.filtered_state
