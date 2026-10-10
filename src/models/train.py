"""Tracked experiments with dataset/Git lineage and portable output paths."""
from __future__ import annotations
import json
import os
import platform
import subprocess
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/tfm-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/tfm-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd

from src.config import FEATURE_COLS, MLFLOW_TRACKING_URI, MODELS_DIR, ROOT
from src.data.provenance import sha256
from src.models.evaluate import analyze, temporal_proxy
from src.models.recommend import PlayerRecommender
from src.preprocessing.clean import load_players


def train_and_log(n_neighbors=15, n_clusters=6, tracking_uri=MLFLOW_TRACKING_URI, allow_legacy=False):
    players = load_players()
    dataset = json.loads((ROOT / 'reports/dataset.json').read_text())
    if 'legacy' in dataset['dataset_kind'] and not allow_legacy:
        raise ValueError('Legacy provenance is unverified: final experiments blocked. Use explicit exploratory mode only.')
    if players.source.str.contains('demo|synthetic', case=False).any():
        raise ValueError('Synthetic rows cannot enter real experiments')
    if sha256(ROOT / 'data/processed/real/players.parquet') != dataset['dataset_sha256']:
        raise ValueError('Dataset fingerprint does not match the prepared dataset manifest')
    # Remove G+A because it is exactly Gls+Ast: avoid triple-weighting attack output.
    cols = [c for c in FEATURE_COLS if c != 'ga_p90' and c in players and players[c].nunique() > 1]
    rec = PlayerRecommender(n_neighbors=n_neighbors, n_clusters=n_clusters).fit(players, cols)
    metrics, baseline, robustness, stability, scenarios = analyze(rec)
    temporal = temporal_proxy(players)
    git_sha = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git','status','--porcelain','--','src','scripts','tests','requirements.txt','requirements.lock.txt','.github'],cwd=ROOT,text=True).strip())
    report = ROOT / 'reports/experiments'
    report.mkdir(parents=True, exist_ok=True)
    for name,frame in [('baselines',baseline),('robustness',robustness),('cluster_stability',stability),('scenarios',scenarios),('temporal_proxy',temporal)]:
        frame.to_csv(report / f'{name}.csv', index=False)
    pd.DataFrame(rec.artifacts.pca.components_, columns=cols).to_csv(report/'pca_loadings.csv',index=False)
    rec.players.groupby('cluster')[cols].mean().to_csv(report/'cluster_profiles.csv')
    pd.crosstab(rec.players.cluster,rec.players.pos_main).to_csv(report/'cluster_positions.csv')
    plt.figure(figsize=(6,4))
    plt.bar(np.arange(len(rec.artifacts.pca.explained_variance_ratio_))+1,rec.artifacts.pca.explained_variance_ratio_)
    plt.xlabel('Principal component'); plt.ylabel('Explained variance fraction'); plt.tight_layout()
    plt.savefig(report/'pca_variance.png'); plt.close()
    plt.figure(figsize=(6,4))
    if 'pc2' in rec.players:
        plt.scatter(rec.players.pc1,rec.players.pc2,c=rec.players.cluster,s=12,cmap='tab10')
        plt.xlabel('PC1');plt.ylabel('PC2')
    plt.tight_layout();plt.savefig(report/'clusters.png');plt.close()
    mlflow.set_tracking_uri(tracking_uri)
    experiment = 'tfm-scouting-legacy-exploratory' if allow_legacy else 'tfm-scouting-real'
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location=f'./mlartifacts/{experiment}')
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name='cosine_knn_kmeans_pca') as run:
        mlflow.set_tags({'owner':os.getenv('TFM_OWNER','tfm-team'), 'project':'tfm-scouting',
            'dataset':dataset['dataset_sha256'], 'dataset_kind':dataset['dataset_kind'],
            'environment':f'Python {platform.python_version()} / {platform.system()}',
            'git_commit':git_sha, 'git_dirty':str(dirty), 'git_dirty_scope':'source_and_dependencies', 'validation':'exploratory_descriptive_not_transfer_success'})
        mlflow.log_params(dict(n_players=len(players), n_features=len(cols), features=','.join(cols),
            n_clusters=rec.artifacts.kmeans.n_clusters, n_neighbors=n_neighbors, random_seed=42))
        mlflow.log_metrics(metrics)
        model_path = rec.save()
        mlflow.log_artifact(str(model_path), artifact_path='models')
        mlflow.log_artifacts(str(report),artifact_path='evaluation')
        mlflow.log_artifact(str(ROOT/'reports/dataset.json'),artifact_path='lineage')
        meta = dict(feature_cols=cols, metrics=metrics, model_path=model_path.relative_to(ROOT).as_posix(),
            dataset=dataset, git_commit=git_sha, git_dirty=dirty, git_dirty_scope='source_and_dependencies', run_id=run.info.run_id,
            evaluation_scope='descriptive exploratory; no transfer or future-performance claims',
            temporal_status='executed' if len(temporal) else 'blocked: fewer than two comparable consecutive seasons')
        MODELS_DIR.mkdir(parents=True,exist_ok=True)
        (MODELS_DIR/'metrics.json').write_text(json.dumps(meta,indent=2))
        mlflow.log_artifact(str(MODELS_DIR/'metrics.json'),artifact_path='models')
    print(json.dumps(meta,indent=2))
    return model_path


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--allow-legacy-exploratory',action='store_true')
    train_and_log(allow_legacy=p.parse_args().allow_legacy_exploratory)
