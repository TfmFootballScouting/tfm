"""Check completed scenario artifacts, executed notebook, tests and app health."""
import json
import xml.etree.ElementTree as ET
from urllib.request import urlopen
import nbformat
from src.config import ROOT
from src.data.provenance import sha256


def main():
    directory=ROOT/'reports/scouting_scenarios'
    report=json.loads((directory/'results.json').read_text())
    for path,digest in report['code_sha256'].items(): assert sha256(ROOT/path)==digest, path
    for path,digest in report['output_sha256'].items(): assert sha256(directory/path)==digest, path
    assert len(report['cases'])==10 and not report['model_retrained'] and not report['transfer_success_validated']
    evidence=json.loads((directory/'notebook_execution.json').read_text())
    assert sha256(ROOT/evidence['path'])==evidence['sha256']
    notebook=nbformat.read(ROOT/evidence['path'],as_version=4)
    code=[cell for cell in notebook.cells if cell.cell_type=='code']
    assert len(code)==4 and all(cell.execution_count is not None for cell in code)
    assert not any(output.output_type=='error' for cell in code for output in cell.outputs)
    suites=ET.parse(directory/'tests.xml').getroot().findall('testsuite')
    counts={key:sum(int(suite.attrib.get(key,0)) for suite in suites) for key in ['tests','errors','failures','skipped']}
    assert counts['tests']>=101 and not any(counts[key] for key in ['errors','failures','skipped'])
    with urlopen('http://127.0.0.1:8501/_stcore/health',timeout=10) as response:
        assert response.status==200 and response.read()==b'ok'
    verification=dict(status='passed', tests=counts, notebook_code_cells=len(code), notebook_errors=0,
                      scenarios=len(report['cases']), streamlit_health=200,
                      protected_artifacts_verified=report['protected_artifacts_verified'],
                      git_source_commit=report['git_commit'],
                      app_sha256=sha256(ROOT/'src/app/streamlit_app.py'),
                      ui_sha256=sha256(ROOT/'src/app/scenario_ui.py'),
                      tests_sha256=sha256(ROOT/'tests/test_scouting_scenarios.py'))
    (directory/'verification.json').write_text(json.dumps(verification,indent=2))
    print(json.dumps(verification,indent=2))

if __name__=='__main__': main()
