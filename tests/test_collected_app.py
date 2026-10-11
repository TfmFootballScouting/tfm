import json
import numpy as np
import pandas as pd
import pytest
from scipy.spatial.distance import cdist
from streamlit.testing.v1 import AppTest
from src.app.collected import load_collected_service
from src.config import ROOT, PLAY_STYLES
from src.features.styles import measured_weight_fraction


def test_frozen_gallery_season_and_distances():
    service = load_collected_service('core')
    source_players = service.model.players.copy(deep=True)
    before_mean = service.model.artifacts.scaler.mean_.copy()
    before_median = service.model.artifacts.imputer.statistics_.copy()
    assert service.available_seasons[0] == '2023-2024'
    assert '2024-2025' not in service.available_seasons
    with pytest.raises(ValueError): service.for_season('2024-2025')
    rec = service.for_season('2023-2024')
    assert len(rec.players) == 393 and rec.players.entity_id.is_unique
    assert rec.players.season.eq('2023-2024').all()
    reference = rec.players.iloc[0]
    results = rec.similar_players(reference.player_id, top_n=5)
    assert reference.entity_id not in results.entity_id.tolist()
    expected = cdist(rec.X[:1], rec.X)[0]
    positions = rec.players.set_index('player_id').index.get_indexer(results.player_id)
    np.testing.assert_allclose(results.distance, expected[positions])
    np.testing.assert_allclose(results.similarity, 1/(1 + results.distance))
    np.testing.assert_array_equal(service.model.artifacts.scaler.mean_, before_mean)
    np.testing.assert_array_equal(service.model.artifacts.imputer.statistics_, before_median)
    pd.testing.assert_frame_equal(service.model.players, source_players)
    assert all(measured_weight_fraction(style, rec.artifacts.feature_cols) >= .6 for style in PLAY_STYLES)


def test_offensive_supported_styles_and_gallery():
    service = load_collected_service('offensive')
    assert service.available_seasons[0] == '2024-2025'
    rec = service.for_season('2024-2025')
    styles = service.supported_styles
    assert set(styles) == {'vertical', 'contraataque'}
    assert len(rec.players) == 399
    with pytest.raises(ValueError): load_collected_service('invalid')


def test_core_app_budget_club_filters_and_similarities(monkeypatch, tmp_path):
    monkeypatch.setenv('TFM_EVENT_LOG', str(tmp_path / 'core_events.jsonl'))
    app = AppTest.from_file(str(ROOT / 'src/app/streamlit_app.py'), default_timeout=45).run()
    assert not app.exception and not app.error
    assert next(s for s in app.selectbox if s.label == 'Modelo de scouting').value == 'Core · seis estilos'
    assert len(next(s for s in app.selectbox if s.label == 'Estilo de juego').options) == 6
    season = next(s for s in app.selectbox if s.label == 'Temporada observada')
    assert season.value == '2023-2024' and '2024-2025' not in season.options
    next(s for s in app.selectbox if s.label == 'Posición').select('FW').run()
    next(s for s in app.selectbox if s.label == 'Excluir club').select('Barcelona').run()
    next(c for c in app.checkbox if c.label == 'Filtrar por valor de mercado').check().run()
    next(n for n in app.number_input if n.label == 'Presupuesto máximo (M€)').set_value(10.0).run()
    next(b for b in app.button if b.label == '🔍 Buscar jugadores').click().run()
    ranking = app.session_state['last_result']
    assert len(ranking) > 0 and ranking.pos.str.contains('FW').all()
    assert ranking.season.eq('2023-2024').all()
    assert ranking.reported_market_value_eur.between(1, 10_000_000).all()
    assert not ranking.clubs.map(lambda value: 'Barcelona' in json.loads(value)).any()
    next(b for b in app.button if b.label == '🔍 Buscar similares').click().run()
    assert not app.exception
    similarities = app.session_state['similar_result']
    assert len(similarities) > 0 and similarities.pos.str.contains('FW').all()
    assert similarities.entity_id.is_unique
    assert similarities.season.eq('2023-2024').all()
    assert similarities.reported_market_value_eur.between(1, 10_000_000).all()
    first = next(s for s in app.selectbox if s.label == 'Primer jugador')
    next(s for s in app.selectbox if s.label == 'Segundo jugador').set_value(first.value).run()
    assert not app.exception
    next(s for s in app.selectbox if s.label == 'Modelo de scouting').select('Ofensivo').run()
    assert not app.exception
    assert next(s for s in app.selectbox if s.label == 'Temporada observada').value == '2024-2025'
    assert len(next(s for s in app.selectbox if s.label == 'Estilo de juego').options) == 2
    assert 'scouting_case' not in app.session_state.filtered_state


def test_radar_preserves_unknown_measurement():
    from src.app.streamlit_app import radar_figure
    service = load_collected_service('offensive')
    rec = service.for_season('2024-2025')
    row = rec.players.iloc[0].copy()
    column = rec.artifacts.feature_cols[0]
    row[column] = np.nan
    figure = radar_figure(row, rec.artifacts.feature_cols, 'unit unknown', rec.players)
    assert figure.data[0].r[0] is None
    assert figure.data[0].connectgaps is False
