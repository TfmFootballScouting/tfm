"""Verify the executed complete pipeline, true runs, artifacts and app health."""
import json
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.request import urlopen
import nbformat
import pandas as pd
from mlflow.tracking import MlflowClient
from src.config import ROOT
from src.data.provenance import sha256
from src.app.fingerprints import source_sha256
from src.app.trained import load_trained_service


def main():
    folder=ROOT/'reports/five_league_pipeline'
    report=json.loads((folder/'pipeline.json').read_text())
    for path,digest in report['preserved_sha256'].items():assert sha256(ROOT/path)==digest,path
    for path,digest in report['code_sha256'].items():assert source_sha256(ROOT/path)==digest,path
    for item in report['outputs'].values():assert sha256(ROOT/item['path'])==item['sha256'],item['path']
    client=MlflowClient(tracking_uri=f'sqlite:///{ROOT/"mlflow.db"}')
    for name,info in report['experiments'].items():
        assert sha256(ROOT/info['model_path'])==info['model_sha256']
        recorded=client.get_run(info['mlflow_run_id'])
        assert recorded.info.status=='FINISHED' and recorded.data.tags['dataset']==report['dataset_version']
        run=json.loads((folder/'mlflow_export'/name/'run.json').read_text())
        assert run['status']=='FINISHED' and run['run_id']==recorded.info.run_id
        assert run['metrics']==recorded.data.metrics
        count=0
        for category in ['evaluation','models']:
            for item in client.list_artifacts(run['run_id'],category):
                local=folder/'mlflow_export'/name/item.path
                original=ROOT/info['model_path'] if category=='models' else folder/Path(item.path).name
                assert sha256(local)==sha256(original);count+=1
        assert count==info['exported_artifacts']==26
        bootstrap=pd.read_csv(folder/f'{name}_cluster_bootstrap.csv')
        assert bootstrap.trial.nunique()==30
    review=json.loads((folder/'review.json').read_text())
    for item in review['outputs'].values():assert sha256(ROOT/item['path'])==item['sha256']
    assert review['approved_identity_pairs']==0 and not review['model_use_eligible'] and len(review['cases'])==50
    for filename,digest in review['reports_sha256'].items():assert sha256(folder/filename)==digest
    assert sha256(folder/'price_coverage.csv')==review['price_coverage_sha256']
    notebook=json.loads((folder/'notebook_execution.json').read_text())
    assert sha256(ROOT/notebook['path'])==notebook['sha256']
    doc=nbformat.read(ROOT/notebook['path'],as_version=4)
    cells=[cell for cell in doc.cells if cell.cell_type=='code']
    assert len(cells)==8 and all(cell.execution_count is not None for cell in cells)
    assert not any(output.output_type=='error' for cell in cells for output in cell.outputs)
    suites=ET.parse(folder/'tests.xml').getroot().findall('testsuite')
    counts={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','errors','failures','skipped']}
    assert counts['tests']>=111 and not any(counts[key] for key in ['errors','failures','skipped'])
    galleries={}
    for name in ['core','offensive']:
        service=load_trained_service(name)
        rec=service.for_season(service.available_seasons[0])
        assert rec.players.entity_id.is_unique
        galleries[name]=dict(people=len(rec.players),season=service.available_seasons[0],styles=service.supported_styles)
    with urlopen('http://127.0.0.1:8502/_stcore/health',timeout=10) as response:assert response.status==200
    verification=dict(status='passed',checked_at=datetime.now(timezone.utc).isoformat(),dataset_version=report['dataset_version'],
        training_commit=report['git_commit'],preserved_artifacts=len(report['preserved_sha256']),tests=counts,
        notebooks_code_cells=len(cells),notebook_errors=0,real_finished_model_runs=3,exported_artifacts=78,
        source_review_pairs=review['supported_provisional_pairs'],identity_approvals=0,scenarios=50,galleries=galleries,
        streamlit_health=200,actual_transfer_success_validated=False,native_windows_verified=False,
        app_sha256=sha256(ROOT/'src/app/streamlit_app.py'),
        artifact_sha256={str(p.relative_to(ROOT)):sha256(p) for p in folder.rglob('*') if p.is_file() and p.name!='verification.json'})
    (folder/'verification.json').write_text(json.dumps(verification,indent=2))
    print(json.dumps({key:value for key,value in verification.items() if key!='artifact_sha256'},indent=2))

if __name__=='__main__':main()
