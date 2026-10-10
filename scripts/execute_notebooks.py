"""Execute authored notebooks with the selected environment kernel, fail on errors."""
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient
ROOT=Path(__file__).resolve().parents[1]
results=[]
for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
    nb=nbformat.read(path,as_version=4)
    NotebookClient(nb,timeout=180,kernel_name='tfm-python',resources={'metadata':{'path':str(ROOT)}}).execute()
    # Host execution paths in traceback outputs are absent on success; no secrets are read.
    nbformat.write(nb,path)
    result=dict(notebook=path.relative_to(ROOT).as_posix(),status='executed',
                code_cells=sum(c.cell_type=='code' for c in nb.cells))
    results.append(result);print(result,flush=True)
(ROOT/'reports/notebook_execution.json').write_text(json.dumps(results,indent=2))
