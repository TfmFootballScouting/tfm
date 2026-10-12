import json
import sqlite3
import pytest
from src.process.store import connect, persist_event, save_feedback, export_events


def test_request_feedback_and_export(tmp_path):
    db = tmp_path/'operations.sqlite'
    event = dict(case_id='request-1',activity='need_defined',timestamp='2026-10-12T10:00:00+00:00',actor='expert-a',event_kind='observed_application',attributes={'player_ids':['fb-1']})
    persist_event(event, db)
    save_feedback('request-1','expert-a','fb-1','shortlist',4,'Suitable role',db)
    with connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM requests').fetchone()[0] == 1
        assert conn.execute('SELECT decision,usefulness FROM feedback').fetchone() == ('shortlist',4)
    output=tmp_path/'events.jsonl'
    assert export_events(output,db)==1
    assert json.loads(output.read_text())['attributes']['player_ids']==['fb-1']
    with pytest.raises(sqlite3.IntegrityError):
        save_feedback('unknown','expert-a','fb-1','shortlist',4,'Suitable role',db)
    with pytest.raises(ValueError):
        save_feedback('request-1','expert-a','fb-1','shortlist',9,'Invalid',db)
