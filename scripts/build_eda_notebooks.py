"""Generate and execute source-separated teacher-review EDA on retained real data."""
import os
import sys
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from src.config import ROOT

COMMON="""from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
ROOT = Path.cwd()
while not (ROOT/'src/config.py').exists():
    if ROOT == ROOT.parent: raise RuntimeError('Run within the project')
    ROOT = ROOT.parent
import sys
sys.path.insert(0,str(ROOT))
from src.data.provenance import sha256
manifest=json.loads((ROOT/'data/processed/manifest.json').read_text(encoding='utf-8'))
def table(name):
    info=manifest['outputs'][name]
    path=ROOT/info['parquet_path']
    assert sha256(path)==info['parquet_sha256'], 'Prepared table checksum changed'
    return pd.read_parquet(path)
"""

def notebook(name,title,cells):
    md=nbformat.v4.new_markdown_cell;code=nbformat.v4.new_code_cell
    n=nbformat.v4.new_notebook(cells=[md(title),code(COMMON)]+[md(text) if kind=='md' else code(text) for kind,text in cells])
    n.metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},'language_info':{'name':'python','version':'3.12'}}
    km=KernelManager(kernel_name='python3');km.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
    NotebookClient(n,timeout=180,km=km,resources={'metadata':{'path':str(ROOT)}}).execute()
    path=ROOT/f'notebooks/{name}.ipynb';nbformat.write(n,path);print('Executed',path.relative_to(ROOT))


def main(which):
    if which=='fbref':notebook('01_fbref_data_exploration','# FBref — datos reales, calidad y EDA\n\nSix original statistical-category archives from GitHub releases, exported into target-season CSVs without cleaning source fields. Their exact archive/CSV hashes are in data/raw/source_manifest.json. Only FBref feeds the current recommender.',[
        ('code',"f=table('fbref_player_seasons'); g=table('fbref_scouting_gallery'); features=['gls_p90','ast_p90','sh_p90','sot_p90','crs_p90','int_p90','tklw_p90','fls_p90','fld_p90']\nprint('Player/league/season rows:',len(f),'Gallery rows:',len(g))\nprint('Duplicate entity/league/season keys:',int(f.duplicated(['entity_id','league','season']).sum()))\nf.groupby(['league','season']).size().unstack(fill_value=0)"),
        ('md','## Grain and identity\n\nFBref category joins use source player ID + club + league + season, with exposure compatibility checks. Club stints are aggregated within player/league/season; unknown counts remain unknown. Cross-league histories remain separate. The gallery retains the highest-minutes league per player/season. Source snapshots do not prove historical publication timestamps.'),
        ('code',"quality=pd.DataFrame({'dtype':f.dtypes.astype(str),'missing':f.isna().sum(),'missing_pct':f.isna().mean()*100})\nquality.sort_values('missing_pct',ascending=False)"),
        ('code',"f[features].describe().T"),
        ('code',"f[features].hist(bins=35,figsize=(12,9));plt.suptitle('Observed per-90 distributions; no global imputation');plt.tight_layout();plt.show()\nq1=f[features].quantile(.25);q3=f[features].quantile(.75);iqr=q3-q1\npd.DataFrame({'iqr_flag_count':((f[features]<q1-1.5*iqr)|(f[features]>q3+1.5*iqr)).sum()})"),
        ('md','## Missing values and outliers\n\nRecent seasons retain standard statistics but lack aligned complete core categories. Gallery eligibility therefore removes incomplete profiles rather than filling them with invented observations. High per-90 rates may reflect low exposure or genuine rare events: IQR flags are diagnostic, not automatic deletions. Current modelling imputes/scales on training seasons only.'),
        ('code',"plt.figure(figsize=(9,7));sns.heatmap(f[features].corr(),cmap='coolwarm',center=0);plt.title('Pairwise-observed correlations');plt.tight_layout();plt.show()\nf.groupby(['league','season','pos_main'])[features+['minutes']].median()"),
        ('code',"fig,axes=plt.subplots(1,2,figsize=(13,4))\nsns.boxplot(data=f,x='pos_main',y='sh_p90',showfliers=False,ax=axes[0]);axes[0].set_title('Shots/90 by source position')\nsns.boxplot(data=f,x='league',y='gls_p90',showfliers=False,ax=axes[1]);axes[1].tick_params(axis='x',rotation=30);axes[1].set_title('Goals/90 by league')\nplt.tight_layout();plt.show()"),
        ('md','## Interpretation and model boundary\n\nPosition and exposure affect distributions; league comparisons are descriptive, not causal. Correlated attacking rates motivate excluding goals+assists as a redundant feature. Complete six-style galleries end in 2023/24; four sparse 2024/25 gallery rows are not offered as a complete season. Full retrieval baselines, PCA/K-means loadings, stability and limitations are in 04_feature_comparison_and_model_validation.ipynb. These EDA plots do not validate transfer success.')])
    elif which=='understat':notebook('02_understat_data_exploration','# Understat — shots, source coverage and attacking profiles\n\nRaw CSVs are source-preserving exports from the five pinned GitHub shot archives. Understat remains separate from FBref; source IDs are not universal player IDs.',[
        ('code',"shots=table('understat_shots');players=table('understat_player_seasons');quarantine=table('understat_quarantine')\nprint('Observed shots:',len(shots),'Player-season summaries:',len(players),'Quarantined:',len(quarantine))\nprint('Duplicate league/shot keys:',int(shots.duplicated(['league','shot_id']).sum()))\nshots.groupby(['league','season']).agg(shots=('shot_id','size'),players=('source_player_id','nunique'),matches=('match_id','nunique'))"),
        ('code',"pd.DataFrame({'missing':shots.isna().sum(),'missing_pct':shots.isna().mean()*100,'dtype':shots.dtypes.astype(str)}).sort_values('missing_pct',ascending=False)"),
        ('md','## Quality decisions\n\nShot IDs, coordinates, dates and home/away sides are checked. Conflicting sides or invalid coordinates are quarantined, not silently replaced. xG=0 is a real value. Own-goal events remain in source data but are excluded from attacking shot/xG totals. Shot minutes are event times, not total player exposure: player minutes remain missing and per-90 rates are not fabricated.'),
        ('code',"print('Zero-xG events:',int(shots.xG.eq(0).sum()))\nshots[['X','Y','xG','minute']].describe().T"),
        ('code',"fig,axes=plt.subplots(1,2,figsize=(12,4))\nshots.xG.hist(bins=40,ax=axes[0]);axes[0].set(title='Observed xG per event',xlabel='xG')\nshots.result.value_counts().plot.bar(ax=axes[1]);axes[1].set_title('Shot outcomes');plt.tight_layout();plt.show()\nplayers[['shots','goals','xg','xg_per_shot']].corr()"),
        ('code',"coverage=shots.groupby(['league','season']).match_id.nunique().rename('observed_matches').reset_index()\ncoverage['expected_matches']=coverage.apply(lambda r:306 if r.league=='Bundesliga' or (r.league=='Ligue 1' and int(r.season[:4])>=2023) else 380,axis=1)\ncoverage['partial_season']=coverage.season.eq('2025-2026')\ncoverage"),
        ('code',"p=players[(~players.partial_season)&players.shots.ge(20)]\nfig,axes=plt.subplots(1,2,figsize=(12,4))\nsns.boxplot(data=p,x='league',y='xg_per_shot',showfliers=False,ax=axes[0]);axes[0].tick_params(axis='x',rotation=30)\nsns.scatterplot(data=p,x='xg',y='goals',hue='league',alpha=.35,ax=axes[1]);plt.tight_layout();plt.show()"),
        ('md','## Interpretation and limitations\n\nShot quality differs across observed profiles, but xG and goals share shot-volume exposure. The archive covers shooters rather than all rostered players. Expected fixture counts help identify missing coverage; Bundesliga/Serie A 2024/25 have gaps and 2025/26 is partial. No positions or full-match player minutes are supplied by these shot events. Missing positions are not filled through unreviewed FBref joins. These observations support shot exploration, not overall player forecasting or the fitted recommender.')])
    elif which=='transfermarkt':notebook('03_transfermarkt_data_exploration','# Transfermarkt-derived uploads — dated valuations and profile audit\n\nThese CSVs were supplied by the user with claimed origin salimt/football-datasets; their exact repository commit was not verified. Original bytes are copied unchanged into data/raw/transfermarkt. Amounts are reported market assessments; EUR is assumed, not explicit in the source. No valuation model is trained.',[
        ('code',"profiles=table('transfermarkt_profiles');values=table('transfermarkt_values')\nprint('Profiles:',len(profiles),'Dated valuation records:',len(values))\nprint('Duplicate player/date keys:',int(values.duplicated(['source_player_id','valuation_date']).sum()))\nprint('Recorded zero values:',int(values.reported_zero_value.sum()))\nprint('Valuation date range:',values.valuation_date.min(),values.valuation_date.max())"),
        ('code',"pd.DataFrame({'missing':profiles.isna().sum(),'missing_pct':profiles.isna().mean()*100,'dtype':profiles.dtypes.astype(str)}).sort_values('missing_pct',ascending=False)"),
        ('md','## Cleaning and units\n\nSource profile IDs and dated valuation keys are validated. Height zero sentinels are retained in the raw field and become missing clean centimetres. Profile name suffix IDs are removed for display, never used as a universal key. ISO valuation dates are parsed; negative/invalid amounts fail validation. Zero does not automatically mean a free player. Current position/club fields do not establish historical membership or role.'),
        ('code',"values.market_value_eur.describe(percentiles=[.5,.9,.95,.99]).to_frame()\nlatest=values.sort_values('valuation_date').drop_duplicates('source_player_id',keep='last')\npositive=latest[latest.market_value_eur.gt(0)].copy()\nprint('Latest positive values:',len(positive),'Latest zero/unknown:',len(latest)-len(positive))\nimport numpy as np\nfig,axes=plt.subplots(1,2,figsize=(12,4))\nnp.log10(positive.market_value_eur).hist(bins=45,ax=axes[0]);axes[0].set(title='Latest positive reported values',xlabel='log10(amount, EUR assumed)')\nprofiles.main_position.value_counts().head(12).plot.bar(ax=axes[1]);axes[1].set_title('Current source profile positions');plt.tight_layout();plt.show()"),
        ('code',"yearly=values.assign(year=values.valuation_date.dt.year).groupby('year').agg(records=('source_player_id','size'),players=('source_player_id','nunique'),median_amount=('market_value_eur','median'))\nyearly"),
        ('code',"combined=positive.merge(profiles[['source_player_id','height_cm','birth_year','main_position']],on='source_player_id',how='left',validate='one_to_one')\ncombined[['market_value_eur','height_cm','birth_year']].corr()\ncombined.groupby('main_position').market_value_eur.agg(['count','median'])"),
        ('md','## Interpretation and integration boundary\n\nReported values are strongly right-skewed; log plotting changes the display, not the stored amounts. Position/value grouping uses current profiles and cannot be interpreted as historical valuations by role. Global uploaded profiles do not establish historical league coverage. Cross-source links use upstream IDs supported by normalized name/birth year, but remain provisional. In Streamlit values filter candidates after ranking, with dates and uncertainty labels. Original publication timestamps and explicit currency are unknown, so these records do not prove historical affordability and never enter recommendation fitting. Expert or primary-source verification remains pending.')])
    else:raise ValueError('Choose fbref, understat or transfermarkt')


if __name__=='__main__':main(sys.argv[1])
