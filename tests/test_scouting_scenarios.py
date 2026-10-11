from dataclasses import replace
import json
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest
from src.config import ROOT
from src.app.collected import load_collected_service
from src.app.budget import load_budget_inputs, candidate_links
from src.app.scenarios import Requirements, TEMPLATES, analyze_scenario, run_scenario, overlap

@pytest.fixture(scope='module')
def inputs():
    service = load_collected_service('core')
    rec = service.for_season('2023-2024')
    values, candidates, canonical = load_budget_inputs()
    links = candidate_links(rec.players, candidates, canonical)
    return rec, links, values


def test_real_constraints_cutoff_baselines_and_frozen_model(inputs):
    rec, links, values = inputs
    before = rec.artifacts.scaler.mean_.copy()
    req = Requirements('Valencia', '2023-2024', **TEMPLATES['Ataque vertical'])
    result = analyze_scenario(rec, req, links, values)
    rows = result['shortlist']
    assert len(rows) > 0
    assert rows.pos_main.eq('FW').all() and rows.age.le(25).all() and rows.minutes.ge(900).all()
    assert not rows.clubs.map(lambda clubs: 'Valencia' in json.loads(clubs)).any()
    assert rows.reported_market_value_eur.between(1, 10_000_000).all()
    assert rows.reported_valuation_date.le(req.valuation_cutoff).all()
    assert rows.price_identity_status.eq('provisional_not_reviewed').all()
    assert not rows.historical_budget_eligible.any() and not rows.model_use_eligible.any()
    assert result['funnel']['count'].is_monotonic_decreasing
    assert result['baselines'].eligible.eq(len(result['eligible'])).all()
    assert len(result['sensitivity']) == 6
    np.testing.assert_array_equal(before, rec.artifacts.scaler.mean_)
    # Final results must be exactly the first eligible rows, not filter an earlier top-N.
    assert rows.entity_id.tolist() == result['eligible'].head(req.top_n).entity_id.tolist()


def test_empty_and_invalid_requirements(inputs):
    rec, links, values = inputs
    req = Requirements('Valencia', '2023-2024', **TEMPLATES['Ataque vertical'])
    assert np.isnan(overlap([], []))
    empty = analyze_scenario(rec, replace(req, min_minutes=10000), links, values)
    assert empty['shortlist'].empty and empty['baselines'].shortlist_jaccard.isna().all()
    for changes in [dict(season='2024-2025'), dict(budget_million=float('inf')), dict(club='Invented club'),
                    dict(min_minutes=0), dict(position='GK'), dict(top_n=0)]:
        with pytest.raises(ValueError): run_scenario(rec, replace(req, **changes), links, values)


def test_scenario_app_execution_export_and_stale_invalidation(monkeypatch, tmp_path):
    log = tmp_path / 'scenario_events.jsonl'
    monkeypatch.setenv('TFM_EVENT_LOG', str(log))
    app = AppTest.from_file(str(ROOT/'src/app/streamlit_app.py'), default_timeout=60).run()
    assert not app.exception
    next(s for s in app.selectbox if s.label == 'Plantilla de requisitos').select('Ataque vertical').run()
    next(b for b in app.button if b.label == 'Ejecutar escenario').click().run()
    assert not app.exception
    rows = app.session_state['scenario_result']['shortlist']
    assert len(rows) > 0 and rows.reported_valuation_date.le('2024-06-30').all()
    case = app.session_state['scenario_case']
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert [e['activity'] for e in events if e['case_id'] == case] == ['need_defined', 'search_executed', 'ranking_generated']
    next(b for b in app.button if b.label == 'Registrar revisión del escenario').click().run()
    assert json.loads(log.read_text().splitlines()[-1])['activity'] == 'shortlist_reviewed'
    next(n for n in app.number_input if n.label == 'Edad máxima del escenario').set_value(24).run()
    assert 'scenario_result' not in app.session_state.filtered_state
    assert 'scenario_case' not in app.session_state.filtered_state
