import json
import pytest
from src.process.events import record_event,discover


def test_formal_event_log_and_discovery(tmp_path):
    p=tmp_path/'unit_test_events.jsonl'
    for activity in ['need_defined','search_executed','ranking_generated']:
        record_event('test-case',activity,'test-runner',path=p)
    dfg,cases=discover(p)
    assert dfg['count'].sum()==2
    assert not cases.complete.any()
    assert (dfg.median_seconds>=0).all()


def test_simulation_excluded(tmp_path):
    p=tmp_path/'synthetic.jsonl'
    event=record_event('case','need_defined','test-runner',path=p)
    event['event_kind']='simulation';p.write_text(json.dumps(event)+'\n')
    with pytest.raises(ValueError,match='Simulated'):
        discover(p)


def test_missing_genuine_log_is_blocked(tmp_path):
    with pytest.raises(ValueError,match='No genuine'):
        discover(tmp_path/'absent.jsonl')
