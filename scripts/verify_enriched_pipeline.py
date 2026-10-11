"""Verify executed enrichment evidence, tests, provenance and actual MLflow runs."""
from datetime import datetime, timezone
import json
import urllib.request
import xml.etree.ElementTree as ET

import mlflow
from mlflow.tracking import MlflowClient
import nbformat
import pandas as pd

from src.config import ROOT, FEATURE_COLS
from scripts.salimt_history_audit import sha


def run():
    report = json.loads((ROOT / 'reports/enrichment/pipeline.json').read_text())
    for name, digest in {**report['preserved_input_sha256'], **report['outputs_sha256'], **report['code_sha256']}.items():
        if sha(ROOT / name) != digest: raise ValueError(f'Checksum mismatch: {name}')
    raw = json.loads((ROOT / 'reports/salimt_history_audit.json').read_text())
    for name, item in raw['receipt']['files'].items():
        base = ROOT / 'data/raw/sources/salimt_uploaded/histories'
        assert sha(base / (name + '.zip')) == item['archive_sha256']
        assert sha(base / (name + '.txt')) == item['payload_sha256']
    notebook = json.loads((ROOT / 'reports/enrichment/notebook_execution.json').read_text())
    assert notebook['status'] == 'executed' and notebook['error_outputs'] == 0
    assert sha(ROOT / notebook['path']) == notebook['sha256']
    doc = nbformat.read(ROOT / notebook['path'], as_version=4)
    assert all(cell.execution_count is not None for cell in doc.cells if cell.cell_type == 'code')
    xml = ET.parse(ROOT / 'reports/enrichment/full_tests.xml').getroot()
    suites = xml.findall('testsuite')
    totals = {name: sum(int(item.get(name, '0')) for item in suites) for name in ['tests', 'failures', 'errors', 'skipped']}
    assert totals['tests'] >= 90 and all(totals[key] == 0 for key in ['failures', 'errors', 'skipped'])
    seasons = pd.read_parquet(ROOT / 'data/processed/real/collected_enrichment_player_seasons.parquet')
    assert set(FEATURE_COLS) <= set(seasons)
    assert not seasons.duplicated(['source_player_id', 'season', 'league']).any()
    assert not seasons.model_use_eligible.any()
    mlflow.set_tracking_uri('sqlite:///mlflow.db'); client = MlflowClient()
    runs = []
    for name, item in report['new_model_experiments'].items():
        record = client.get_run(item['mlflow_run_id'])
        assert record.info.status == 'FINISHED'
        assert record.data.tags['dataset'] == report['dataset_version']
        assert record.data.tags['learned_dataset'] == item['learned_dataset_version']
        assert record.data.tags['mlflow.source.name'] == 'scripts/enriched_pipeline.py'
        assert record.data.metrics['holdout_mrr'] == item['holdout_mrr']
        runs.append(record.info.run_id)
    health = {}
    for name, url in [('streamlit', 'http://127.0.0.1:8501/_stcore/health'), ('mlflow', 'http://127.0.0.1:5000/health')]:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read().decode().strip()
            assert response.status == 200 and body.lower() == 'ok'
            health[name] = '200 ' + body
    evidence = {'status': 'passed', 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'dataset_version': report['dataset_version'], 'tests': totals, 'notebook': notebook,
        'preserved_files': len(report['preserved_input_sha256']), 'verified_outputs': len(report['outputs_sha256']),
        'verified_finished_MLflow_runs': runs, 'services': health,
        'transfermarkt_fields_entered_model_fit': False, 'cross_source_identity_approvals': 0,
        'historical_budgets_enabled': False}
    (ROOT / 'reports/enrichment/verification.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    run()
