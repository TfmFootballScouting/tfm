"""Verify released five-league data, source fingerprints and actual app checks."""
import json
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from urllib.request import urlopen
import nbformat
from src.config import ROOT
from src.data.provenance import sha256
from src.app.fingerprints import source_sha256
from src.app.leagues import load_top_five_service, LEAGUES


def main():
    destination=ROOT/'reports/top_five_leagues'
    report=json.loads((destination/'manifest.json').read_text())
    for path,digest in report['code_sha256'].items(): assert source_sha256(ROOT/path)==digest,path
    for filename,digest in report['report_sha256'].items(): assert sha256(destination/filename)==digest,filename
    previous=json.loads((ROOT/'reports/enrichment/pipeline.json').read_text())
    protected={**previous['preserved_input_sha256'],**previous['outputs_sha256'],**previous['code_sha256']}
    protected_verified=0
    protected_missing=[]
    for path,digest in protected.items():
        if (ROOT/path).exists():
            assert sha256(ROOT/path)==digest,path
            protected_verified+=1
        else: protected_missing.append(path)
    raw_verified=0
    raw_missing=[]
    for item in report['raw_sources']:
        if (ROOT/item['path']).exists():
            assert sha256(ROOT/item['path'])==item['sha256'],item['path']
            raw_verified+=1
        else: raw_missing.append(item['path'])
    for item in report['outputs'].values(): assert sha256(ROOT/item['path'])==item['sha256'],item['path']
    models={}
    for name in ['core','offensive']:
        service=load_top_five_service(name)
        rec=service.for_season(service.available_seasons[0])
        assert rec.players.entity_id.is_unique
        counts=rec.players.groupby('league').size().to_dict()
        assert set(counts)==set(LEAGUES) and min(counts.values())>300
        models[name]=dict(season=service.available_seasons[0],league_players=counts,styles=service.supported_styles)
    notebook=json.loads((destination/'notebook_execution.json').read_text())
    assert sha256(ROOT/notebook['path'])==notebook['sha256']
    doc=nbformat.read(ROOT/notebook['path'],as_version=4)
    cells=[cell for cell in doc.cells if cell.cell_type=='code']
    assert len(cells)==4 and all(cell.execution_count is not None for cell in cells)
    assert not any(output.output_type=='error' for cell in cells for output in cell.outputs)
    suites=ET.parse(destination/'tests.xml').getroot().findall('testsuite')
    tests={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','errors','failures','skipped']}
    assert tests['tests']>=107 and not any(tests[key] for key in ['errors','failures','skipped'])
    with urlopen('http://127.0.0.1:8502/_stcore/health',timeout=10) as response:
        assert response.status==200 and response.read()==b'ok'
    verification=dict(status='passed_released_outputs',checked_at=datetime.now(timezone.utc).isoformat(),
        source_commit=report['git_commit'],dataset_version=report['dataset_version'],tests=tests,
        historical_protected_verified=protected_verified,historical_protected_missing=protected_missing,
        raw_archives_verified=raw_verified,raw_archives_missing=raw_missing,models=models,
        notebook_cells=len(cells),notebook_errors=0,streamlit_health=200,
        browser_note='Chromium desktop 1440x1000 and mobile390x844: no page errors or document horizontal overflow; screenshots reviewed locally',
        native_windows_verified=False,model_retrained=False,transfer_success_validated=False)
    (destination/'verification.json').write_text(json.dumps(verification,indent=2))
    print(json.dumps(verification,indent=2))

if __name__=='__main__':main()
