"""Run readiness checks and record genuine outcomes, including expected guard failures."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
from src.config import ROOT,MODELS_DIR
from src.data.provenance import sha256


def execute(args):
    result=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    return result.returncode,result.stdout+result.stderr


def run():
    results={'checked_at':datetime.now(timezone.utc).isoformat()}
    code,output=execute([sys.executable,'-m','pytest','-q','--junitxml=reports/test_results.xml'])
    print(output)
    if code:
        raise RuntimeError('Tests failed')
    suites=ET.parse(ROOT/'reports/test_results.xml').getroot()
    results['tests']={k:sum(int(s.get(k,0)) for s in suites.iter('testsuite')) for k in ['tests','failures','errors','skipped']}
    results['tests']['exit_code']=code
    code,output=execute([sys.executable,'-m','pip','check'])
    assert code==0,output
    results['pip_check']='passed'
    before=sha256(ROOT/'data/raw/players_raw.csv')
    processed_before=sha256(ROOT/'data/processed/real/players.parquet')
    code,output=execute([sys.executable,'-m','src.pipeline'])
    assert code!=0 and 'No collected real player statistics' in output,output
    results['default_pipeline_without_collected_stats']='expected_failure_no_synthetic_fallback'
    assert before==sha256(ROOT/'data/raw/players_raw.csv')
    assert processed_before==sha256(ROOT/'data/processed/real/players.parquet')
    code,output=execute([sys.executable,'-m','src.models.train'])
    assert code!=0 and 'final experiments blocked' in output,output
    results['final_training_with_unverified_legacy']='expected_failure_provenance_guard'
    manifest=ROOT/'data/raw/provenance.jsonl'
    records=[json.loads(line) for line in manifest.read_text().splitlines()]
    for record in records:
        assert sha256(ROOT/record['path'])==record['sha256']
    results['raw_snapshot_checksums']={'records_verified':len(records),'unique_snapshots':len(set(r['sha256'] for r in records))}
    notebooks=json.loads((ROOT/'reports/notebook_execution.json').read_text())
    results['notebooks']=notebooks
    for name,url,method in [('streamlit','http://127.0.0.1:8501/_stcore/health','get'),('mlflow','http://127.0.0.1:5000/api/2.0/mlflow/experiments/search','post')]:
        try:
            r=requests.get(url,timeout=5) if method=='get' else requests.post(url,json={'max_results':10},timeout=5)
            assert r.status_code==200
            if name=='streamlit': assert r.text=='ok'
            else: assert 'tfm-scouting-legacy-exploratory' in [x['name'] for x in r.json()['experiments']]
            results[name+'_service']='passed'
        except requests.RequestException:
            results[name+'_service']='unrun_service_not_started'
    results['genuine_process_log']='absent_discovery_blocked' if not (ROOT/'data/events/scouting.jsonl').exists() else 'present_requires_review'
    results['run_id']=json.loads((MODELS_DIR/'metrics.json').read_text())['run_id']
    (ROOT/'reports/verification.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    run()
