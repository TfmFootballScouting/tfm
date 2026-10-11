"""Optional private expanded identity proposals for post-ranking price screening."""
import json
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.app import budget


def load_europe_budget_inputs():
    values,candidates,fbref=budget.load_budget_inputs()
    report_path=ROOT/'reports/five_league_pipeline/review.json'
    if not report_path.exists():return values,candidates,fbref
    report=json.loads(report_path.read_text())
    item=report['outputs']['candidates']
    path=ROOT/item['path']
    if not path.exists():return values,candidates,fbref
    if sha256(path)!=item['sha256']:raise ValueError('European private candidate fingerprint changed')
    pipeline=json.loads((ROOT/'reports/five_league_pipeline/pipeline.json').read_text())
    item=pipeline['outputs']['player_seasons']
    if sha256(ROOT/item['path'])!=item['sha256']:raise ValueError('European identity bridge fingerprint changed')
    return values,pd.read_parquet(path),pd.read_parquet(ROOT/item['path'])
