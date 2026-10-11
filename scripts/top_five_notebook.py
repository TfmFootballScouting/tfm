"""Execute coverage and external-league analysis without retraining."""
import json
import os
import nbformat as nb
from nbclient import NotebookClient
from src.config import ROOT
from src.data.provenance import sha256


def main():
    os.environ.setdefault('JUPYTER_PATH',str(ROOT/'.jupyter/share/jupyter'))
    os.environ.setdefault('IPYTHONDIR','/tmp/tfm-ipython')
    os.environ.setdefault('JUPYTER_RUNTIME_DIR','/tmp/tfm-jupyter')
    cells=[
      ('md','# Five-league coverage and frozen-model evaluation\n\nReal retained, checksum-pinned FBref/worldfootballR archives expand La Liga to Premier League, Bundesliga, Serie A and Ligue 1. Existing model artifacts and training transforms are unchanged. No synthetic observations, estimates, new Transfermarkt collection or transfer-success labels are introduced.'),
      ('code', '''from pathlib import Path
import os,sys,json
ROOT=Path.cwd()
while not (ROOT/'src/config.py').exists():
    if ROOT==ROOT.parent: raise RuntimeError('Run inside the repository')
    ROOT=ROOT.parent
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
import pandas as pd
from IPython.display import display,Markdown
from src.data.provenance import sha256
report=json.loads((ROOT/'reports/top_five_leagues/manifest.json').read_text())
for item in report['outputs'].values(): assert sha256(ROOT/item['path'])==item['sha256']
for filename,digest in report['report_sha256'].items(): assert sha256(ROOT/'reports/top_five_leagues'/filename)==digest
coverage=pd.read_csv(ROOT/'reports/top_five_leagues/coverage.csv')
availability=pd.read_csv(ROOT/'reports/top_five_leagues/availability.csv')
display(availability.pivot(index=['model','season'],columns='league',values='players'))
'''),
      ('md','## Category and exposure reliability\n\nSource player ID + league + season + club defines a stint. Auxiliary category totals are used only when their reported 90s agree with standard minutes/90 within 0.061, accommodating the source rounding. Incompatible values become unknown, never zero. A multi-club season sums only within one league and missing stints propagate. Cross-league transfers retain separate historical rows; the gallery takes the highest-minutes league before feature eligibility, with alphabetical league ties. It does not blend league totals or treat the player as two distinct candidates. This rule can exclude otherwise eligible secondary-league observations and slightly changes the La Liga cohort.'),
      ('code', '''display(coverage.groupby(['league','category']).agg(raw_stints=('raw_stints','sum'),matched=('matched','sum'),compatible=('compatible','sum')))
quality=availability[~availability.offered]
display(quality)
display(Markdown(f"Cross-league player-season rows requiring gallery selection: **{report['cross_league_person_seasons']}**. Core galleries cover 2020/21–2023/24; offensive galleries extend through 2024/25. Tiny Core 2024/25 cohorts are not offered. The 2025/26 archive is partial and excluded from recommendations. Category presence alone does not establish aligned feature completeness."))
'''),
      ('md','## External league profile retrieval\n\nThe original model and neighbor method were selected on La Liga. Apply their frozen transforms and the selected method to each league without refitting on future seasons. Core queries 2022/23 against 2023/24; offensive queries 2023/24 against 2024/25. Candidate pools are league-specific and the target is the same player in the next season. All available profile methods and goals/assists/random baselines are evaluated on identical returning players. Confidence intervals are player bootstrap intervals conditional on this source cohort. Differences between Core and offensive are not controlled because features, years and cohorts differ.'),
      ('code', '''evaluation=pd.read_csv(ROOT/'reports/top_five_leagues/evaluation.csv')
selected=evaluation[evaluation.selected_method]
display(selected[['model','league','queries','candidate_count','mrr','mrr_ci_low','mrr_ci_high','recall_at_5','mrr_delta_goals_assists','mrr_delta_ci_low','mrr_delta_ci_high']])
display(evaluation[evaluation.method.isin(['goals_assists','random'])][['model','league','method','mrr','recall_at_5']])
assert selected.query_season.lt(selected.evaluation_season).all()
display(Markdown('Observed retrieval scores describe profile persistence. The league-specific pools do not validate a pooled cross-league tactical ranking, adjust league strength, establish a signing benefit or calibrate affinity as probability. No new training-performance gain is claimed.'))
'''),
      ('md','## App scope and valuation coverage\n\nThe five-league market is the default; the original La Liga-only gallery remains selectable. League selection restricts rankings, similar players, clusters and comparison choices; scenarios have an explicit league requirement. All six measured Core styles remain available. Offensive supports vertical and counterattack. Retained supported valuation links remain provisional: an unmatched player has unknown value, not an estimate or free-transfer status. Private uploads are not necessary to launch ordinary five-league scouting from Git.'),
      ('code', '''from src.app.leagues import load_top_five_service
for name in ['core','offensive']:
    service=load_top_five_service(name)
    gallery=service.for_season(service.available_seasons[0]).players
    assert gallery.entity_id.is_unique
    display(gallery.groupby('league').agg(players=('entity_id','size'),median_age=('age','median'),median_minutes=('minutes','median')))
    display(Markdown(f"{name}: styles **{', '.join(service.supported_styles)}**. Dataset `{report['dataset_version']}`."))
'''),
    ]
    doc=nb.v4.new_notebook(cells=[nb.v4.new_markdown_cell(text) if kind=='md' else nb.v4.new_code_cell(text) for kind,text in cells])
    doc.metadata['kernelspec']={'display_name':'TFM Python 3.12','language':'python','name':'tfm-python'}
    NotebookClient(doc,timeout=180,kernel_name='tfm-python',resources={'metadata':{'path':str(ROOT)}}).execute()
    path=ROOT/'notebooks/10_top_five_leagues.ipynb'
    nb.write(doc,path)
    evidence=dict(path=str(path.relative_to(ROOT)),sha256=sha256(path),code_cells=sum(c.cell_type=='code' for c in doc.cells),
                  errors=sum(o.output_type=='error' for c in doc.cells if c.cell_type=='code' for o in c.outputs),status='executed')
    (ROOT/'reports/top_five_leagues/notebook_execution.json').write_text(json.dumps(evidence,indent=2))
    print(evidence)

if __name__=='__main__': main()
