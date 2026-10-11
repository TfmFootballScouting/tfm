"""Execute the full five-league cleaning, EDA, model and validation analysis."""
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
      ('md','# Complete five-league real-data pipeline\n\nNew models are actually fitted on real FBref observations from La Liga, Premier League, Bundesliga, Serie A and Ligue1. Every prior source, table and model artifact is preserved. Market values/profile enrichment remain private, provisional review data and do not enter fitting. This notebook analyses executed experiments; no synthetic player data or transfer-success results are introduced.'),
      ('code','''from pathlib import Path
import os,sys,json
ROOT=Path.cwd()
while not (ROOT/'src/config.py').exists():
    if ROOT==ROOT.parent:raise RuntimeError('Run inside the repository')
    ROOT=ROOT.parent
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
import pandas as pd
from IPython.display import display,Markdown,Image
from src.data.provenance import sha256
folder=ROOT/'reports/five_league_pipeline'
report=json.loads((folder/'pipeline.json').read_text())
for path,digest in report['preserved_sha256'].items():assert sha256(ROOT/path)==digest,path
for item in report['outputs'].values():assert sha256(ROOT/item['path'])==item['sha256']
display(pd.DataFrame(report['counts'].items(),columns=['table','rows']))
display(Markdown('Dataset version `'+report['dataset_version']+'`; training code commit `'+report['git_commit']+'`.'))
'''),
      ('md','## Identity, cleaning and season-aware preprocessing\n\nSource FBref player ID identifies a person; observation keys also include league, season and club. Club stints sum only inside a league-season; any missing stint total leaves the seasonal total unknown. For a gallery, cross-league transfers select the highest-minute league before feature eligibility, never merge league rates. Exact duplicates are removed; conflicting identity keys stop. Numeric/age/unit checks preserve missing values, and auxiliary source totals require period-compatible exposure. Unknown values are never substituted with zero. 2025/26 is partial and never fitted. Core advanced2024/25 is too sparse for a usable gallery. The full field dictionary and source coverage describe retained fields, not absent statistics.'),
      ('code','''display(pd.read_csv(folder/'alignment.csv').groupby(['league','category']).agg(stints=('stints','sum'),matched=('matched','sum'),compatible=('compatible','sum')))
missing=pd.read_csv(folder/'missingness.csv')
display(missing[missing.table.eq('player_seasons')].sort_values('missing_fraction',ascending=False).head(25))
display(pd.read_csv(folder/'season_position_quality.csv'))
'''),
      ('md','## EDA: distributions, outliers, correlation and cohort differences\n\nPlots use observed complete-season profiles with at least450minutes for per90 comparisons. IQR reference limits use 2020/21–2021/22 development years and flag tails without deleting rows or clipping values. Boxplots suppress visual fliers only; observations stay in data and models. Spearman correlations use available pairs, not global imputation. G+A is redundant and excluded from the nine-feature Core fit. Comparisons across roles/leagues/seasons describe coverage-selected cohorts, not causal league quality.'),
      ('code','''display(pd.read_csv(folder/'distributions.csv'))
display(pd.read_csv(folder/'outliers.csv').groupby(['league','feature']).agg(observed=('observed','sum'),flagged=('outside','sum')))
display(Image(filename=str(folder/'eda_quality.png')))
display(Image(filename=str(folder/'eda_cohorts.png')))
'''),
      ('md','## Chronological experiments and meaningful baselines\n\nCore trains2020/21–2021/22, validates2022/23 and holds out2023/24. Offensive trains through2022/23, validates2023/24 and holds out2024/25. Attack-on-Core uses the Core cohort with offensive features. K is chosen using training silhouette; distance method is chosen on validation MRR. Imputer/scaler/PCA/clusters see training seasons only. The holdout is never tuned. Retrieval tests the same player’s next-season profile against the full future gallery, with goals/assists, goals-only and random baselines; ties use uniform expected ranks. Pooled galleries are much larger than the old La Liga-only pools.'),
      ('code','''summary=[]
for name,info in report['experiments'].items():
    summary.append(dict(model=name,**{key:info[key] for key in ['selected_method','selected_k','train_seasons','validation_season','holdout_season','holdout_mrr','holdout_recall_at_5','rows_by_split']}))
    metrics=pd.read_csv(folder/f'{name}_retrieval.csv')
    display(metrics[metrics.phase.eq('holdout')][['method','queries','candidate_count','mrr','mrr_ci_low','mrr_ci_high','recall_at_5','mrr_delta_goals_assists','mrr_delta_ci_low','mrr_delta_ci_high']])
display(pd.DataFrame(summary))
comparison=pd.read_csv(folder/'matched_pool_comparison.csv')
display(comparison)
display(Markdown('Matched-pool differences compare identical returning identities and candidates. Their paired bootstrap intervals, rather than the old single-league metric magnitude, determine whether an observed change is distinguishable from zero in this cohort. No improvement is assumed.'))
'''),
      ('md','## PCA and K-means interpretation, robustness and drift\n\nPCA loadings explain measured profile directions; components are not discovered tactical styles. K-means groups statistical profiles. Position, league and season NMI detect associations; they do not validate role labels. Thirty person-block bootstraps retain all seasons of a sampled player and refit preprocessing/PCA/clusters, reporting out-of-bag ARI, component alignment/subspace angles and ranking stability. These are resampled real records, not invented players. Low individual-component alignment can coexist with stable subspaces; review component-level instability before assigning meanings.'),
      ('code','''for name,info in report['experiments'].items():
    display(Markdown('### '+name))
    display(pd.DataFrame([info['cluster_diagnostics']]))
    display(pd.read_csv(folder/f'{name}_pca_loadings.csv'))
    clusters=pd.read_csv(folder/f'{name}_cluster_bootstrap.csv')
    loadings=pd.read_csv(folder/f'{name}_pca_loading_bootstrap.csv')
    display(clusters[['adjusted_rand_reference','adjusted_rand_out_of_bag']].describe())
    display(loadings.groupby('component').absolute_loading_cosine.agg(['mean','min','max']))
    display(pd.read_csv(folder/f'{name}_ranking_bootstrap.csv').groupby(['kind','method']).top5_jaccard.agg(['mean','min','max']))
    display(Image(filename=str(folder/f'{name}_evaluation.png')))
'''),
      ('md','## Position/league diagnostics and qualitative recommendations\n\nThe per-league holdout slices use the same trained models and previously selected distance methods. Position slices retain actual returning players, candidate universe and bootstrap uncertainty. Qualitative alternatives apply known age, broad position and club restrictions; they are examples for human/video review, not validated club suitability, official budgets or outcomes.'),
      ('code','''for name,info in report['experiments'].items():
    league=pd.read_csv(folder/f'{name}_league_retrieval.csv')
    display(league[league.method.eq(info['selected_method'])][['league','queries','candidate_count','mrr','recall_at_5']])
    display(pd.read_csv(folder/f'{name}_position_retrieval.csv'))
    display(pd.read_csv(folder/f'{name}_qualitative.csv').head(8))
'''),
      ('md','## Cross-source review and realistic budget scenarios\n\nExisting source-ID mapping plus normalized-name/birth-year agreement proposes additional identities across all five leagues. Every proposal remains unreviewed; current profile evidence does not establish historical known-at information. Profile enrichment and dated reported values remain separate private review outputs and are rejected by model-use guards. A reported market assessment is not a fee; latest zero is unknown, not free. Fifty one-vacancy cases across five league pools use observed model profiles with age/position/style/minutes/own-club/value constraints and requirement sensitivity. Empty pools are never relaxed and are not failures. Offline batches create no human process events.'),
      ('code','''review=json.loads((folder/'review.json').read_text())
assert review['approved_identity_pairs']==0 and not review['model_use_eligible']
display(pd.DataFrame([{key:review[key] for key in ['proposed_pairs','supported_provisional_pairs','approved_identity_pairs','review_rows']}]))
display(pd.read_csv(folder/'price_coverage.csv'))
cases=pd.DataFrame([dict(case_id=c['case_id'],eligible=c['eligible'],returned=c['returned']) for c in review['cases']])
display(cases)
display(pd.read_csv(folder/'scenario_sensitivity.csv').groupby('variation').agg(cases=('case_id','size'),mean_overlap=('shortlist_jaccard','mean'),min_overlap=('shortlist_jaccard','min')))
display(Markdown(f"{len(cases)} cases; {int(cases.returned.eq(0).sum())} empty; unknown/unmatched valuations exclude candidates rather than being estimated."))
'''),
      ('md','## MLflow, app and remaining validation limits\n\nThree actual model-refit runs are separate from the earlier frozen-model diagnostic. Each records dataset/code version, owner/project/environment, evaluation plots, PCA/clustering/robustness tables and model artifacts, with checksum-verified portable exports. Serving keeps European-trained and original La Liga-trained choices. Historical actual-transfer success, genuine club-process outcomes, individually approved identities, provider publication dates and advanced Segunda coverage remain incomplete. No valuation prediction or transfer-success metric is invented.'),
      ('code','''for name,info in report['experiments'].items():
    run=json.loads((folder/'mlflow_export'/name/'run.json').read_text())
    assert run['status']=='FINISHED' and run['run_id']==info['mlflow_run_id']
    assert run['tags']['dataset']==report['dataset_version']
    display(pd.DataFrame([dict(model=name,run_id=run['run_id'],status=run['status'],exported_artifacts=info['exported_artifacts'])]))
display(Markdown('; '.join(report['limits'])))
'''),
    ]
    doc=nb.v4.new_notebook(cells=[nb.v4.new_markdown_cell(text) if kind=='md' else nb.v4.new_code_cell(text) for kind,text in cells])
    doc.metadata['kernelspec']={'display_name':'TFM Python3.12','language':'python','name':'tfm-python'}
    NotebookClient(doc,timeout=240,kernel_name='tfm-python',resources={'metadata':{'path':str(ROOT)}}).execute()
    path=ROOT/'notebooks/11_five_league_full_pipeline.ipynb';nb.write(doc,path)
    evidence=dict(path=str(path.relative_to(ROOT)),sha256=sha256(path),code_cells=sum(c.cell_type=='code' for c in doc.cells),
        errors=sum(o.output_type=='error' for c in doc.cells if c.cell_type=='code' for o in c.outputs),status='executed')
    (ROOT/'reports/five_league_pipeline/notebook_execution.json').write_text(json.dumps(evidence,indent=2));print(evidence)

if __name__=='__main__':main()
