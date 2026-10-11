"""Log actual frozen-model external-league diagnostics; no training occurs."""
import json
import platform
import shutil
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mlflow
from mlflow.tracking import MlflowClient
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256


def main():
    folder=ROOT/'reports/top_five_leagues'
    manifest=json.loads((folder/'manifest.json').read_text())
    results=pd.read_csv(folder/'evaluation.csv')
    selected=results[results.selected_method]
    pivot=selected.pivot(index='league',columns='model',values='mrr')
    ax=pivot.plot.bar(figsize=(9,4),ylim=(0,.35),rot=20)
    ax.set_ylabel('Next-season profile retrieval MRR')
    ax.set_title('Frozen La Liga models · distinct evaluation periods')
    plt.tight_layout()
    plot=folder/'external_profile_retrieval.png'
    plt.savefig(plot,dpi=150)
    plt.close()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    mlflow.set_tracking_uri(f'sqlite:///{ROOT/"mlflow.db"}')
    mlflow.set_experiment('tfm-scouting-five-league-frozen-evaluation')
    with mlflow.start_run(run_name='real_external_league_profile_retrieval',tags={
        'owner':'tfm-team','project':'tfm-scouting','dataset':manifest['dataset_version'],
        'dataset_kind':'real_fbref_secondary_archive','environment':f'Python {platform.python_version()} / {platform.system()}',
        'git_commit':commit,'mlflow.source.git.commit':commit,'mlflow.source.name':'scripts/top_five_mlflow.py',
        'model_retrained':'False','validation_kind':'next_season_same_player_retrieval_not_transfer_success'}) as run:
        mlflow.log_params({'training_scope':'La Liga frozen existing models','serving_scope':'five leagues',
                          'core_evaluation':'2022-2023_to_2023-2024','offensive_evaluation':'2023-2024_to_2024-2025',
                          'cross_league_identity':'highest_minutes_league_before_feature_eligibility'})
        for row in selected.itertuples():
            prefix=f'{row.model}_{row.league.replace(" ","_")}'
            mlflow.log_metrics({f'{prefix}_mrr':row.mrr,f'{prefix}_recall_at_5':row.recall_at_5,f'{prefix}_queries':row.queries})
        for name in ['evaluation.csv','coverage.csv','availability.csv','manifest.json',plot.name]:
            mlflow.log_artifact(str(folder/name),artifact_path='evaluation')
        model_report=json.loads((ROOT/'reports/enrichment/pipeline.json').read_text())
        for name in ['core','offensive']:
            mlflow.log_artifact(str(ROOT/model_report['new_model_experiments'][name]['model_path']),artifact_path='models')
        run_id=run.info.run_id
    client=MlflowClient()
    recorded=client.get_run(run_id)
    assert recorded.info.status=='FINISHED'
    export=folder/'mlflow_export'
    export.mkdir(exist_ok=True)
    counts=0
    for artifact_folder in ['evaluation','models']:
        for item in client.list_artifacts(run_id,artifact_folder):
            downloaded=client.download_artifacts(run_id,item.path)
            target=export/item.path
            target.parent.mkdir(exist_ok=True,parents=True)
            shutil.copyfile(downloaded,target)
            counts+=1
    portable=dict(run_id=run_id,status=recorded.info.status,artifact_root='.',params=recorded.data.params,
                  metrics=recorded.data.metrics,tags=recorded.data.tags,exported_artifacts=counts,
                  script_sha256=sha256(ROOT/'scripts/top_five_mlflow.py'))
    (export/'run.json').write_text(json.dumps(portable,indent=2))
    assert counts==7
    print(json.dumps({'run_id':run_id,'status':recorded.info.status,'exported_artifacts':counts}))

if __name__=='__main__':main()
