import numpy as np
from streamlit.testing.v1 import AppTest
from src.app.ui_helpers import group_profiles, LABELS
from src.app.model_loader import load_scouting_service
from src.config import ROOT


def test_exploratory_grouping_uses_real_profiles_without_changing_models():
    service=load_scouting_service()
    rec=service.for_season('2023-2024')
    frozen=rec.artifacts.kmeans.cluster_centers_.copy()
    matrix=rec.X.copy()
    for number in [3,7]:
        grouped=group_profiles(rec.X, rec.players, number)
        assert grouped.group.nunique()==number
        assert grouped.player_id.tolist()==rec.players.player_id.tolist()
        assert grouped.groupby('group').size().sum()==1810
    np.testing.assert_array_equal(frozen, rec.artifacts.kmeans.cluster_centers_)
    np.testing.assert_array_equal(matrix, rec.X)
    assert all(c in LABELS for c in rec.artifacts.feature_cols)


def test_scout_compare_three_histories_and_group_members(monkeypatch,tmp_path):
    monkeypatch.setenv('TFM_EVENT_LOG',str(tmp_path/'events.jsonl'))
    app=AppTest.from_file(str(ROOT/'src/app/streamlit_app.py'),default_timeout=60).run()
    next(s for s in app.multiselect if s.label=='Ligas').set_value(['Premier League','Bundesliga']).run()
    service=load_scouting_service()
    gallery=service.for_season('2023-2024').players
    ids=gallery[gallery.league.isin(['Premier League','Bundesliga'])].player_id.head(3).astype(int).tolist()
    next(s for s in app.multiselect if s.label=='Jugadores a comparar').set_value(ids).run()
    assert not app.exception
    expanders=[e for e in app.expander if e.label.startswith('Perfil e historial')]
    assert len(expanders)==3
    for identifier, expander in zip(ids,expanders):
        entity=gallery[gallery.player_id.eq(identifier)].entity_id.iloc[0]
        expected=service.history[service.history.entity_id.eq(entity)]
        history=expander.dataframe[0].value
        assert len(history)==len(expected)
        assert set(history.Temporada)==set(expected.season)
    next(s for s in app.slider if s.label=='Número de grupos').set_value(4).run()
    members=app.session_state['explore_group_members']
    assert members.group.nunique()==4
    chosen=int(members.group.max())
    next(s for s in app.selectbox if s.label=='Grupo a explorar').set_value(chosen).run()
    assert not app.exception
    assert any(set(d.value.Jugador)==set(gallery[gallery.player_id.isin(members[members.group.eq(chosen)].player_id)].player)
               for d in app.dataframe if 'Goles por 90 min' in d.value.columns and 'Jugador' in d.value.columns)
    assert not any(any('_p90' in str(c) for c in d.value.columns) for d in app.dataframe)
