"""Offline cleaning, review integration, EDA and eligible real-data model reruns."""
import hashlib
import json
import os
import platform
import subprocess

os.environ.setdefault('MPLCONFIGDIR', '/tmp/tfm-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
import seaborn as sns
from mlflow.tracking import MlflowClient

from src.config import ROOT, FEATURE_COLS, PLAY_STYLES
from src.data.source_rights import require_model_data_use, SourceUseRestricted
from src.preprocessing.enrichment import clean_performances, aggregate_seasons, clean_transfers, merge_review_only, field_description
from src.models.collected import EXPERIMENTS, fit_experiment, cluster_analysis, qualitative_shortlists, shortlist_robustness
from scripts.collected_models import verified_inputs
from scripts.salimt_history_audit import sha

OUT = ROOT / 'data/processed/real'
REPORT = ROOT / 'reports/enrichment'


def recorded_prices(seasons, values):
    """Reported-date association for audit, never an operational budget value."""
    left = seasons[['source_player_id', 'season', 'league', 'season_start_year']].copy()
    left['report_cutoff'] = pd.to_datetime((left.season_start_year + 1).astype(str) + '-06-30')
    right = values[['source_player_id', 'valuation_date', 'market_value_eur']].copy()
    joined = pd.merge_asof(left.sort_values('report_cutoff'), right.sort_values('valuation_date'),
                           left_on='report_cutoff', right_on='valuation_date', by='source_player_id', direction='backward')
    joined = joined.rename(columns={'market_value_eur': 'reported_value_eur_not_budget',
                                    'valuation_date': 'reported_value_date'})
    joined['zero_value_ambiguous'] = joined.reported_value_eur_not_budget.eq(0)
    joined['historical_budget_eligible'] = False
    joined['original_source'] = 'Transfermarkt.com'
    joined['ml_use_status'] = values.ml_use_status.iloc[0]
    joined['association_status'] = 'reported_date_only_publication_unknown_review_only'
    return joined


def run_models(dataset_version, code_commit):
    """Refit only the eligible unchanged FBref cohorts, to new artifact paths."""
    base_manifest, _, tables = verified_inputs()
    experiment = 'tfm-scouting-enrichment-eligible-real-rerun'
    mlflow.set_tracking_uri('sqlite:///mlflow.db')
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location='./mlartifacts/' + experiment)
    mlflow.set_experiment(experiment)
    client = MlflowClient()
    results = {}
    for name, spec in EXPERIMENTS.items():
        require_model_data_use(tables[spec['table']])
        rec, parts, search, scores, details, selected = fit_experiment(tables[spec['table']], spec)
        stability, centroids, profiles, sizes, diagnostics = cluster_analysis(rec)
        robustness = shortlist_robustness(rec)
        shortlists = qualitative_shortlists(rec, selected)
        frames = {'retrieval': scores, 'queries': details, 'cluster_search': search,
                  'cluster_stability': stability, 'cluster_centroids': centroids,
                  'cluster_profiles': profiles, 'cluster_sizes': sizes,
                  'robustness': robustness, 'shortlists': shortlists,
                  'pca_loadings': pd.DataFrame(rec.artifacts.pca.components_, columns=rec.artifacts.feature_cols)}
        paths = []
        for suffix, frame in frames.items():
            path = REPORT / f'{name}_{suffix}.csv'
            frame.to_csv(path, index=True if suffix in ['cluster_centroids', 'cluster_profiles', 'cluster_sizes'] else False)
            paths.append(path)
        model = ROOT / f'models/real/enrichment_{name}_recommender.joblib'
        rec.save(model)
        figure, axes = plt.subplots(1, 2, figsize=(12, 4))
        scores.pivot(index='method', columns='phase', values='mrr').plot.bar(ax=axes[0])
        axes[0].set_ylabel('Temporal profile retrieval MRR')
        axes[1].plot(np.cumsum(rec.artifacts.pca.explained_variance_ratio_), 'o-')
        axes[1].set_ylabel('Cumulative training PCA variance'); axes[1].set_xlabel('Component index from zero')
        figure.tight_layout()
        plot = REPORT / f'{name}_evaluation.png'; figure.savefig(plot, dpi=130); plt.close(figure)
        paths.append(plot)
        holdout = scores[scores.phase.eq('holdout') & scores.method.eq(selected)].iloc[0]
        info = {'selected_method': selected, 'holdout_mrr': float(holdout.mrr),
                'holdout_recall_at_5': float(holdout.recall_at_5), 'holdout_recall_at_10': float(holdout.recall_at_10),
                'pca_explained_variance': rec.artifacts.pca.explained_variance_ratio_.tolist(),
                'selected_k': rec.artifacts.kmeans.n_clusters,
                'cluster_diagnostics': diagnostics,
                'robustness_top5_jaccard_mean': float(robustness.top5_jaccard.mean()),
                'rows_by_split': {key: len(frame) for key, frame in parts.items()},
                'model_path': str(model.relative_to(ROOT)), 'model_sha256': sha(model),
                'learned_dataset_version': base_manifest['dataset_version'],
                'learned_features_source': 'FBref only; uploaded Transfermarkt data blocked',
                'six_style_definitions_preserved': list(PLAY_STYLES)}
        lineage = REPORT / f'{name}_lineage.json'
        lineage.write_text(json.dumps(info, indent=2) + '\n')
        paths.append(lineage)
        with mlflow.start_run(run_name=f'{name}_real_eligible_rerun') as active:
            mlflow.set_tags({'owner': os.getenv('TFM_OWNER', 'tfm-team'), 'project': 'tfm-scouting',
                'dataset': dataset_version, 'dataset_kind': 'real_fbref_only_enrichment_excluded',
                'learned_dataset': base_manifest['dataset_version'],
                'mlflow.source.name': 'scripts/enriched_pipeline.py',
                'environment': f'Python {platform.python_version()} / {platform.system()}',
                'git_commit': code_commit,
                'git_dirty': str(bool(subprocess.check_output(['git', 'status', '--porcelain', '--', 'src', 'scripts', 'tests'], cwd=ROOT, text=True).strip())),
                'evaluation': 'temporal_profile_proxy_not_transfer_success', 'enrichment_training': 'blocked_by_source_and_identity_checks'})
            mlflow.log_params({'selected_method': selected, 'selected_k': info['selected_k'],
                               'features': ','.join(spec['features']), 'seed': 42, 'median_and_scaler_fit': 'train_only'})
            mlflow.log_metrics({key: info[key] for key in ['holdout_mrr', 'holdout_recall_at_5', 'holdout_recall_at_10', 'robustness_top5_jaccard_mean']})
            for path in paths: mlflow.log_artifact(str(path), artifact_path='evaluation')
            mlflow.log_artifact(str(model), artifact_path='models')
            run_id = active.info.run_id
        record = client.get_run(run_id)
        if record.info.status != 'FINISHED': raise ValueError('Model run not finished')
        export = REPORT / 'mlflow_export' / name
        export.mkdir(parents=True, exist_ok=True)
        count = 0
        for folder in ['evaluation', 'models']:
            for artifact in client.list_artifacts(run_id, folder):
                downloaded = client.download_artifacts(run_id, artifact.path, str(export))
                original = model if folder == 'models' else next(path for path in paths if path.name == artifact.path.split('/')[-1])
                if sha(downloaded) != sha(original): raise ValueError('MLflow artifact checksum mismatch')
                count += 1
        info['mlflow_run_id'] = run_id; info['exported_artifacts'] = count
        (export / 'run.json').write_text(json.dumps({'status': record.info.status, 'run_id': run_id,
            'artifact_root': '.', 'params': record.data.params, 'tags': record.data.tags, 'metrics': record.data.metrics}, indent=2) + '\n')
        results[name] = info
        print(name, info['holdout_mrr'], flush=True)
    return results


def run():
    REPORT.mkdir(parents=True, exist_ok=True)
    previous = json.loads((ROOT / 'reports/salimt_history_audit.json').read_text())
    preserved = {**previous['preserved_input_sha256'], **previous['outputs_sha256']}
    for name in ['reports/salimt_history_audit.json', 'reports/salimt_history_verification.json',
                 'scripts/salimt_history_audit.py', 'reports/collected_model_results.json']:
        preserved[name] = sha(ROOT / name)
    for name, digest in preserved.items():
        if sha(ROOT / name) != digest: raise ValueError(f'Previous evidence changed: {name}')
    print('Verified prior inputs; cleaning source histories.', flush=True)
    stints = clean_performances(pd.read_parquet(OUT / 'collected_salimt_performance_history.parquet'),
                                pd.read_parquet(OUT / 'collected_salimt_profiles.parquet'))
    seasons = aggregate_seasons(stints)
    transfers = clean_transfers(pd.read_parquet(OUT / 'collected_salimt_transfer_history.parquet'))
    club_seasons = pd.read_parquet(OUT / 'collected_salimt_spain_team_seasons.parquet')
    contexts = []
    for direction in ['from', 'to']:
        membership = club_seasons[['club_id', 'season', 'competition_id']].rename(columns={'club_id': direction + '_team_id'})
        context = transfers.merge(membership, on=[direction + '_team_id', 'season'], how='inner', validate='many_to_many')
        context['club_context_direction'] = direction
        contexts.append(context)
    spanish_transfers = pd.concat(contexts, ignore_index=True)
    base = pd.read_parquet(OUT / 'collected_player_seasons.parquet')
    preview = merge_review_only(base, seasons, pd.read_parquet(OUT / 'collected_salimt_identity_candidates.parquet'))
    prices = recorded_prices(seasons, pd.read_parquet(OUT / 'collected_salimt_values.parquet'))
    frames = {'player_club_seasons': stints, 'player_seasons': seasons,
              'transfers': transfers, 'spain_transfer_context': spanish_transfers,
              'integration_review': preview, 'reported_price_context': prices}
    print('Cleaned and integrated review tables:', {name: len(frame) for name, frame in frames.items()}, flush=True)
    outputs = {}
    for name, frame in frames.items():
        path = OUT / f'collected_enrichment_{name}.parquet'
        frame.to_parquet(path, index=False); outputs[str(path.relative_to(ROOT))] = sha(path)
    blocked = {}
    for name, frame in frames.items():
        try: require_model_data_use(frame)
        except (ValueError, SourceUseRestricted) as exc: blocked[name] = str(exc)
        else: raise ValueError(f'Restricted enrichment unexpectedly eligible: {name}')
    quality = seasons.groupby(['season', 'league']).agg(rows=('source_player_id', 'size'),
        people=('source_player_id', 'nunique'), minutes_missing=('minutes_played', lambda x: x.isna().sum()),
        eligible_minutes=('minutes_eligible', 'sum'), multi_club=('club_count', lambda x: x.gt(1).sum()),
        inconsistent=('count_inconsistency', 'sum'), outliers=('performance_outlier', 'sum')).reset_index()
    quality.to_csv(REPORT / 'season_quality.csv', index=False)
    dictionary = []
    for name, frame in frames.items():
        for column in frame:
            description, unit = field_description(column)
            dictionary.append({'table': name, 'column': column, 'dtype': str(frame[column].dtype),
                'missing': int(frame[column].isna().sum()), 'definition': description,
                'policy': 'Source-prefixed fields are review-only; raw values retained; missing is unknown; current profiles are not historical evidence.',
                'unit': unit})
    pd.DataFrame(dictionary).to_csv(REPORT / 'dictionary.csv', index=False)
    agreement = preview[['season', 'league', 'entity_id', 'minutes', 'gls', 'ast',
                          'salimt_minutes_played', 'salimt_goals', 'salimt_assists']].copy()
    agreement['minutes_agree'] = agreement.minutes.eq(agreement.salimt_minutes_played) & agreement.minutes.notna()
    agreement['goals_agree'] = agreement.gls.eq(agreement.salimt_goals) & agreement.gls.notna()
    agreement['assists_agree'] = agreement.ast.eq(agreement.salimt_assists) & agreement.ast.notna()
    agreement.to_csv(REPORT / 'cross_source_agreement.csv', index=False)
    coverage = seasons.groupby(['season', 'league'])[['gls_p90', 'ast_p90', 'ga_p90']].count()
    for feature in FEATURE_COLS:
        if feature not in coverage: coverage[feature] = 0
    coverage.reset_index().to_csv(REPORT / 'mandatory_feature_coverage.csv', index=False)
    # Descriptive IQR flags use development years only and never remove rows or
    # participate in model fitting; small-minute per-90 artefacts are excluded.
    tails = []
    for league, group in seasons.groupby('league'):
        development = group[group.season_start_year.le(2022) & group.minutes_eligible]
        for column in ['minutes_played', 'gls_p90', 'ast_p90']:
            q1, q3 = development[column].quantile([.25, .75])
            lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
            for season, rows in group[group.minutes_eligible].groupby('season'):
                tails.append({'league': league, 'season': season, 'field': column,
                    'development_IQR_low': lo, 'development_IQR_high': hi,
                    'observed': int(rows[column].notna().sum()),
                    'outside_development_IQR': int((rows[column].lt(lo) | rows[column].gt(hi)).sum()),
                    'policy': 'descriptive flag only; no deletion or winsorization'})
    pd.DataFrame(tails).to_csv(REPORT / 'distribution_tail_flags.csv', index=False)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    sns.heatmap(seasons[['minutes_played', 'goals', 'assists', 'gls_p90', 'ast_p90']].isna().mean().to_frame('missing fraction'), annot=True, ax=axes[0], vmin=0, vmax=1)
    sns.histplot(data=seasons, x='minutes_played', hue='league', element='step', ax=axes[1])
    # Correlations describe observed source rows; missing pairs are not imputed.
    sns.heatmap(seasons[['minutes_played', 'goals', 'assists', 'gls_p90', 'ast_p90']].corr(method='spearman'), vmin=-1, vmax=1, annot=True, fmt='.2f', ax=axes[2])
    fig.tight_layout(); fig.savefig(REPORT / 'quality_distributions_correlations.png', dpi=140); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    sns.boxplot(data=seasons[seasons.minutes_eligible], x='season', y='gls_p90', hue='league', ax=axes[0])
    roles = stints.groupby('position_source').agg(rows=('player_id', 'size'), minutes_missing=('minutes_played', lambda x: x.isna().mean())).sort_values('rows', ascending=False).head(10)
    roles.minutes_missing.plot.bar(ax=axes[1]); axes[1].set_ylabel('Missing minutes fraction (current position labels)')
    fig.tight_layout(); fig.savefig(REPORT / 'season_league_position_comparison.png', dpi=140); plt.close(fig)
    codes = {name: sha(ROOT / name) for name in ['src/preprocessing/enrichment.py', 'scripts/enriched_pipeline.py',
        'src/models/collected.py', 'src/models/recommend.py', 'src/data/source_rights.py']}
    dataset_version = hashlib.sha256(json.dumps({'inputs': preserved, 'outputs': outputs, 'code': codes}, sort_keys=True).encode()).hexdigest()
    git_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    # Commit the executable pipeline before running for precise MLflow provenance.
    experiments = run_models(dataset_version, git_commit)
    report = {'dataset_version': dataset_version, 'git_commit': git_commit, 'code_sha256': codes,
        'preserved_input_sha256': preserved, 'outputs_sha256': outputs,
        'counts': {name: len(frame) for name, frame in frames.items()},
        'joined_fbref_observations': int(preview.salimt_source_player_id.notna().sum()),
        'base_fbref_rows': len(base), 'unreviewed_join': True, 'model_input_rejections': blocked,
        'minutes_missing_stints': int(stints.minutes_played.isna().sum()),
        'missing_minutes_with_appearances': int(stints.minutes_unknown_for_appearance.sum()),
        'count_inconsistencies': int(stints.count_inconsistency.sum()),
        'outlier_rows_retained': int(stints.performance_outlier.sum()),
        'transfer_exact_duplicates_removed': previous['statistics']['transfer_history']['target_rows'] - len(transfers),
        'ambiguous_zero_fee_events': int(transfers.transfer_fee_zero_ambiguous.sum()),
        'transfer_season_date_conflicts': int(transfers.date_season_inconsistent.sum()),
        'approved_identity_links': 0, 'eligible_historical_budgets': 0,
        'new_model_experiments': experiments,
        'status': 'cleaned_eda_completed_review_only_integration_eligible_FBref_models_rerun',
        'limits': ['No Transfermarkt-derived fields entered fitting or transformation.',
                   'Cross-source joins are proposals, not verified identity labels.',
                   'Reported-date valuation context is not a budget price or historical availability proof.',
                   'Advanced mandatory features absent in uploaded source; 2025/26 partial.',
                   'Model metrics are temporal profile retrieval, not transfer-success validation.']}
    for path in REPORT.rglob('*'):
        # Execution evidence is created after this stage; never freeze mutable
        # test/notebook verification files into the dataset artifact manifest.
        if (path.is_file() and path.suffix != '.xml' and
                path.name not in ['pipeline.json', 'notebook_execution.json', 'verification.json']):
            outputs[str(path.relative_to(ROOT))] = sha(path)
    for name, info in experiments.items(): outputs[info['model_path']] = info['model_sha256']
    (REPORT / 'pipeline.json').write_text(json.dumps(report, indent=2) + '\n')
    for name, digest in preserved.items():
        if sha(ROOT / name) != digest: raise ValueError(f'Previous evidence changed: {name}')
    print(json.dumps({'counts': report['counts'], 'joined': report['joined_fbref_observations'], 'dataset_version': dataset_version}, indent=2))
    return report


if __name__ == '__main__':
    run()
