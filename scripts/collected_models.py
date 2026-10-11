"""Execute and track real collected-data model comparisons in the existing layout."""
import json
import hashlib
import os
import platform
import shutil
import subprocess
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/tfm-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/tfm-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mlflow
from mlflow.tracking import MlflowClient
import numpy as np
import pandas as pd
import seaborn as sns

from src.config import ROOT
from src.data.provenance import sha256
from src.models.collected import (EXPERIMENTS, cluster_analysis, fit_experiment,
                                  qualitative_shortlists, shortlist_robustness)


def verified_inputs():
    manifest = json.loads((ROOT/'reports/collected_preprocessing.json').read_text())
    tables = {}
    for spec in EXPERIMENTS.values():
        record = manifest['outputs'][spec['table']]
        path = ROOT/record['path']
        if sha256(path) != record['sha256']:
            raise ValueError('Collected model input changed without a provenance update')
        tables[spec['table']] = pd.read_parquet(path)
    identity = json.loads((ROOT/'reports/identity_resolution.json').read_text())
    record = identity['outputs']['collected_identity_join_preview']
    if sha256(ROOT/record['path']) != record['sha256']:
        raise ValueError('Identity preview changed without provenance update')
    return manifest, identity, tables


def source_agreement(identity):
    preview = pd.read_parquet(ROOT/identity['outputs']['collected_identity_join_preview']['path'])
    rows = []
    for season, group in preview.groupby('season'):
        linked = group[group.understat_player_id.notna()]
        comparable = linked[['gls', 'understat_goals', 'xg', 'understat_xg']].dropna()
        rows.append(dict(season=season, proposed_understat_club_links=len(linked), comparable_rows=len(comparable),
            goals_exact_agreement=int(comparable.gls.eq(comparable.understat_goals).sum()),
            goals_absolute_difference_mean=float((comparable.gls-comparable.understat_goals).abs().mean()),
            xg_spearman=float(comparable[['xg','understat_xg']].corr(method='spearman').iloc[0,1]),
            interpretation='Provisional join diagnostic; provider/exposure differences are not identity labels'))
    return pd.DataFrame(rows)


def plots(name, rec, scores, search, centroids, stability, robustness):
    report = ROOT/'reports/experiments'
    filenames = []
    def save(suffix, fig):
        path = report/f'collected_{name}_{suffix}.png'
        fig.tight_layout(); fig.savefig(path, dpi=140, bbox_inches='tight'); plt.close(fig)
        filenames.append(path)
    fig, ax = plt.subplots(figsize=(11, 4))
    values = scores.pivot(index='method', columns='phase', values='mrr')
    values.plot.bar(ax=ax); ax.set_ylabel('MRR (uniform score ties)')
    ax.set_title(f'{name}: next-season identity/profile retrieval; not transfer success')
    save('retrieval', fig)
    fig, ax = plt.subplots(figsize=(7, 4))
    variance = rec.artifacts.pca.explained_variance_ratio_
    ax.bar(np.arange(1, len(variance)+1), variance, label='Per component')
    ax.plot(np.arange(1, len(variance)+1), np.cumsum(variance), 'o-', label='Cumulative')
    ax.set_ylim(0, 1); ax.set_xlabel('Component'); ax.set_ylabel('Explained variance'); ax.legend()
    save('pca_variance', fig)
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.heatmap(pd.DataFrame(rec.artifacts.pca.components_, columns=rec.artifacts.feature_cols,
                            index=[f'PC{i+1}' for i in range(len(variance))]), center=0, cmap='vlag', annot=True, fmt='.2f', ax=ax)
    ax.set_title('Training PCA loadings; sign is arbitrary, components are not tactical labels')
    save('pca_loadings', fig)
    fig, ax = plt.subplots(figsize=(10, max(3, len(centroids)*.65)))
    sns.heatmap(centroids, center=0, cmap='vlag', annot=True, fmt='.2f', ax=ax)
    ax.set_title('K-means centroids in training-standardized units')
    save('cluster_profiles', fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(search.k, search.training_silhouette, 'o-'); axes[0].set_xlabel('k'); axes[0].set_ylabel('Training silhouette')
    axes[1].bar(stability.seed.astype(str), stability.adjusted_rand); axes[1].set_ylabel('ARI against seed 42'); axes[1].set_ylim(0, 1.01)
    save('cluster_selection', fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.boxplot(data=robustness, x='position', y='top5_jaccard', ax=ax)
    ax.set_ylim(0, 1.05); ax.set_title('Selected-method shortlist stability under training-row bootstrap')
    save('robustness', fig)
    return filenames


def export_logged_run(client, run_id, name):
    """Download genuinely logged artifacts; keep portable paths in the export."""
    record = client.get_run(run_id)
    if record.info.status != 'FINISHED':
        raise ValueError('MLflow experiment did not finish')
    export = ROOT/'reports/mlflow_export'
    for folder in ['evaluation', 'models', 'lineage']:
        for artifact in client.list_artifacts(run_id, folder):
            if artifact.is_dir:
                raise ValueError('Unexpected nested artifact directory')
            source = Path(client.download_artifacts(run_id, artifact.path))
            target = export/folder/source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if sha256(source) != sha256(target):
                raise ValueError('MLflow artifact export checksum mismatch')
    payload = dict(run_id=run_id, experiment_id=record.info.experiment_id, status=record.info.status,
                   artifact_root='.', runtime_artifact_uri_scope='machine-local URI omitted',
                   params=record.data.params, metrics=record.data.metrics, tags=record.data.tags)
    (export/f'collected_{name}_run.json').write_text(json.dumps(payload, indent=2)+'\n')


def run():
    manifest, identity, tables = verified_inputs()
    git_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--', 'src', 'scripts', 'tests', 'requirements.txt'], cwd=ROOT, text=True).strip())
    code_paths = ['src/models/collected.py', 'src/models/recommend.py', 'src/data/source_rights.py',
                  'src/features/styles.py', 'src/config.py', 'scripts/collected_models.py']
    code = {path: sha256(ROOT/path) for path in code_paths}
    dataset_version = hashlib.sha256(json.dumps(dict(base=manifest['dataset_version'], code=code,
        experiments=EXPERIMENTS, seed=42), sort_keys=True).encode()).hexdigest()
    report = ROOT/'reports/experiments'
    report.mkdir(parents=True, exist_ok=True)
    agreement = source_agreement(identity)
    agreement.to_csv(report/'collected_source_agreement.csv', index=False)
    mlflow.set_tracking_uri('sqlite:///mlflow.db')
    experiment = 'tfm-scouting-collected-real-proxies'
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location=f'./mlartifacts/{experiment}')
    mlflow.set_experiment(experiment)
    result = dict(dataset_version=dataset_version, base_dataset_version=manifest['dataset_version'],
        identity_dataset_version=identity['dataset_version'], matching_method_user_accepted=True,
        identity_links_manually_verified=False, git_commit=git_commit, git_source_dirty=dirty, code_hashes=code,
        input_manifest_sha256=sha256(ROOT/'reports/collected_preprocessing.json'),
        experiment_scope='Real FBref secondary archives; temporal identity/profile persistence only',
        learned_features_source='FBref only; no provisional cross-source features or market values',
        current_app_model_replaced=False, experiments={},
        limitations=['Retrieval does not measure transfer success, future performance prediction or club-fit relevance',
                     'Future candidate profiles are evaluation targets; they cannot be known at scouting time',
                     'Returning 450+ minute outfield players create selection/survivorship bias',
                     'Unknown archive publication dates prevent strict historical as-of claims',
                     'Segunda, goalkeeper, budget and genuine transfer validation remain unavailable',
                     'Cross-source identity method accepted; individual links still unverified'])
    for name, spec in EXPERIMENTS.items():
        print('Fitting collected experiment:', name, flush=True)
        rec, parts, search, scores, details, selected = fit_experiment(tables[spec['table']], spec)
        stability, centroids, profiles, sizes, cluster_metrics = cluster_analysis(rec)
        robustness = shortlist_robustness(rec)
        qualitative = qualitative_shortlists(rec, selected)
        loadings = pd.DataFrame(rec.artifacts.pca.components_, columns=rec.artifacts.feature_cols)
        loadings.index = [f'PC{i+1}' for i in range(len(loadings))]
        frames = dict(retrieval=scores, retrieval_queries=details, cluster_search=search,
                      cluster_stability=stability, cluster_centroids=centroids,
                      cluster_profiles=profiles, cluster_sizes=sizes,
                      cluster_positions=pd.crosstab(rec.players.cluster, rec.players.pos_main),
                      cluster_seasons=pd.crosstab(rec.players.cluster, rec.players.season),
                      pca_loadings=loadings, robustness=robustness, shortlists=qualitative)
        csv_paths = []
        for suffix, frame in frames.items():
            path = report/f'collected_{name}_{suffix}.csv'
            frame.to_csv(path, index=suffix in ['cluster_centroids', 'cluster_profiles', 'cluster_sizes',
                                               'cluster_positions', 'cluster_seasons', 'pca_loadings'])
            csv_paths.append(path)
        figures = plots(name, rec, scores, search, centroids, stability, robustness)
        model_path = rec.save(ROOT/f'models/real/collected_{name}_recommender.joblib')
        holdout = scores[(scores.phase == 'holdout') & scores.method.eq(selected)].iloc[0]
        info = dict(feature_cols=rec.artifacts.feature_cols, selected_method=selected,
                    selection_rule='Highest validation MRR among profile methods; holdout never selects parameters',
                    cohort_rows={part:len(frame) for part, frame in parts.items()},
                    cohort_seasons={part:sorted(frame.season.unique()) for part,frame in parts.items()},
                    selected_k=rec.artifacts.kmeans.n_clusters,
                    pca_explained_variance=rec.artifacts.pca.explained_variance_ratio_.tolist(),
                    cluster_analysis=cluster_metrics, bootstrap_top5_jaccard_mean=float(robustness.top5_jaccard.mean()),
                    holdout_metrics={key:float(holdout[key]) for key in ['mrr','recall_at_5','recall_at_10','ndcg_at_10']},
                    model_path=model_path.relative_to(ROOT).as_posix(), model_sha256=sha256(model_path),
                    imputer_statistics=rec.artifacts.imputer.statistics_.tolist(),
                    scaler_mean=rec.artifacts.scaler.mean_.tolist(),
                    scaler_scale=rec.artifacts.scaler.scale_.tolist(),
                    validation_queries=int(scores[scores.phase.eq('validation')].queries.iloc[0]),
                    holdout_queries=int(holdout.queries),
                    output_files={path.relative_to(ROOT).as_posix(): sha256(path) for path in csv_paths+figures})
        lineage = report/f'collected_{name}_lineage.json'
        lineage.write_text(json.dumps(dict(dataset_version=dataset_version, git_commit=git_commit,
            git_source_dirty=dirty, base_dataset_version=manifest['dataset_version'],
            identity_method_accepted_but_links_unverified=True, model_inputs_source='fbref_worldfootballr',
            parameters=spec, result=info), indent=2)+'\n')
        with mlflow.start_run(run_name=f'collected_{name}_chronological_profile_retrieval') as active:
            mlflow.set_tags(dict(owner=os.getenv('TFM_OWNER','tfm-team'), project='tfm-scouting',
                dataset=dataset_version, dataset_kind='real_collected_fbref_secondary_archive',
                environment=f'Python {platform.python_version()} / {platform.system()}',
                git_commit=git_commit, git_dirty=str(dirty), validation='temporal_profile_proxy_not_transfer_success',
                identity_mapping='method_accepted_links_unverified_not_used_as_learned_features',
                analysis_design='post_hoc_matched_cohort_ablation' if name == 'attack_on_core' else 'chronological_profile_comparison',
                **{'mlflow.source.name':'scripts/collected_models.py'}))
            mlflow.log_params(dict(cohort=name, features=','.join(rec.artifacts.feature_cols),
                train_rows=len(parts['train']), validation_rows=len(parts['validation']), holdout_rows=len(parts['holdout']),
                selected_method=selected, selected_k=rec.artifacts.kmeans.n_clusters,
                pca_dimensions=rec.artifacts.pca.n_components_, random_seed=42,
                bootstrap_replicates=200, shortlist_bootstrap_trials=20, imputation='training_median', scaling='training_standard'))
            logged_metrics = {f'holdout_{key}':value for key,value in info['holdout_metrics'].items()}
            logged_metrics.update(cluster_metrics)
            logged_metrics.update(pca_variance_sum=sum(info['pca_explained_variance']),
                                  bootstrap_top5_jaccard_mean=info['bootstrap_top5_jaccard_mean'])
            for row in scores.itertuples():
                for key in ['mrr','recall_at_5','recall_at_10','ndcg_at_10']:
                    logged_metrics[f'{row.phase}_{row.method}_{key}'] = float(getattr(row,key))
            mlflow.log_metrics(logged_metrics)
            for path in csv_paths+figures:
                mlflow.log_artifact(str(path), artifact_path='evaluation')
            mlflow.log_artifact(str(model_path), artifact_path='models')
            mlflow.log_artifact(str(lineage), artifact_path='lineage')
            info['mlflow_run_id'] = active.info.run_id
        export_logged_run(MlflowClient(), info['mlflow_run_id'], name)
        result['experiments'][name] = info
        print(name, 'validation-selected:', selected, 'holdout:', info['holdout_metrics'], flush=True)
    # A same-season/same-person diagnostic avoids comparing the different main
    # holdout years as if they were a controlled feature ablation. This additional
    # comparison follows the initial trials and is explicitly post hoc.
    core = pd.read_csv(report/'collected_core_retrieval_queries.csv')
    attack = pd.read_csv(report/'collected_attack_on_core_retrieval_queries.csv')
    pairs = core[core.method.eq('euclidean_profile')].merge(
        attack[attack.method.eq('euclidean_profile')], on=['phase','entity_id'], suffixes=('_core','_attack'), validate='one_to_one')
    ablation = []
    for phase, group in pairs.groupby('phase'):
        assert (group.candidate_count_core == group.candidate_count_attack).all()
        rng = np.random.default_rng(42)
        indexes = rng.integers(0, len(group), (200, len(group)))
        difference = (group.reciprocal_rank_core-group.reciprocal_rank_attack).to_numpy()
        low, high = np.quantile(difference[indexes].mean(axis=1), [.025,.975])
        ablation.append(dict(phase=phase, queries=len(group), method='euclidean_profile',
            mrr_core=float(group.reciprocal_rank_core.mean()), mrr_attack=float(group.reciprocal_rank_attack.mean()),
            mrr_difference=float(difference.mean()), difference_ci_low=float(low), difference_ci_high=float(high),
            design='post_hoc_matched_cohort_diagnostic_not_independent_confirmation'))
    pd.DataFrame(ablation).to_csv(report/'collected_feature_ablation.csv', index=False)
    (ROOT/'reports/collected_model_results.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    run()
