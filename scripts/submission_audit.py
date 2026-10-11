"""Read-only first-submission inventory; no data downloads or model refits."""
import json
import subprocess
from datetime import datetime, timezone
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import nbformat
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.app.collected import load_collected_service


def main():
    destination=ROOT/'reports/submission'
    destination.mkdir(exist_ok=True)
    pipeline=json.loads((ROOT/'reports/enrichment/pipeline.json').read_text())
    protected={**pipeline['preserved_input_sha256'],**pipeline['outputs_sha256'],**pipeline['code_sha256']}
    for path,digest in protected.items():
        if sha256(ROOT/path)!=digest: raise ValueError(f'Changed protected artifact: {path}')
    scenarios=json.loads((ROOT/'reports/scouting_scenarios/results.json').read_text())
    for path,digest in scenarios['code_sha256'].items(): assert sha256(ROOT/path)==digest,path
    for path,digest in scenarios['output_sha256'].items(): assert sha256(ROOT/'reports/scouting_scenarios'/path)==digest,path
    notebooks=[]
    for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
        doc=nbformat.read(path,as_version=4)
        cells=[c for c in doc.cells if c.cell_type=='code']
        errors=sum(o.output_type=='error' for c in cells for o in c.get('outputs',[]))
        executed=sum(c.execution_count is not None for c in cells)
        notebooks.append(dict(path=str(path.relative_to(ROOT)),code_cells=len(cells),executed=executed,errors=errors,sha256=sha256(path)))
        assert cells and executed==len(cells) and errors==0,path
    models={}
    for name,info in pipeline['new_model_experiments'].items():
        path=ROOT/f'reports/enrichment/mlflow_export/{name}/run.json'
        run=json.loads(path.read_text())
        assert run['status']=='FINISHED' and run['run_id']==info['mlflow_run_id']
        for tag in ['owner','dataset','environment','project','git_commit']: assert run['tags'].get(tag),tag
        models[name]=dict(run_id=run['run_id'],status=run['status'],mrr=info['holdout_mrr'],recall_at_5=info['holdout_recall_at_5'])
    dictionary=pd.read_csv(ROOT/'reports/enrichment/dictionary.csv')
    assert {'table','column','definition','unit'}<=set(dictionary)
    assert not dictionary.duplicated(['table','column']).any()
    suites=ET.parse(destination/'tests.xml').getroot().findall('testsuite')
    tests={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','errors','failures','skipped']}
    assert tests['tests']>=101 and not any(tests[key] for key in ['errors','failures','skipped'])
    health={}
    for service,url in [('streamlit','http://127.0.0.1:8501/_stcore/health'),('mlflow','http://127.0.0.1:5000/health')]:
        with urlopen(url,timeout=10) as response:
            assert response.status==200
            health[service]=dict(status=response.status,body=response.read().decode())
    galleries={name:{season:len(service.gallery[service.gallery.season.eq(season)]) for season in service.available_seasons}
               for name in ['core','offensive'] for service in [load_collected_service(name)]}
    report=dict(status='passed_current_retained_workspace',checked_at=datetime.now(timezone.utc).isoformat(),
                git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256=sha256(ROOT/'scripts/submission_audit.py'), tests_xml_sha256=sha256(destination/'tests.xml'),
                protected_artifacts_verified=len(protected),tests=tests,notebooks=notebooks,models=models,
                dictionary_rows=len(dictionary),galleries=galleries,services=health,
                scenarios=len(scenarios['cases']),fresh_checkout_verified=False,remote_ci_verified=False,
                actual_transfer_success_validated=False,
                limitations=['Private ignored datasets require retained workspace or authorized checksum-verified restoration',
                             'Price identities provisional and original publication time unknown',
                             'Advanced Segunda gallery unavailable; 2025/26 coverage incomplete',
                             'Genuine human process data insufficient for empirical scouting-process validation'])
    (destination/'audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({key:report[key] for key in ['status','protected_artifacts_verified','tests','dictionary_rows','scenarios','services']},indent=2))

if __name__=='__main__': main()
