import json
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.config import ROOT
from src.app.trained import load_trained_service
from src.data.provenance import sha256
from src.data.source_rights import require_model_data_use
from src.models.collected import EXPERIMENTS,cohorts
from src.models.recommend import PlayerRecommender


def test_actual_refits_train_only_and_preserved_evidence():
    report=json.loads((ROOT/'reports/five_league_pipeline/pipeline.json').read_text())
    for path,digest in report['preserved_sha256'].items():assert sha256(ROOT/path)==digest,path
    for name,spec in EXPERIMENTS.items():
        info=report['experiments'][name]
        frame=pd.read_parquet(ROOT/report['outputs']['offensive_gallery' if name=='offensive' else 'core_gallery']['path'])
        parts=cohorts(frame,spec['split'])
        rec=PlayerRecommender.load(ROOT/info['model_path'])
        assert set(rec.players.player_id)==set(parts['train'].player_id)
        assert set(rec.players.league)=={'La Liga','Premier League','Bundesliga','Serie A','Ligue 1'}
        assert rec.players.season.max()<parts['validation'].season.min()<parts['holdout'].season.min()
        np.testing.assert_allclose(rec.artifacts.imputer.statistics_,parts['train'][spec['features']].median())
        imputed=rec.artifacts.imputer.transform(parts['train'][spec['features']])
        np.testing.assert_allclose(rec.artifacts.scaler.mean_,imputed.mean(axis=0))
        assert not any('market' in f or 'salimt' in f for f in rec.artifacts.feature_cols)
        queries=pd.read_csv(ROOT/f'reports/five_league_pipeline/{name}_queries.csv')
        selected=queries[queries.phase.eq('holdout')&queries.method.eq(info['selected_method'])]
        assert selected.entity_id.is_unique
        assert len(selected)==len(set(parts['validation'].entity_id)&set(parts['holdout'].entity_id))
        assert selected.candidate_count.eq(len(parts['holdout'])).all()
        run=json.loads((ROOT/f'reports/five_league_pipeline/mlflow_export/{name}/run.json').read_text())
        assert run['status']=='FINISHED' and run['tags']['dataset']==report['dataset_version']


def test_private_review_is_not_training_and_scenarios_are_actual():
    folder=ROOT/'reports/five_league_pipeline'
    report=json.loads((folder/'review.json').read_text())
    preview=pd.read_parquet(ROOT/report['outputs']['preview']['path'])
    with pytest.raises(ValueError):require_model_data_use(preview)
    assert report['approved_identity_pairs']==0 and report['supported_provisional_pairs']>1119
    assert len(report['cases'])==50
    rows=pd.read_csv(folder/'scenario_shortlists.csv')
    assert not rows.historical_budget_eligible.any() and not rows.model_use_eligible.any()
    assert rows.price_identity_status.eq('provisional_not_reviewed').all()
    assert pd.to_datetime(rows.reported_valuation_date).le(pd.to_datetime(rows.reported_valuation_cutoff)).all()
    assert rows.reported_market_value_eur.gt(0).all()
    assert all(len(group)==group.entity_id.nunique() for _,group in rows.groupby('case_id'))


def test_retrained_app_serves_prices_and_switches_models(monkeypatch,tmp_path):
    monkeypatch.setenv('TFM_EVENT_LOG',str(tmp_path/'eu_pipeline_events.jsonl'))
    app=AppTest.from_file(str(ROOT/'src/app/streamlit_app.py'),default_timeout=60).run()
    assert not app.exception and not app.error
    assert next(s for s in app.selectbox if s.label=='Entrenamiento').value=='Cinco ligas · reentrenado'
    next(s for s in app.selectbox if s.label=='Liga').select('Premier League').run()
    next(c for c in app.checkbox if c.label=='Filtrar por valor de mercado').check().run()
    rows=app.session_state['last_result']
    assert len(rows)>0 and rows.league.eq('Premier League').all()
    assert rows.reported_value_screenable.all() and rows.price_identity_status.eq('provisional_not_reviewed').all()
    next(s for s in app.selectbox if s.label=='Entrenamiento').select('La Liga · original').run()
    assert not app.exception
    assert app.session_state['last_filters'][-1]=='La Liga · original'
    next(s for s in app.selectbox if s.label=='Entrenamiento').select('Cinco ligas · reentrenado').run()
    next(s for s in app.selectbox if s.label=='Modelo de scouting').select('Ofensivo').run()
    assert not app.exception
    assert next(s for s in app.selectbox if s.label=='Temporada observada').value=='2024-2025'


def test_trained_serving_preserves_parameters_and_six_core_styles():
    service=load_trained_service('core')
    mean=service.model.artifacts.scaler.mean_.copy()
    rec=service.for_season('2023-2024')
    assert len(rec.players)==1810 and len(service.supported_styles)==6
    np.testing.assert_array_equal(mean,service.model.artifacts.scaler.mean_)
    with pytest.raises(ValueError):service.for_season('2025-2026')
