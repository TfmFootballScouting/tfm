"""Complete real-data five-league rerun, preserving every earlier experiment."""
import hashlib
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mlflow
from mlflow.tracking import MlflowClient
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import normalized_mutual_info_score
from src.config import ROOT
from src.data.provenance import sha256
from src.data.source_rights import require_model_data_use
from src.preprocessing.collected import normalize_fbref, aggregate_player_seasons, data_dictionary, quality_tables
from src.models.collected import EXPERIMENTS, fit_experiment, cluster_analysis, evaluate_pair, qualitative_shortlists
from src.models.validation import resampling_validation, temporal_validation, position_retrieval
from scripts.top_five_leagues import select_rows, align_category, dominant_league_gallery, MAPPINGS, KEYS, LEAGUES
from scripts.worldfootballr_archive import ensure_snapshot, read_rds

REPORT=ROOT/'reports/five_league_pipeline'


def preserved_artifacts():
    previous=json.loads((ROOT/'reports/enrichment/pipeline.json').read_text())
    hashes={**previous['preserved_input_sha256'],**previous['outputs_sha256'],**previous['code_sha256']}
    top=json.loads((ROOT/'reports/top_five_leagues/manifest.json').read_text())
    for item in top['outputs'].values(): hashes[item['path']]=item['sha256']
    for filename,digest in top['report_sha256'].items(): hashes[f'reports/top_five_leagues/{filename}']=digest
    for directory in ['reports/top_five_leagues/mlflow_export']:
        for path in (ROOT/directory).rglob('*'):
            if path.is_file(): hashes[str(path.relative_to(ROOT))]=sha256(path)
    for name in ['reports/top_five_leagues/manifest.json','notebooks/10_top_five_leagues.ipynb']:
        hashes[name]=sha256(ROOT/name)
    for path,digest in hashes.items():
        if sha256(ROOT/path)!=digest: raise ValueError(f'Previous artifact changed: {path}')
    return hashes


def prepare_data():
    records=[r for r in json.loads((ROOT/'reports/worldfootballr_sources.json').read_text()) if r['original_source']=='fbref']
    tables={r['category']:select_rows(read_rds(ensure_snapshot(r,False))[0]) for r in records}
    standard=tables['standard']
    fields=['Player','Nation','Pos','Age','Born','Min_Playing','MP_Playing','Gls','Ast','xG_Expected','xAG_Expected']
    base=standard[KEYS+fields].rename(columns={'Player':'player','Nation':'nation','Pos':'pos','Age':'age','Born':'birth_year',
        'Min_Playing':'minutes','MP_Playing':'mp','Gls':'gls','Ast':'ast','xG_Expected':'xg','xAG_Expected':'xag'})
    alignment=[]
    for category,mapping in MAPPINGS.items():
        check,packet=align_category(standard,tables[category],mapping)
        base=base.merge(packet,on=KEYS,how='left',validate='one_to_one')
        for (league,season),group in check.groupby(['league','season']):
            alignment.append(dict(category=category,league=league,season=season,stints=len(group),
                matched=int(group.category_key_matched.sum()),compatible=int(group.category_exposure_compatible.sum())))
    base['source']='fbref_worldfootballr'
    base['provenance_status']='published_secondary_archive'
    base['period_status']=np.where(base.season.eq('2025-2026'),'partial_September_2025','historical_season_label_completeness_not_guaranteed')
    clubs,issues,duplicates=normalize_fbref(base)
    seasons=aggregate_player_seasons(clubs)
    gallery=dominant_league_gallery(seasons)
    frames=dict(player_club_seasons=clubs,player_seasons=seasons,
        core_gallery=gallery[gallery.tactical_proxy_candidate&~gallery.partial_season].copy(),
        offensive_gallery=gallery[gallery.baseline_candidate&~gallery.partial_season].copy())
    outputs={}
    for name,frame in frames.items():
        path=ROOT/f'data/processed/real/five_league_pipeline_{name}.parquet'
        frame.to_parquet(path,index=False)
        outputs[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha256(path),rows=len(frame))
    pd.DataFrame(alignment).to_csv(REPORT/'alignment.csv',index=False)
    pd.DataFrame(issues).to_csv(REPORT/'cleaning.csv',index=False)
    data_dictionary(frames).to_csv(REPORT/'dictionary.csv',index=False)
    inventory,missingness=quality_tables(frames)
    inventory.to_csv(REPORT/'inventory.csv',index=False)
    missingness.to_csv(REPORT/'missingness.csv',index=False)
    seasons.groupby(['league','season','pos_main'],dropna=False).agg(players=('entity_id','size'),
        minutes_missing=('minutes',lambda x:x.isna().sum()),eligible_baseline=('baseline_candidate','sum'),
        eligible_core=('tactical_proxy_candidate','sum'),multiclub=('club_count',lambda x:x.gt(1).sum()),
        outliers=('quality_outlier','sum')).reset_index().to_csv(REPORT/'season_position_quality.csv',index=False)
    features=['minutes','gls_p90','ast_p90','sh_p90','sot_p90','crs_p90','int_p90','tklw_p90','fls_p90','fld_p90']
    observed=seasons[seasons.minutes_eligible&~seasons.partial_season]
    observed[features].describe(percentiles=[.01,.25,.5,.75,.99]).T.to_csv(REPORT/'distributions.csv')
    observed[features].corr(method='spearman').to_csv(REPORT/'correlations.csv')
    tails=[]
    for league,group in observed.groupby('league'):
        train=group[group.season.le('2021-2022')]
        for feature in features:
            q1,q3=train[feature].quantile([.25,.75]);low,high=q1-1.5*(q3-q1),q3+1.5*(q3-q1)
            for season,rows in group.groupby('season'):
                tails.append(dict(league=league,season=season,feature=feature,development_low=low,development_high=high,
                    observed=int(rows[feature].notna().sum()),outside=int((rows[feature].lt(low)|rows[feature].gt(high)).sum()),policy='flag_only_no_deletion'))
    pd.DataFrame(tails).to_csv(REPORT/'outliers.csv',index=False)
    fig,axes=plt.subplots(1,3,figsize=(16,5))
    sns.heatmap(seasons[features].isna().mean().to_frame('missing fraction'),vmin=0,vmax=1,annot=True,ax=axes[0])
    sns.histplot(observed,x='gls_p90',hue='league',element='step',ax=axes[1])
    sns.heatmap(observed[features].corr(method='spearman'),vmin=-1,vmax=1,cmap='vlag',ax=axes[2])
    fig.tight_layout();fig.savefig(REPORT/'eda_quality.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(14,5))
    sns.boxplot(observed,x='pos_main',y='sh_p90',hue='league',showfliers=False,ax=axes[0])
    sns.boxplot(observed,x='season',y='ast_p90',hue='league',showfliers=False,ax=axes[1])
    fig.tight_layout();fig.savefig(REPORT/'eda_cohorts.png',dpi=140);plt.close(fig)
    return frames,outputs,records,duplicates


def models(frames,dataset_version,commit):
    mlflow.set_tracking_uri(f'sqlite:///{ROOT/"mlflow.db"}')
    mlflow.set_experiment('tfm-scouting-five-league-trained-real')
    client=MlflowClient();results={}
    for name,spec in EXPERIMENTS.items():
        players=frames['offensive_gallery' if name=='offensive' else 'core_gallery']
        require_model_data_use(players)
        print('Training five-league model:',name,flush=True)
        rec,parts,search,scores,details,selected=fit_experiment(players,spec)
        stability,centroids,profiles,sizes,diagnostics=cluster_analysis(rec)
        diagnostics['league_nmi']=float(normalized_mutual_info_score(rec.players.cluster,rec.players.league))
        print('Executing person-block PCA/cluster/ranking validation:',name,flush=True)
        extra=resampling_validation(rec,trials=30,seed=42)
        extra.update(temporal_validation(rec,parts))
        extra['position_retrieval']=position_retrieval(details)
        slices=[]
        for league in LEAGUES:
            metrics,_=evaluate_pair(rec,parts['validation'][parts['validation'].league.eq(league)],
                parts['holdout'][parts['holdout'].league.eq(league)],'holdout_league')
            slices.append(metrics.assign(league=league))
        outputs=dict(retrieval=scores,queries=details,cluster_search=search,cluster_stability=stability,
            cluster_centroids=centroids,cluster_profiles=profiles,cluster_sizes=sizes,
            pca_loadings=pd.DataFrame(rec.artifacts.pca.components_,columns=rec.artifacts.feature_cols),
            league_retrieval=pd.concat(slices,ignore_index=True),qualitative=qualitative_shortlists(rec,selected),**extra)
        paths=[]
        for suffix,frame in outputs.items():
            path=REPORT/f'{name}_{suffix}.csv'
            frame.to_csv(path,index=suffix in ['cluster_centroids','cluster_profiles','cluster_sizes'])
            paths.append(path)
        path=ROOT/f'models/real/five_league_{name}_recommender.joblib'
        rec.save(path)
        figure,axes=plt.subplots(1,3,figsize=(16,4))
        scores.pivot(index='method',columns='phase',values='mrr').plot.bar(ax=axes[0]);axes[0].set_ylabel('Pooled profile retrieval MRR')
        axes[1].plot(np.cumsum(rec.artifacts.pca.explained_variance_ratio_),'o-');axes[1].set_ylabel('Cumulative training PCA variance')
        sns.boxplot(extra['ranking_bootstrap'].query('kind == "style"'),x='method',y='top5_jaccard',ax=axes[2]);axes[2].tick_params(axis='x',rotation=45)
        figure.tight_layout();plot=REPORT/f'{name}_evaluation.png';figure.savefig(plot,dpi=140);plt.close(figure);paths.append(plot)
        holdout=scores[scores.phase.eq('holdout')&scores.method.eq(selected)].iloc[0]
        info=dict(selected_method=selected,selected_k=rec.artifacts.kmeans.n_clusters,holdout_mrr=float(holdout.mrr),
            holdout_recall_at_5=float(holdout.recall_at_5),holdout_recall_at_10=float(holdout.recall_at_10),
            pca_explained_variance=rec.artifacts.pca.explained_variance_ratio_.tolist(),cluster_diagnostics=diagnostics,
            robustness_top5_jaccard_mean=float(extra['ranking_bootstrap'].query('kind == "neighbor"').top5_jaccard.mean()),
            cluster_oob_ari_mean=float(extra['cluster_bootstrap'].adjusted_rand_out_of_bag.mean()),
            rows_by_split={key:len(value) for key,value in parts.items()},train_seasons=sorted(parts['train'].season.unique()),
            validation_season=parts['validation'].season.iloc[0],holdout_season=parts['holdout'].season.iloc[0],
            model_path=str(path.relative_to(ROOT)),model_sha256=sha256(path),training_scope='five_leagues',dataset_version=dataset_version)
        with mlflow.start_run(run_name=f'five_league_{name}_real_refit',tags={
            'owner':'tfm-team','project':'tfm-scouting','dataset':dataset_version,'dataset_kind':'real_fbref_five_leagues',
            'environment':f'Python {platform.python_version()} / {platform.system()}','git_commit':commit,
            'mlflow.source.name':'scripts/five_league_pipeline.py','mlflow.source.git.commit':commit,
            'git_dirty':str(bool(subprocess.check_output(['git','status','--porcelain','--','src','scripts','tests'],cwd=ROOT,text=True).strip())),
            'evaluation':'next_season_same_player_proxy_not_transfer_success','price_features':'excluded'}) as active:
            mlflow.log_params(dict(selected_method=selected,selected_k=info['selected_k'],features=','.join(spec['features']),
                seed=42,bootstrap_person_trials=30,preprocessing_fit='train_only',training_scope='five_leagues'))
            mlflow.log_metrics({key:info[key] for key in ['holdout_mrr','holdout_recall_at_5','holdout_recall_at_10','robustness_top5_jaccard_mean','cluster_oob_ari_mean']})
            for artifact in paths:mlflow.log_artifact(str(artifact),artifact_path='evaluation')
            mlflow.log_artifact(str(path),artifact_path='models')
            run_id=active.info.run_id
        run=client.get_run(run_id);assert run.info.status=='FINISHED'
        export=REPORT/'mlflow_export'/name;export.mkdir(parents=True,exist_ok=True)
        count=0
        for category in ['evaluation','models']:
            for artifact in client.list_artifacts(run_id,category):
                download=client.download_artifacts(run_id,artifact.path)
                target=export/artifact.path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(download,target)
                original=path if category=='models' else next(p for p in paths if p.name==target.name)
                assert sha256(target)==sha256(original);count+=1
        info.update(mlflow_run_id=run_id,exported_artifacts=count)
        (export/'run.json').write_text(json.dumps(dict(run_id=run_id,status=run.info.status,artifact_root='.',tags=run.data.tags,params=run.data.params,metrics=run.data.metrics),indent=2))
        results[name]=info
        print(name,'completed:',info['holdout_mrr'],info['holdout_recall_at_5'],flush=True)
    return results


def main():
    REPORT.mkdir(exist_ok=True)
    preserved=preserved_artifacts()
    frames,outputs,records,duplicates=prepare_data()
    code_paths=['scripts/five_league_pipeline.py','scripts/top_five_leagues.py','src/preprocessing/collected.py','src/models/collected.py','src/models/validation.py','src/models/recommend.py','src/features/styles.py','src/data/source_rights.py']
    code={path:sha256(ROOT/path) for path in code_paths}
    version=hashlib.sha256(json.dumps(dict(outputs=outputs,code=code),sort_keys=True).encode()).hexdigest()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    trained=models(frames,version,commit)
    for path,digest in preserved.items():assert sha256(ROOT/path)==digest,path
    report=dict(dataset_version=version,git_commit=commit,created_at=datetime.now(timezone.utc).isoformat(),
        code_sha256=code,outputs=outputs,raw_sources=records,preserved_sha256=preserved,
        experiments=trained,exact_duplicates_removed=duplicates,counts={name:len(frame) for name,frame in frames.items()},
        limits=['Future seasons never enter fitting; partial2025/26 excluded','Transfermarkt fields excluded from fitting; cross-source price identities provisional',
                'Profile retrieval and descriptive tactical affinity are not transfer-success or club relevance labels',
                'Core/offensive periods differ; attack_on_core is a matched-cohort feature comparison',
                'Core advanced2024/25 sparse; advancedSegunda missing','Outliers flagged, never automatically removed'])
    (REPORT/'pipeline.json').write_text(json.dumps(report,indent=2))
    print('Five-league pipeline completed.',flush=True)

if __name__=='__main__':main()
