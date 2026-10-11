"""Integration checks against the separately prepared legacy exploratory model."""
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from src.config import MODELS_DIR, ROOT


def test_app_real_exploratory_workflow(monkeypatch,tmp_path):
    assert (MODELS_DIR/'metrics.json').exists(), 'Prepare the documented exploratory pipeline before application integration tests'
    monkeypatch.setenv('TFM_EVENT_LOG',str(tmp_path/'app_test_events.jsonl'))
    app=AppTest.from_file(str(ROOT/'src/app/streamlit_app.py'),default_timeout=30).run()
    next(s for s in app.selectbox if s.label=='Modelo de scouting').select('Exploración heredada').run()
    assert not app.exception
    assert not app.error
    assert any('procedencia' in warning.value for warning in app.warning)
    assert app.dataframe, 'A functional default ranking must be rendered'
    style=next(s for s in app.selectbox if s.label=='Estilo de juego')
    assert len(style.options)==2, 'Unsupported tactical styles must not be offered with goal/assist-only features'
    position=next(s for s in app.selectbox if s.label=='Posición')
    position.select('FW')
    next(b for b in app.button if b.label=='🔍 Buscar jugadores').click().run()
    assert not app.exception
    ranking=app.session_state['last_result']
    assert len(ranking)>0
    assert ranking.pos.str.contains('FW').all()
    assert 'budget_est' not in ranking
    events=[json.loads(x) for x in (tmp_path/'app_test_events.jsonl').read_text().splitlines()]
    assert [x['activity'] for x in events]==['need_defined','search_executed','ranking_generated']
    next(b for b in app.button if b.label=='🔍 Buscar similares').click().run()
    assert not app.exception
    next(b for b in app.button if b.label=='Registrar revisión de shortlist').click().run()
    assert not app.exception
    events=[json.loads(x) for x in (tmp_path/'app_test_events.jsonl').read_text().splitlines()]
    assert events[-1]['activity']=='shortlist_reviewed'
