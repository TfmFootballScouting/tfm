"""Formal append-only event log; actual app activity only, tests use a separate path."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from src.config import ROOT

ACTIVITIES = ['need_defined','search_executed','ranking_generated','shortlist_reviewed','decision_recorded']


def record_event(case_id, activity, actor, attributes=None, path=None):
    if not case_id or activity not in ACTIVITIES or not actor:
        raise ValueError('Valid case ID, activity and actor required')
    path = Path(path or os.getenv('TFM_EVENT_LOG', str(ROOT / 'data/events/scouting.jsonl')))
    path.parent.mkdir(parents=True,exist_ok=True)
    event = dict(case_id=str(case_id), activity=activity, timestamp=datetime.now(timezone.utc).isoformat(),
                 actor=actor, event_kind='observed_application', attributes=attributes or {})
    with path.open('a',encoding='utf8') as f:
        f.write(json.dumps(event,ensure_ascii=False)+'\n')
    return event


def discover(path):
    """Directly-follows discovery from observed ordered cases; no simulation fallback."""
    path=Path(path)
    if not path.exists() or not path.stat().st_size:
        raise ValueError('No genuine event log available; process discovery blocked')
    events=pd.read_json(path,lines=True)
    required={'case_id','activity','timestamp','actor','event_kind'}
    if not required <= set(events):
        raise ValueError('Incomplete event schema')
    if not (events.event_kind=='observed_application').all():
        raise ValueError('Simulated/test logs cannot enter genuine process discovery')
    if events[list(required)].isna().any().any() or not events.activity.isin(ACTIVITIES).all():
        raise ValueError('Invalid event values')
    events['timestamp']=pd.to_datetime(events.timestamp,utc=True,errors='raise')
    edges=[]
    cases=[]
    for case,group in events.groupby('case_id',sort=False):
        if not group.timestamp.is_monotonic_increasing:
            raise ValueError('Timestamps out of order within a case')
        for i in range(1,len(group)):
            a,b=group.iloc[i-1],group.iloc[i]
            edges.append(dict(source=a.activity,target=b.activity,elapsed_seconds=(b.timestamp-a.timestamp).total_seconds()))
        cases.append(dict(case_id=case,events=len(group),complete=group.iloc[-1].activity=='decision_recorded',
                          elapsed_seconds=(group.timestamp.iloc[-1]-group.timestamp.iloc[0]).total_seconds()))
    frame=pd.DataFrame(edges,columns=['source','target','elapsed_seconds'])
    dfg=frame.groupby(['source','target']).agg(count=('elapsed_seconds','size'),median_seconds=('elapsed_seconds','median')).reset_index()
    return dfg,pd.DataFrame(cases)
