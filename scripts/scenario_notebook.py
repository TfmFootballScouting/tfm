"""Execute the real-observation scouting scenario analysis."""
import json
import os
import nbformat as nb
from nbclient import NotebookClient
from src.config import ROOT
from src.data.provenance import sha256


def main():
    os.environ.setdefault('JUPYTER_PATH', str(ROOT/'.jupyter/share/jupyter'))
    os.environ.setdefault('IPYTHONDIR', '/tmp/tfm-ipython')
    os.environ.setdefault('JUPYTER_RUNTIME_DIR', '/tmp/tfm-jupyter')
    cells = [
        ('md', '# Scouting scenarios with real observations\n\nIllustrative, adjustable club requirements, not official club plans or budgets. Each case represents **one vacancy** and the shortlist contains alternatives. The models use frozen FBref transformations. Uploaded reported market assessments screen the ranking afterwards; they are not transfer fees, predictions, training features or verified historical information.'),
        ('code', '''from pathlib import Path
import os, sys, json
ROOT = Path.cwd()
while not (ROOT/'src/config.py').exists():
    if ROOT == ROOT.parent: raise RuntimeError('Run inside the repository')
    ROOT = ROOT.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
import pandas as pd
from IPython.display import display, Markdown
from src.data.provenance import sha256
report=json.loads((ROOT/'reports/scouting_scenarios/results.json').read_text())
for name, digest in report['output_sha256'].items():
    assert sha256(ROOT/'reports/scouting_scenarios'/name)==digest, name
cases=pd.DataFrame([{**case['requirements'], 'case_id':case['case_id'], 'eligible':case['eligible'], 'returned':case['returned']} for case in report['cases']])
display(cases)
display(Markdown('Dataset version: `'+report['dataset_version']+'`. No models were retrained.'))
'''),
        ('md', '## Coverage and feasibility\n\nCore uses validation 2022/23 and held-out 2023/24 seasons; offensive uses validation 2023/24 and held-out 2024/25. These seasons follow each model’s training period. Prices use the latest reported effective date no later than June 30 of the observed season. This aligns the snapshot but does not establish that the value was published or known then. Broad historical FBref positions are retained; FW is not proof of a winger role. Players with any own-club stint are excluded. Unknown ages and unknown, zero or unmatched prices cannot pass their constraints.'),
        ('code', '''funnel=pd.read_csv(ROOT/'reports/scouting_scenarios/funnel.csv')
display(funnel.pivot(index='case_id', columns='stage', values='count'))
for case, rows in funnel.groupby('case_id',sort=False):
    assert rows['count'].is_monotonic_decreasing
empty=int(cases.returned.eq(0).sum())
short=int(cases.returned.lt(cases.top_n).sum())
display(Markdown(f"**{empty}** cases have no feasible players; **{short}** return fewer alternatives than requested. Constraints are never relaxed automatically. Coverage exclusions describe source availability and selection bias, not poor player quality."))
'''),
        ('md', '## Baselines and requirement sensitivity\n\nGoals+assists per 90, goals per 90 and seeded random selection rank exactly the same eligible pool. Top-list Jaccard measures selection agreement, not recommendation relevance, statistical superiority or transfer success. Defensive and possession requirements should not be judged by goals alone. Budget and minutes vary ±20%; age varies ±2 years. Actual observed player measurements are unchanged. Empty/empty comparisons remain unknown.'),
        ('code', '''baselines=pd.read_csv(ROOT/'reports/scouting_scenarios/baselines.csv')
sensitivity=pd.read_csv(ROOT/'reports/scouting_scenarios/sensitivity.csv')
display(baselines.groupby(['model','baseline']).shortlist_jaccard.agg(['count','mean','min','max']))
display(sensitivity.groupby(['model','variation']).agg(cases=('case_id','size'),mean_eligible=('eligible','mean'),mean_overlap=('shortlist_jaccard','mean'),min_overlap=('shortlist_jaccard','min')))
unstable=sensitivity[sensitivity.shortlist_jaccard.lt(.5)]
display(unstable)
display(Markdown(f"**{len(unstable)}** perturbed cases have Jaccard below 0.5. This is a transparent descriptive threshold, not a calibrated significance test. Low overlap means the shortlist depends strongly on the selected requirements; human review should consider alternatives near each boundary."))
'''),
        ('md', '## Qualitative shortlist review\n\nInspect observed age, minutes, goals/assists and affinity alongside the source value date. The affinity is an expert-weight cosine score, not a probability or independently validated tactical fit. Remaining candidates require video, role and injury review, identity verification and actual fee negotiation. Desborde uses a broad FW proxy and measured model features; it cannot certify a winger. This local output contains provisional provider data and is excluded from Git.'),
        ('code', '''shortlist=pd.read_csv(ROOT/'reports/scouting_scenarios/shortlist.csv')
assert not shortlist.historical_budget_eligible.any()
assert shortlist.price_identity_status.eq('provisional_not_reviewed').all()
assert shortlist.entity_id.groupby(shortlist.case_id).apply(lambda x:x.is_unique).all()
# Display aggregate observed profiles; individual provisional prices remain in the private CSV.
display(shortlist.groupby('case_id').agg(players=('entity_id','size'),min_age=('age','min'),max_age=('age','max'),min_minutes=('minutes','min'),median_affinity=('affinity','median'),median_goals_p90=('gls_p90','median'),median_assists_p90=('ast_p90','median')))
display(Markdown('These descriptive differences explain the returned profiles; they are not evidence that a club would sign or benefit from any player.'))
'''),
        ('md', '## Completion and validation limits\n\nCompleted: ten observed-data cases, strict requirement funnels, same-pool baselines, sensitivity analysis, executable notebook and interactive downloadable scenarios. Partial: tactical role fit and cross-source identities remain proxies/provisional. Blocked: transfer-success validation requires reviewed identities, historically available information, defensible outcome labels and realistic fee/club requirements. No actual transfer-success score is reported. Offline execution records no human process events. The app records only explicit execution/review actions. Existing real-data model evaluation and MLflow artifacts remain unchanged; this analysis does not claim a new model experiment.'),
    ]
    notebook=nb.v4.new_notebook(cells=[nb.v4.new_markdown_cell(text) if kind=='md' else nb.v4.new_code_cell(text) for kind,text in cells])
    notebook.metadata['kernelspec']={'display_name':'TFM Python 3.12','language':'python','name':'tfm-python'}
    path=ROOT/'notebooks/09_scouting_scenarios.ipynb'
    NotebookClient(notebook, timeout=180, kernel_name='tfm-python', resources={'metadata':{'path':str(ROOT)}}).execute()
    nb.write(notebook,path)
    evidence=dict(path=str(path.relative_to(ROOT)), sha256=sha256(path), code_cells=sum(c.cell_type=='code' for c in notebook.cells),
                  error_outputs=sum(o.output_type=='error' for c in notebook.cells if c.cell_type=='code' for o in c.outputs), status='executed')
    (ROOT/'reports/scouting_scenarios/notebook_execution.json').write_text(json.dumps(evidence,indent=2))
    print(evidence)

if __name__=='__main__': main()
