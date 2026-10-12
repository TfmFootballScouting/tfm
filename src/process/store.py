"""Operational scouting records. Never uses the MLflow experiment database."""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from src.config import ROOT


def database_path(path=None):
    if path:
        return Path(path)
    if os.getenv('TFM_OPERATIONAL_DB'):
        return Path(os.environ['TFM_OPERATIONAL_DB'])
    if os.getenv('TFM_EVENT_LOG'):
        return Path(os.environ['TFM_EVENT_LOG']).with_suffix('.sqlite')
    return ROOT / 'data/operational/scouting.sqlite'


def connect(path=None):
    target = database_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, timeout=15)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS requests (
      scouting_request_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
      participant_alias TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events (
      event_id INTEGER PRIMARY KEY, scouting_request_id TEXT NOT NULL REFERENCES requests,
      activity TEXT NOT NULL, timestamp TEXT NOT NULL, actor TEXT NOT NULL,
      event_kind TEXT NOT NULL, attributes_json TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS feedback (
      feedback_id INTEGER PRIMARY KEY, scouting_request_id TEXT NOT NULL REFERENCES requests,
      timestamp TEXT NOT NULL, participant_alias TEXT NOT NULL, player_id TEXT NOT NULL,
      decision TEXT NOT NULL CHECK(decision IN ('shortlist','reject','needs_review')),
      usefulness INTEGER CHECK(usefulness BETWEEN 1 AND 5), rationale TEXT NOT NULL);
    ''')
    return db


def persist_event(event, path=None):
    with connect(path) as db:
        db.execute('INSERT OR IGNORE INTO requests VALUES (?,?,?)',
                   (event['case_id'], event['timestamp'], event['attributes'].get('participant_alias', event['actor'])))
        db.execute('INSERT INTO events (scouting_request_id,activity,timestamp,actor,event_kind,attributes_json) VALUES (?,?,?,?,?,?)',
                   (event['case_id'],event['activity'],event['timestamp'],event['actor'],event['event_kind'],json.dumps(event['attributes'],ensure_ascii=False)))


def save_feedback(case_id, alias, player_id, decision, usefulness, rationale, path=None):
    if not all(str(x).strip() for x in (case_id, alias, player_id, rationale)):
        raise ValueError('Request, participant alias, player and rationale required')
    if decision not in {'shortlist','reject','needs_review'} or usefulness not in range(1,6):
        raise ValueError('Invalid decision or usefulness rating')
    timestamp = datetime.now(timezone.utc).isoformat()
    with connect(path) as db:
        db.execute('INSERT INTO feedback (scouting_request_id,timestamp,participant_alias,player_id,decision,usefulness,rationale) VALUES (?,?,?,?,?,?,?)',
                   (case_id,timestamp,alias,str(player_id),decision,usefulness,rationale.strip()))
    return {'player_id':str(player_id),'decision':decision,'usefulness':usefulness,'rationale':rationale.strip()}


def export_events(destination, path=None):
    """JSONL compatible with process discovery, ordered by insertion ID."""
    with connect(path) as db:
        rows = db.execute('SELECT scouting_request_id,activity,timestamp,actor,event_kind,attributes_json FROM events ORDER BY event_id').fetchall()
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w',encoding='utf8') as output:
        for case,activity,timestamp,actor,kind,attributes in rows:
            output.write(json.dumps(dict(case_id=case,activity=activity,timestamp=timestamp,actor=actor,event_kind=kind,attributes=json.loads(attributes)),ensure_ascii=False)+'\n')
    return len(rows)
