import json
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest
from src.config import ROOT
from src.app.trained import load_trained_service
from src.app.player_analysis import load_analysis_shots,shot_map,development_plot_data


def test_real_shot_loading_and_zero_xg_events_remain_visible():
    shots=load_analysis_shots()
    assert set(shots.league)=={'La Liga','Premier League','Bundesliga','Serie A','Ligue 1'}
    assert len(shots)==228785
    zero=shots[shots.xG.eq(0)&shots.result.ne('OwnGoal')].head(8)
    fig=shot_map(zero)
    assert sum(len(trace.x) for trace in fig.data)==len(zero)
    assert len(zero)>0
    assert all((np.asarray(trace.marker.size)>0).all() for trace in fig.data)


def test_development_plot_has_unknown_gaps_without_changing_source():
    history=load_trained_service('core').history.copy()
    group=next(g for _,g in history[~history.partial_season].groupby(['entity_id','league']) if 1<len(g)<4)
    original=group.copy(deep=True)
    group['Jugador del historial']=group.player.iloc[0]
    axis=sorted(history[~history.partial_season].season.unique())
    result=development_plot_data(group,axis)
    absent=result[~result.season.isin(original.season)]
    assert absent.minutes.isna().all() and absent.gls_p90.isna().all()
    actual=result[result.season.isin(original.season)].set_index('season')
    expected=original.set_index('season')
    np.testing.assert_allclose(actual.gls_p90,expected.loc[actual.index].gls_p90,equal_nan=True)


def test_app_development_shots_partial_and_missing_coverage(monkeypatch,tmp_path):
    monkeypatch.setenv('TFM_EVENT_LOG',str(tmp_path/'analytics_events.jsonl'))
    app=AppTest.from_file(str(ROOT/'src/app/streamlit_app.py'),default_timeout=60).run()
    assert not app.exception and not app.error
    assert any('Evolución del jugador' in t.label for t in app.tabs)
    assert any('Análisis de tiros' in t.label for t in app.tabs)
    source=load_trained_service('core').history
    eligible=source[~source.partial_season & source.minutes.ge(450)].sort_values('season').drop_duplicates('entity_id',keep='last')
    pair=next(g for _,g in eligible.groupby(['player','league']) if len(g)>1)
    names=pair.entity_id.head(2).tolist()+eligible[~eligible.entity_id.isin(pair.entity_id)].entity_id.head(1).tolist()
    next(s for s in app.multiselect if s.label=='Jugadores para ver su evolución').set_value(names).run()
    assert not app.exception
    chart=next(c for c in app.get('plotly_chart') if c.proto.id.endswith('development_chart'))
    traces=json.loads(chart.proto.spec)['data']
    assert len(traces)>=2 and len({t['name'] for t in traces})==len(traces)
    next(s for s in app.selectbox if s.label=='Liga para analizar tiros').select('Serie A').run()
    assert any('374/380' in w.value for w in app.warning)
    next(c for c in app.checkbox if c.label=='Incluir temporadas parciales de tiros').check().run()
    next(s for s in app.selectbox if s.label=='Temporada de tiros').select('2025-2026').run()
    assert any('Temporada parcial' in w.value for w in app.warning)
    next(s for s in app.multiselect if s.label=='Situaciones de tiro').set_value([]).run()
    assert not app.exception and any('No hay tiros' in i.value for i in app.info)
    next(s for s in app.multiselect if s.label=='Ligas').set_value(['La Liga']).run()
    assert not app.exception
    assert next(s for s in app.selectbox if s.label=='Liga para analizar tiros').value=='La Liga'


def test_cross_league_transfer_season_stays_separate():
    history=load_trained_service('core').history.copy()
    overlapping=history[history.duplicated(['entity_id','season'],keep=False)]
    entity=overlapping.entity_id.iloc[0]
    real=history[history.entity_id.eq(entity)].copy()
    real['Jugador del historial']=real.player+' · '+real.league
    chart=development_plot_data(real,sorted(history.season.unique()))
    actual=chart[chart.minutes.notna()]
    keys=['entity_id','league','season']
    assert len(actual)==len(real)
    expected=real.set_index(keys).sort_index()
    observed=actual.set_index(keys).sort_index()
    np.testing.assert_allclose(observed.minutes,expected.minutes)
    assert set(actual.league)==set(real.league)


def test_optional_four_league_files_missing_keeps_existing_laliga(monkeypatch,tmp_path):
    import shutil
    import src.app.player_analysis as analysis
    path=tmp_path/'data/processed/real/collected_understat_shots.parquet'
    path.parent.mkdir(parents=True)
    shutil.copyfile(ROOT/'data/processed/real/collected_understat_shots.parquet',path)
    report=tmp_path/'reports/collected_preprocessing.json'
    report.parent.mkdir(parents=True)
    shutil.copyfile(ROOT/'reports/collected_preprocessing.json',report)
    analysis.load_analysis_shots.clear()
    try:
        monkeypatch.setattr(analysis,'ROOT',tmp_path)
        shots=analysis.load_analysis_shots()
        assert len(shots)==45847 and shots.league.eq('La Liga').all()
    finally:
        analysis.load_analysis_shots.clear()
