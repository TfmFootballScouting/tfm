"""Author reproducible notebooks; execution is a separate, failure-preserving step."""
from pathlib import Path
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
SETUP="""from pathlib import Path
import os, sys, json
ROOT = Path.cwd()
while not (ROOT / 'src/config.py').exists():
    if ROOT == ROOT.parent: raise RuntimeError('Run inside the project')
    ROOT = ROOT.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault('MPLCONFIGDIR', '/tmp/tfm-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/tfm-cache')
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display, Markdown
from src.config import ROOT, MODELS_DIR
from src.preprocessing.clean import load_players
players = load_players()
dataset = json.loads((ROOT / 'reports/dataset.json').read_text())
display(Markdown('**Dataset:** ' + dataset['dataset_kind'] + '. Legacy-labelled observations are preliminary; no synthetic rows are included.'))
assert not players.source.str.contains('demo|synthetic', case=False).any()
"""

def write(name,cells):
    nb=nbf.v4.new_notebook()
    nb.cells=[nbf.v4.new_markdown_cell(text) if kind=='md' else nbf.v4.new_code_cell(text) for kind,text in cells]
    nb.metadata['kernelspec']={'display_name':'TFM Python 3.12','language':'python','name':'tfm-python'}
    nb.metadata['language_info']={'name':'python','version':'3.12'}
    nbf.write(nb,ROOT/'notebooks'/name)


write('01_data_quality_eda.ipynb',[
('md', '# Data quality and exploratory analysis\nResearch question: what can the available football observations support? Audit the source mix before analyzing rates. Raw legacy files are preserved, including excluded synthetic rows. This notebook analyses only the explicitly labelled subset, not a validated six-season dataset.'),
('code',SETUP),
('code',"""raw = pd.read_csv(ROOT / 'data/raw/players_raw.csv')
display(raw.groupby(['source','league','season']).size().rename('raw_rows').to_frame())
coverage = pd.read_csv(ROOT / 'reports/source_coverage.csv')
display(coverage.groupby(['source','status']).size().rename('coverage_cells').to_frame())
display(players.groupby(['league','season','pos_main']).agg(observations=('player_id','size'),minutes=('minutes','sum')))
print('Rows after conservative minutes/transfer handling:', len(players))
print('Conflicting/duplicate processed observation IDs:', players.player_id.duplicated().sum())
"""),
('md','## Missingness and preprocessing\nUnavailable source statistics remain missing, not zero. Training-time median imputation only applies to selected partially observed features. All-missing columns are excluded. Legacy shots and defensive statistics are discarded because the original merge used row order. Per-90 rates use exact minutes/90, rather than rounded published 90s. No market values are estimated from age or production.'),
('code',"""numeric = ['age','minutes','gls_p90','ast_p90','ga_p90','sh_p90','sot_p90','int_p90','tklw_p90','crs_p90']
missing = players[numeric].isna().mean().sort_values(ascending=False)
display(missing.rename('missing_fraction').to_frame())
missing.plot.bar(title='Missingness: unavailable is not zero'); plt.ylabel('Missing fraction'); plt.tight_layout(); plt.show()
display(players[numeric].describe().T)
"""),
('code',"""fig,axes=plt.subplots(1,3,figsize=(12,3))
for ax,col in zip(axes,['minutes','gls_p90','ast_p90']):
    sns.histplot(players[col].dropna(),ax=ax,bins=25); ax.set_title(col)
plt.tight_layout();plt.show()
fig,axes=plt.subplots(1,2,figsize=(10,3))
for ax,col in zip(axes,['gls_p90','ast_p90']):
    sns.boxplot(data=players,x='pos_main',y=col,ax=ax)
plt.tight_layout();plt.show()
display(players[players.quality_outlier][['player','minutes','gls_p90','sh_p90']])
print('Flagged extreme observations:', int(players.quality_outlier.sum()))
"""),
('md','Extreme observations are flagged for source review rather than silently clipped. The 450-minute eligibility floor limits the most unstable rate estimates, but does not establish reliability or remove selection bias. Position comparisons are descriptive; leagues and seasons cannot be compared if only one is available.'),
('code',"""corr=players[['gls_p90','ast_p90','ga_p90','minutes','age']].corr()
sns.heatmap(corr,annot=True,vmin=-1,vmax=1,cmap='vlag');plt.title('Descriptive correlations');plt.tight_layout();plt.show()
display(players.groupby('pos_main')[['gls_p90','ast_p90']].agg(['median','count']))
display(players.groupby(['league','season'])[['gls_p90','ast_p90']].median())
display(Markdown(f'Available leagues: **{players.league.nunique()}**; seasons: **{players.season.nunique()}**. Cross-league and temporal conclusions are blocked. G+A is algebraically redundant with goals and assists, so it is excluded from model fitting.'))
"""),
('md','## Separate current Transfermarkt sample\nThe source league-page sample is a top-value first-page selection, not a representative roster. Current valuations cannot backfill 2020–2026 decision dates. The requested season parameter is retained solely as provenance, not as a verified effective season.'),
('code',"""tm_path=ROOT/'data/external/transfermarkt/current_market_sample.csv'
if tm_path.exists():
    tm=pd.read_csv(tm_path)
    display(tm.groupby('league').agg(rows=('source_player_id','size'),missing_value=('market_value_eur',lambda x:x.isna().sum())))
    display(tm[['player','league','market_value_eur','valuation_date','temporal_scope']].head())
    tm['market_value_eur'].dropna().div(1e6).plot.hist(bins=15,title='Current first-page market sample (M EUR)');plt.show()
else:
    display(Markdown('No parsed Transfermarkt sample available.'))
"""),
('md','## Interpretation\nThe data supports preliminary descriptions of attacking output and availability only. Missing defensive/passing metrics prevent broad tactical-style interpretation. The legacy provenance and single-season restriction prevent a final TFM claim about recommendation quality. New source snapshots or licensed exports with stable IDs and dated valuations are required.')])

write('02_model_analysis.ipynb',[
('md','# Recommendation, PCA and K-means analysis\nDistinguish descriptive structure from recommendation relevance. This notebook inspects an actually executed, explicitly exploratory MLflow run; it never reports unexecuted temporal or transfer validation as passed.'),
('code',SETUP+"\nfrom src.models.recommend import PlayerRecommender\nrec=PlayerRecommender.load()\nmeta=json.loads((MODELS_DIR/'metrics.json').read_text())\ndisplay(meta)\n"),
('code',"""from src.data.provenance import sha256
assert sha256(ROOT/'data/processed/real/players.parquet') == meta['dataset']['dataset_sha256']
print('Git commit:', meta['git_commit'], 'Dirty:',meta['git_dirty'])
print('Run ID:', meta['run_id'])
print('Fitted features:',rec.artifacts.feature_cols)
display(pd.read_csv(ROOT/'reports/experiments/baselines.csv'))
"""),
('md','## Baselines and ranking interpretation\nCompare cosine style-direction rankings with linear weighted standardized scores, goals+assists per 90, and minutes played. Top-k Jaccard overlap describes ranking agreement, not relevance or transfer success. A separate temporal profile-retrieval benchmark is implemented, including a seeded random baseline, but requires consecutive observed seasons. It tests profile persistence rather than the quality of a signing. Tactical styles below 60% measured absolute weight are disabled rather than inferred from unavailable data.'),
('code',"""temporal=pd.read_csv(ROOT/'reports/experiments/temporal_proxy.csv')
display(temporal)
display(Markdown('**Temporal benchmark:** '+meta['temporal_status']))
robustness=pd.read_csv(ROOT/'reports/experiments/robustness.csv')
display(robustness.groupby(['style','perturbation']).top10_jaccard.agg(['mean','min','max']))
sns.boxplot(data=robustness,x='style',y='top10_jaccard',hue='perturbation');plt.xticks(rotation=30);plt.title('Weight and training-bootstrap sensitivity');plt.tight_layout();plt.show()
"""),
('md','Multiplying a single-feature direction by a positive weight does not change cosine rankings. Stability of the goals-only or assists-only profiles under these perturbations is therefore expected by construction; it is not evidence of robust scouting quality. Thirty bootstrap resamples of the observed training rows also refit medians/scaling and rank the unchanged original candidate set. This gives a more useful preprocessing-sensitivity diagnostic. Full-feature multi-source validation remains required.'),
('code',"""loadings=pd.DataFrame(rec.artifacts.pca.components_,columns=rec.artifacts.feature_cols,index=[f'PC{i+1}' for i in range(rec.artifacts.pca.n_components_)])
display(loadings)
display(pd.Series(rec.artifacts.pca.explained_variance_ratio_,index=loadings.index,name='explained_variance'))
loadings.T.plot.bar(title='PCA loadings: directions, not tactical labels');plt.tight_layout();plt.show()
profiles=rec.players.groupby('cluster')[rec.artifacts.feature_cols].mean()
display(profiles)
display(pd.crosstab(rec.players.cluster,rec.players.pos_main))
display(pd.read_csv(ROOT/'reports/experiments/cluster_stability.csv'))
"""),
('md','With two retained features and two PCs, explained variance totals 100% by construction. PCA has rotated the feature plane, not demonstrated successful dimensionality reduction. K-means partitions attack-production levels, including a near-zero-output group; these groups must not be labelled playing styles. Silhouette and seed ARI describe cluster geometry and initialization stability, not transfer relevance.'),
('code',"""for style in ['finisher','creator']:
    display(Markdown('### '+style))
    top=rec.recommend(style,top_n=5)
    display(top[['player','team','pos','minutes','gls_p90','ast_p90','affinity']])
    print('Median top-5 minutes:', top.minutes.median())
"""),
('md','Cosine measures direction after centering: a balanced low-output player and a prolific player can share a direction. Inspect raw rates and minutes next to the ranking and compare the linear baseline. Expert review, position-specific feature availability, uncertainty intervals and historical transfer labels are still needed before operational signing recommendations.')])

write('03_scouting_validation.ipynb',[
('md','# Scouting scenarios and validation gates\nA club request should define position, season, style, excluded current club, minimum exposure and budget. This notebook distinguishes executable descriptive shortlists from scenarios that cannot be evaluated without historical evidence.'),
('code',SETUP+"\nfrom src.models.recommend import PlayerRecommender\nrec=PlayerRecommender.load()\n"),
('code',"""latest=sorted(rec.players.season.unique())[-1]
requests=[dict(name='Forward scoring shortlist',position='FW',style='finisher',budget_m_eur=10),
          dict(name='Midfield assisting shortlist',position='MF',style='creator',budget_m_eur=5)]
for request in requests:
    display(Markdown('### '+request['name']))
    display(rec.recommend(request['style'],position=request['position'],season=latest,exclude_club='Barcelona',top_n=5)[['player','team','minutes','gls_p90','ast_p90','affinity']])
    decision_date=latest[5:]+'-07-01'
    try:
        budgeted=rec.recommend(request['style'],position=request['position'],season=latest,
                    max_budget=request['budget_m_eur'],cutoff=decision_date)
        display(budgeted)
    except ValueError as exc:
        display(Markdown('**Budget scenario blocked:** '+str(exc)))
"""),
('md','These are documented analysis requests executed against legacy football observations, not actual club mandates. Unknown valuations are never treated as free transfers; market value is not the same as an agreed fee or total recruitment cost. A 2026 current valuation cannot be attached to a 2024 shortlist.'),
('code',"""from src.data.matching import propose_matches
profile_path=ROOT/'data/external/transfermarkt/current_profiles_sample.csv'
if profile_path.exists() and profile_path.stat().st_size>1:
    tm=pd.read_csv(profile_path,dtype={'source_player_id':str})
    entities=players.drop_duplicates('source_player_id')[['source_player_id','player']]
    proposals=propose_matches(entities,tm)
    display(proposals.status.value_counts().rename('identities').to_frame())
    display(proposals[proposals.status!='unmatched'].head(20))
    proposals.to_csv(ROOT/'reports/identity_proposals.csv',index=False)
else:
    display(Markdown('Profile identity matching unavailable: no parsed profile sample.'))
"""),
('md','No cross-source identity is auto-approved from a name alone. Unique name plus date of birth or an explicit reviewed mapping is required. Current sampled profiles do not provide historical club membership. Retrospective transfer evaluation needs a dated candidate universe, prior-only feature fitting, historical valuation knowledge dates, transfer dates and actual fees. None is reconstructed from future observations.'),
('code',"""requirements=pd.DataFrame([
 {'requirement':'Multiple consecutive statistical seasons','status':'blocked' if players.season.nunique()<2 else 'available'},
 {'requirement':'Historical dated candidate roster','status':'blocked'},
 {'requirement':'As-of EUR valuations / actual transfer fees','status':'blocked'},
 {'requirement':'Verified identity-to-transfer labels','status':'blocked'},
 {'requirement':'Recommendation engine and cutoff guard','status':'executed in automated tests'},
])
display(requirements)
"""),
('md','## Required historical experiment\nFor each summer decision date, fit imputation, scaling, PCA and clustering only on completed prior seasons. Freeze the eligibility universe as known then. Compare position/budget-eligible ranked shortlists with observed next-window transfers, with recall@k, precision@k and NDCG only when relevance labels and sampling rules are documented. Report selection and survivorship bias. This design is documented, but transfer metrics remain unrun because the required labels are missing.')])

write('04_process_mining.ipynb',[
('md','# Scouting process and genuine event-log analysis\nCase = one explicitly executed scouting search. Activities: need_defined → search_executed → ranking_generated → shortlist_reviewed → decision_recorded. Only observed app actions are logged. A generated ranking does not imply analyst review or a signing. Unit-test logs are temporary and are not included here.'),
('code',SETUP+"\nfrom src.process.events import discover\n"),
('code',"""schema=pd.DataFrame([
('case_id','string','Search UUID, not player ID'),
('activity','enum','Observed process step'),
('timestamp','UTC ISO-8601','Actual server event timestamp'),
('actor','string','app_user or system, not an invented named scout'),
('event_kind','enum','observed_application; simulation rejected'),
('attributes','JSON','style, position, season, club filters and candidate count')],columns=['field','type','meaning'])
display(schema)
path=ROOT/'data/events/scouting.jsonl'
try:
    dfg,cases=discover(path)
except ValueError as exc:
    display(Markdown('**Discovery blocked:** '+str(exc)))
else:
    display(dfg);display(cases)
    dfg.to_csv(ROOT/'reports/process_dfg.csv',index=False)
    cases.to_csv(ROOT/'reports/process_cases.csv',index=False)
"""),
('md','Directly-follows discovery is available for genuine event logs, with edge counts, median transition time and incomplete-case indicators. There are no genuine human scouting sessions in this submission, so discovery and bottleneck findings are not claimed. Real app usage may create partial observed cases; those are not evidence of actual club recruitment. Formal conformance, completed decisions and organizational KPIs require consented real workflow records. No simulated log is generated to fill the gap.')])
