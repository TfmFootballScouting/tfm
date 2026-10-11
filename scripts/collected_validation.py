"""Run offline post-hoc diagnostics; preserve fixed models and source tables."""
import hashlib
import json
import os
import platform
import subprocess

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
from src.models.collected import EXPERIMENTS, cohorts
from src.models.recommend import PlayerRecommender
from src.models.validation import position_retrieval, resampling_validation, temporal_validation
from scripts.collected_models import export_logged_run

TRIALS = 30
SEED = 42


def verified_base():
    base_path = ROOT/'reports/collected_model_results.json'
    base = json.loads(base_path.read_text())
    manifest_path = ROOT/'reports/collected_preprocessing.json'
    if sha256(manifest_path) != base['input_manifest_sha256']:
        raise ValueError('Base data manifest changed')
    manifest = json.loads(manifest_path.read_text())
    preserved = {base_path.relative_to(ROOT).as_posix(): sha256(base_path)}
    for path, expected in base['code_hashes'].items():
        if sha256(ROOT/path) != expected:
            raise ValueError(f'Base model implementation changed: {path}')
        preserved[path] = expected
    for records in [manifest['inputs'], manifest['source_snapshots'], manifest['outputs']]:
        records = records.values() if isinstance(records, dict) else records
        for record in records:
            path = ROOT/record['path']
            if sha256(path) != record['sha256']:
                raise ValueError(f'Changed source/preprocessing evidence: {record["path"]}')
            preserved[record['path']] = record['sha256']
    for info in base['experiments'].values():
        for path, expected in {info['model_path']: info['model_sha256'], **info['output_files']}.items():
            if sha256(ROOT/path) != expected:
                raise ValueError(f'Base model or evaluation changed: {path}')
            preserved[path] = expected
    return base, manifest, preserved


def plots(name, frames):
    paths = []
    def save(suffix, fig):
        path = ROOT/f'reports/experiments/collected_validation_{name}_{suffix}.png'
        fig.tight_layout(); fig.savefig(path, dpi=135, bbox_inches='tight'); plt.close(fig)
        paths.append(path)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    clusters = frames['cluster_bootstrap']
    axes[0, 0].plot(clusters.trial, clusters.adjusted_rand_reference, 'o-', label='All training rows')
    axes[0, 0].plot(clusters.trial, clusters.adjusted_rand_out_of_bag, 'x-', label='OOB players')
    axes[0, 0].set_ylim(-.05, 1.05); axes[0, 0].set_ylabel('Cluster ARI'); axes[0, 0].legend()
    sns.boxplot(data=frames['pca_loading_bootstrap'], x='component', y='absolute_loading_cosine', ax=axes[0, 1])
    axes[0, 1].set_ylim(0, 1.05); axes[0, 1].set_title('Matched directions in common standardized coordinates')
    sns.boxplot(data=frames['pca_subspace_bootstrap'], x='dimensions', y='maximum_angle_degrees', ax=axes[1, 0])
    axes[1, 0].set_title('PCA subspace angles: lower is more stable')
    sns.boxplot(data=frames['ranking_bootstrap'].query('kind == "neighbor"'), x='position', y='top5_jaccard', ax=axes[1, 1])
    axes[1, 1].set_ylim(0, 1.05); axes[1, 1].set_title('Selected neighbors; fixed historical gallery')
    fig.suptitle(f'{name}: 30 person-block refits, fixed k and PCA width')
    save('bootstrap', fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, phase in zip(axes, ['validation', 'holdout']):
        frame = frames['position_retrieval']
        frame = frame[frame.phase.eq(phase) & frame.method.isin(['euclidean_profile', 'goals_assists', 'pca4_euclidean', 'cluster_cosine'])]
        frame.pivot(index='position', columns='method', values='recall_at_5').plot.bar(ax=ax)
        ax.set_ylabel('Recall@5 (identity/profile proxy)'); ax.set_title(f'{phase}: '+frame.evaluation_season.iloc[0])
    save('positions', fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    drift = frames['feature_drift']
    sns.heatmap(drift.pivot(index='feature', columns='season', values='mean_shift_training_sd'),
                center=0, cmap='vlag', annot=True, fmt='.2f', ax=axes[0])
    sns.heatmap(drift.pivot(index='feature', columns='season', values='js_divergence'),
                vmin=0, vmax=1, cmap='mako', annot=True, fmt='.3f', ax=axes[1])
    axes[0].set_title('Observed mean change in training SD'); axes[1].set_title('JS divergence: fixed training bins')
    save('drift', fig)
    fig, ax = plt.subplots(figsize=(12, 4))
    sns.boxplot(data=frames['ranking_bootstrap'].query('kind == "style"'), x='method', y='top5_jaccard', hue='position', ax=ax)
    ax.set_ylim(0, 1.05); ax.set_title('Original supported styles: person-block preprocessing stability')
    ax.tick_params(axis='x', rotation=20)
    save('styles', fig)
    return paths


def run():
    base, manifest, preserved = verified_base()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--', 'src', 'scripts', 'tests', 'requirements.txt'], cwd=ROOT, text=True).strip())
    code_paths = ['src/models/validation.py', 'scripts/collected_validation.py',
                  'scripts/collected_validation_notebook.py', 'src/models/collected.py',
                  'src/models/recommend.py', 'src/features/styles.py', 'src/config.py']
    code = {path: sha256(ROOT/path) for path in code_paths}
    parameters = dict(person_block_trials=TRIALS, seed=SEED, query_bootstrap_trials=500,
                      k='fixed_previously_selected', pca='fixed_previously_selected_width',
                      interpretation='post_hoc_diagnostics_no_parameter_tuning')
    version = hashlib.sha256(json.dumps(dict(base=sha256(ROOT/'reports/collected_model_results.json'),
        code=code, parameters=parameters), sort_keys=True).encode()).hexdigest()
    result = dict(validation_version=version, dataset_version=base['dataset_version'],
        base_dataset_version=manifest['dataset_version'], git_commit=commit, git_source_dirty=dirty,
        code_hashes=code, parameters=parameters, preserved_input_hashes=preserved,
        scope='Post-hoc real FBref archive diagnostics; stability and temporal profile retrieval only',
        fitting_scope='Original development seasons only; whole-player blocks, all their observed seasons',
        limitations=['Bootstrap distributions are conditional diagnostics, not external accuracy intervals',
                     'Previously viewed holdouts and subgroup analyses are post hoc, not new confirmation',
                     'Frozen-cluster transitions are descriptive and subject to returning-player selection',
                     'PCA directions use common standardized axes; eigenvector rotation is assessed via subspaces',
                     'Six original styles remain expert-defined proxies, without independently measured tactical relevance',
                     'Dated budgets, complete Segunda data, actual transfer validation and verified cross-source identities remain unavailable'],
        current_app_model_replaced=False, experiments={})
    mlflow.set_tracking_uri('sqlite:///mlflow.db')
    experiment = 'tfm-scouting-collected-validation'
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location=f'./mlartifacts/{experiment}')
    mlflow.set_experiment(experiment)
    for name, spec in EXPERIMENTS.items():
        print('Validating fixed real-data model:', name, flush=True)
        info = base['experiments'][name]
        rec = PlayerRecommender.load(ROOT/info['model_path'])
        record = manifest['outputs'][spec['table']]
        parts = cohorts(pd.read_parquet(ROOT/record['path']), spec['split'])
        if set(rec.players.player_id) != set(parts['train'].player_id) or rec.players.season.max() >= parts['validation'].season.min():
            raise ValueError('Frozen model does not correspond to development cohort')
        frames = resampling_validation(rec, TRIALS, SEED)
        frames.update(temporal_validation(rec, parts))
        details = pd.read_csv(ROOT/f'reports/experiments/collected_{name}_retrieval_queries.csv')
        frames['position_retrieval'] = position_retrieval(details)
        paths = []
        for suffix, frame in frames.items():
            path = ROOT/f'reports/experiments/collected_validation_{name}_{suffix}.csv'
            frame.to_csv(path, index=False)
            paths.append(path)
        paths.extend(plots(name, frames))
        clusters = frames['cluster_bootstrap']
        ranking = frames['ranking_bootstrap']
        spaces = frames['pca_subspace_bootstrap']
        metrics = dict(cluster_ari_reference_mean=float(clusters.adjusted_rand_reference.mean()),
            cluster_ari_reference_min=float(clusters.adjusted_rand_reference.min()),
            cluster_ari_oob_mean=float(clusters.adjusted_rand_out_of_bag.mean()),
            cluster_ari_oob_min=float(clusters.adjusted_rand_out_of_bag.min()),
            cluster_oob_trials_measured=int(clusters.adjusted_rand_out_of_bag.notna().sum()),
            neighbor_top5_jaccard_mean=float(ranking[ranking.kind.eq('neighbor')].top5_jaccard.mean()),
            style_top5_jaccard_mean=float(ranking[ranking.kind.eq('style')].top5_jaccard.mean()),
            pca2_max_angle_mean=float(spaces[spaces.dimensions.eq(2)].maximum_angle_degrees.mean()),
            pca4_max_angle_mean=float(spaces[spaces.dimensions.eq(4)].maximum_angle_degrees.mean()))
        experiment_info = dict(base_run_id=info['mlflow_run_id'], base_model_path=info['model_path'],
            base_model_sha256=info['model_sha256'], selected_method=info['selected_method'],
            train_rows=len(parts['train']), train_people=parts['train'].entity_id.nunique(),
            train_seasons=sorted(parts['train'].season.unique()), metrics=metrics,
            output_files={path.relative_to(ROOT).as_posix(): sha256(path) for path in paths})
        lineage = ROOT/f'reports/experiments/collected_validation_{name}_lineage.json'
        lineage.write_text(json.dumps(dict(validation_version=version, dataset_version=base['dataset_version'],
            git_commit=commit, git_source_dirty=dirty, code_hashes=code, parameters=parameters,
            experiment=experiment_info), indent=2)+'\n')
        with mlflow.start_run(run_name=f'collected_validation_{name}_post_hoc') as active:
            mlflow.set_tags(dict(owner=os.getenv('TFM_OWNER', 'tfm-team'), project='tfm-scouting',
                dataset=base['dataset_version'], dataset_kind='real_collected_fbref_secondary_archive',
                validation_version=version, environment=f'Python {platform.python_version()} / {platform.system()}',
                git_commit=commit, git_dirty=str(dirty), base_model_run_id=info['mlflow_run_id'],
                analysis_design='post_hoc_person_block_stability_and_subgroup_diagnostics',
                validation='profile_stability_not_transfer_success', **{'mlflow.source.name': 'scripts/collected_validation.py'}))
            mlflow.log_params(dict(cohort=name, **parameters, train_people=experiment_info['train_people'],
                train_rows=len(parts['train']), selected_k=rec.artifacts.kmeans.n_clusters,
                pca_dimensions=rec.artifacts.pca.n_components_))
            mlflow.log_metrics({key: value for key, value in metrics.items() if np.isfinite(value)})
            for path in paths:
                mlflow.log_artifact(str(path), artifact_path='evaluation')
            mlflow.log_artifact(str(lineage), artifact_path='lineage')
            experiment_info['mlflow_run_id'] = active.info.run_id
        export_logged_run(MlflowClient(), experiment_info['mlflow_run_id'], 'validation_'+name)
        result['experiments'][name] = experiment_info
        print(name, metrics, flush=True)
    for path, expected in preserved.items():
        if sha256(ROOT/path) != expected:
            raise ValueError(f'Validation modified preserved evidence: {path}')
    (ROOT/'reports/collected_validation_results.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    run()
