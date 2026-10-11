"""Verify recorded diagnostics against data, frozen models and logged artifacts."""
import json
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import mlflow
from mlflow.tracking import MlflowClient
import nbformat
import numpy as np
import pandas as pd

from src.config import ROOT
from src.data.provenance import sha256


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run():
    result = json.loads((ROOT/'reports/collected_validation_results.json').read_text())
    base = json.loads((ROOT/'reports/collected_model_results.json').read_text())
    old = json.loads((ROOT/'reports/collected_model_verification.json').read_text())
    for paths in [result['code_hashes'], result['preserved_input_hashes'], old['preserved_application_and_raw_files']]:
        for path, expected in paths.items():
            require(sha256(ROOT/path) == expected, f'Changed preserved file: {path}')
    identity = json.loads((ROOT/'reports/identity_resolution.json').read_text())
    for record in identity['outputs'].values():
        require(sha256(ROOT/record['path']) == record['sha256'], 'Identity output changed')
    mlflow.set_tracking_uri('sqlite:///mlflow.db')
    client = MlflowClient()
    artifacts, runs = [], []
    for name, info in result['experiments'].items():
        for path, expected in info['output_files'].items():
            require(sha256(ROOT/path) == expected, f'Diagnostic output changed: {path}')
        prefix = ROOT/f'reports/experiments/collected_validation_{name}'
        def frame(suffix):
            return pd.read_csv(Path(str(prefix)+'_'+suffix+'.csv'))
        clusters = frame('cluster_bootstrap')
        require(len(clusters) == result['parameters']['person_block_trials'], 'Wrong bootstrap count')
        require(clusters.trial.tolist() == list(range(len(clusters))), 'Duplicate/missing bootstrap trial')
        require(clusters.out_of_bag_people.gt(0).all(), 'No genuine OOB people')
        require(np.isclose(clusters.adjusted_rand_out_of_bag.mean(), info['metrics']['cluster_ari_oob_mean']), 'OOB summary disagrees')
        rankings = frame('ranking_bootstrap')
        require(rankings.top5_jaccard.between(0, 1).all(), 'Invalid shortlist overlap')
        require(np.isclose(rankings[rankings.kind.eq('neighbor')].top5_jaccard.mean(), info['metrics']['neighbor_top5_jaccard_mean']), 'Neighbor summary disagrees')
        require(np.isclose(rankings[rankings.kind.eq('style')].top5_jaccard.mean(), info['metrics']['style_top5_jaccard_mean']), 'Style summary disagrees')
        if name == 'core':
            coverage = frame('style_coverage')
            require(len(coverage) == 6 and coverage.supported.all(), 'Original six core styles unavailable')
            require(rankings[rankings.kind.eq('style')].method.nunique() == 6, 'Six styles not exercised')
        subgroups = frame('position_retrieval')
        details = pd.read_csv(ROOT/f'reports/experiments/collected_{name}_retrieval_queries.csv')
        for row in subgroups.itertuples():
            query = details[details.phase.eq(row.phase) & details.method.eq(row.method) & details.position.eq(row.position)]
            require(len(query) == row.queries, 'Subgroup query count mismatch')
            require(np.isclose(query.reciprocal_rank.mean(), row.mrr), 'Subgroup MRR mismatch')
            baseline = details[details.phase.eq(row.phase) & details.method.eq('goals_assists') & details.position.eq(row.position)]
            paired = query.merge(baseline, on='entity_id', suffixes=('_method', '_baseline'), validate='one_to_one')
            delta = (paired.reciprocal_rank_method-paired.reciprocal_rank_baseline).mean()
            require(np.isclose(delta, row.mrr_delta_goals_assists), 'Subgroup baseline pairing mismatch')
        selected = subgroups[subgroups.phase.eq('holdout') & subgroups.method.eq(info['selected_method'])]
        require(selected.queries.sum() == base['experiments'][name]['holdout_queries'], 'Holdout query count changed')
        require(np.isclose(np.average(selected.mrr, weights=selected.queries), base['experiments'][name]['holdout_metrics']['mrr']), 'Holdout metric changed')
        drift = frame('feature_drift')
        require(drift.js_divergence.between(0, 1).all(), 'Invalid JS divergence')
        angles = frame('pca_subspace_bootstrap')
        require(angles.maximum_angle_degrees.between(0, 90+1e-8).all(), 'Invalid PCA principal angle')
        transitions = frame('cluster_transitions')
        for phase in ['validation', 'holdout']:
            total = transitions[transitions.phase.eq(phase)].returning_players.sum()
            expected = base['experiments'][name][phase+'_queries']
            require(total == expected, 'Frozen-cluster transition universe differs from retrieval universe')
        lineage_path = Path(str(prefix)+'_lineage.json')
        lineage = json.loads(lineage_path.read_text())
        require(lineage['validation_version'] == result['validation_version'], 'Lineage version mismatch')
        require(lineage['git_commit'] == result['git_commit'], 'Lineage Git commit mismatch')
        run = client.get_run(info['mlflow_run_id'])
        require(run.info.status == 'FINISHED', 'Unfinished validation run')
        for key, expected in [('dataset', result['dataset_version']), ('validation_version', result['validation_version']),
                              ('base_model_run_id', info['base_run_id']), ('git_commit', result['git_commit']),
                              ('git_dirty', str(result['git_source_dirty']))]:
            require(run.data.tags[key] == expected, 'MLflow tag mismatch: '+key)
        for key, expected in info['metrics'].items():
            if np.isfinite(expected):
                require(np.isclose(run.data.metrics[key], expected), 'MLflow metric mismatch: '+key)
        expected_artifacts = {f'evaluation/{Path(path).name}': expected for path, expected in info['output_files'].items()}
        expected_artifacts['lineage/'+lineage_path.name] = sha256(lineage_path)
        logged = [artifact for folder in ['evaluation', 'lineage'] for artifact in client.list_artifacts(info['mlflow_run_id'], folder)]
        require(set(artifact.path for artifact in logged) == set(expected_artifacts), 'Logged artifact membership mismatch')
        for artifact in logged:
            require(not artifact.is_dir, 'Unexpected nested artifact')
            downloaded = Path(client.download_artifacts(info['mlflow_run_id'], artifact.path))
            exported = ROOT/'reports/mlflow_export'/artifact.path
            expected = expected_artifacts[artifact.path]
            require(sha256(downloaded) == sha256(exported) == expected, 'Logged/exported checksum mismatch')
            artifacts.append(dict(run_id=info['mlflow_run_id'], path=artifact.path, sha256=expected))
        portable = json.loads((ROOT/f'reports/mlflow_export/collected_validation_{name}_run.json').read_text())
        require(portable['status'] == 'FINISHED' and portable['run_id'] == run.info.run_id, 'Portable run mismatch')
        require(portable['artifact_root'] == '.' and 'artifact_uri' not in portable, 'Machine-local artifact path exposed')
        runs.append(dict(cohort=name, run_id=run.info.run_id, status=run.info.status))
    notebook_evidence = json.loads((ROOT/'reports/collected_validation_notebook_execution.json').read_text())
    notebook_path = ROOT/notebook_evidence['notebook']
    require(sha256(notebook_path) == notebook_evidence['sha256'], 'Executed notebook hash mismatch')
    notebook = nbformat.read(notebook_path, as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == 'code']
    require(all(cell.execution_count is not None for cell in code_cells), 'Notebook has unexecuted code')
    require(not any(output.output_type == 'error' for cell in code_cells for output in cell.outputs), 'Notebook contains errors')
    require(len(code_cells) == notebook_evidence['code_cells'] and notebook_evidence['error_outputs'] == 0, 'Notebook evidence count mismatch')
    suites = ET.parse(ROOT/'reports/collected_validation_tests.xml').getroot()
    counts = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites.iter('testsuite')) for key in ['tests', 'failures', 'errors', 'skipped']}
    require(counts['tests'] > 0 and counts['failures'] == counts['errors'] == counts['skipped'] == 0, 'Incomplete or failing tests')
    evidence = dict(status='passed', checked_at=datetime.now(timezone.utc).isoformat(),
        validation_version=result['validation_version'], analysis_git_commit=result['git_commit'],
        analysis_source_dirty=result['git_source_dirty'], verifier_path='scripts/verify_collected_validation.py',
        verifier_sha256=sha256(ROOT/'scripts/verify_collected_validation.py'),
        preserved_source_model_and_evaluation_files=len(result['preserved_input_hashes']),
        preserved_original_raw_and_application_files=old['preserved_application_and_raw_files'],
        identity_outputs_unchanged=True, verified_finished_runs=runs,
        verified_logged_and_exported_artifacts=artifacts, tests=counts, notebook=notebook_evidence,
        bootstrap_replay='Notebook independently replayed first two core person-block trials in six tables',
        original_holdout_metrics_reconciled_from_position_slices=True,
        historical_transfer_success_evaluated=False, strict_historical_asof_verified=False,
        six_core_styles_exercised=True, current_app_model_replaced=False)
    (ROOT/'reports/collected_validation_verification.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('Verified:', len(runs), 'finished runs;', len(artifacts), 'logged/exported artifacts;', counts)
    return evidence


if __name__ == '__main__':
    run()
