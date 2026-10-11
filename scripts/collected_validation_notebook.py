"""Author and execute notebook 07 in the existing notebooks directory."""
import hashlib
import json
import os

os.environ.setdefault('MPLCONFIGDIR', '/tmp/tfm-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/tfm-cache')
os.environ.setdefault('IPYTHONDIR', '/tmp/tfm-ipython')
os.environ.setdefault('JUPYTER_RUNTIME_DIR', '/tmp/tfm-jupyter')
import nbformat as nb
from nbclient import NotebookClient
from src.config import ROOT

SETUP = '''from pathlib import Path
import os, sys, json
ROOT = Path.cwd()
while not (ROOT/'src/config.py').exists():
    if ROOT == ROOT.parent: raise RuntimeError('Run inside the repository')
    ROOT = ROOT.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from IPython.display import display, Markdown, Image
from src.data.provenance import sha256
result = json.loads((ROOT/'reports/collected_validation_results.json').read_text())
base = json.loads((ROOT/'reports/collected_model_results.json').read_text())
for path, expected in result['preserved_input_hashes'].items():
    assert sha256(ROOT/path) == expected, path
for info in result['experiments'].values():
    for path, expected in info['output_files'].items(): assert sha256(ROOT/path) == expected, path
def frame(name, suffix):
    return pd.read_csv(ROOT/f'reports/experiments/collected_validation_{name}_{suffix}.csv')
def figure(name, suffix):
    display(Image(filename=str(ROOT/f'reports/experiments/collected_validation_{name}_{suffix}.png')))
display(Markdown('All source, baseline-model and diagnostic artifact hashes verified. Validation version: `'+result['validation_version']+'`.'))
'''


def run():
    cells = [
        ('md', '# Extended validation of collected scouting models\n\nThis notebook analyses genuinely executed real FBref archive diagnostics. It extends notebook 06 with person-block refits, PCA direction/subspace stability, frozen-cluster seasonal changes, position-specific retrieval and the six original playing styles. These are **post-hoc diagnostics on already viewed cohorts**. No new held-out confirmation, transfer-success estimate or forecast is claimed. Existing models and raw data are preserved.'),
        ('code', SETUP),
        ('md', '## Design and experimental unit\n\nThirty bootstrap draws sample source player identities with replacement. Each draw retains **all development-season observations** of each sampled person; repeated draws act as weights on observed records. Median imputation, standard scaling, PCA and K-means are refitted on those development rows. K and PCA width remain fixed at the previously selected values. No validation/holdout row is fitted. Player-level sampling accounts for repeated seasons within training, while still treating players as independent; club/competition dependencies are not modelled. Out-of-bag (OOB) players were absent from the bootstrap fitting sample. ARI is label-permutation invariant, and evaluates assignment agreement with the original development model, not correctness.'),
        ('code', '''display(pd.DataFrame([dict(cohort=name, development_rows=info['train_rows'], development_people=info['train_people'], seasons=', '.join(info['train_seasons']), method=info['selected_method'], base_run_id=info['base_run_id']) for name,info in result['experiments'].items()]))
display(pd.DataFrame([result['parameters']]))
'''),
        ('md', '## K-means: population sensitivity beyond initialization\n\nAll refits predict clusters on the same original training reference set, with OOB agreement reported separately. The CSV records OOB sample sizes and explicitly marks insufficient cluster diversity. Centroids are matched by minimum total distance after converting them to the original standardized feature space. Quantiles describe the conditional resampling distribution; they are not population accuracy confidence intervals.'),
        ('code', '''for name in result['experiments']:
    clusters=frame(name,'cluster_bootstrap')
    display(Markdown('### '+name))
    display(clusters[['adjusted_rand_reference','adjusted_rand_out_of_bag','matched_centroid_distance_mean','out_of_bag_people']].describe(percentiles=[.05,.5,.95]))
    display(clusters.out_of_bag_status.value_counts().to_frame('trials'))
    figure(name,'bootstrap')
    display(Markdown(f"OOB ARI averaged {clusters.adjusted_rand_out_of_bag.mean():.3f}, with a minimum of {clusters.adjusted_rand_out_of_bag.min():.3f}. This measures assignment sensitivity to sampled players; it does not validate tactical labels. The two original clusters remain broad attacking-output groupings."))
'''),
        ('md', '## PCA: loadings, subspaces and variance\n\nComponent signs and ordering are arbitrary. Bootstrap score directions are converted to the original standardized coordinates using the ratio of original to bootstrap feature scales, normalized and matched by maximum absolute loading cosine. A rotation among close eigenvectors can change individual loadings without changing their joint space, so top-two and top-four principal angles are reported separately (zero means the same subspace). Explained variance belongs to each bootstrap fit\'s standardized covariance and is not directly a share of a fixed original covariance. These checks complement notebook 06\'s observed retrieval loss after PCA compression.'),
        ('code', '''for name in result['experiments']:
    display(Markdown('### '+name))
    display(frame(name,'pca_loading_bootstrap').groupby('component').absolute_loading_cosine.agg(['mean','min','max']))
    display(frame(name,'pca_subspace_bootstrap').groupby('dimensions').maximum_angle_degrees.agg(['mean','min','max']))
    display(frame(name,'pca_variance_bootstrap').groupby('component').cumulative_variance.agg(['mean','min','max']))
    angles=frame(name,'pca_subspace_bootstrap')
    display(Markdown(f"The largest top-four principal angle averaged {angles[angles.dimensions.eq(4)].maximum_angle_degrees.mean():.2f}°. Direction stability alone cannot establish that compressed features retain the information needed for recommendations; the temporal retrieval comparison remains the relevant proxy test."))
'''),
        ('md', '## Independent replay of the first two real bootstrap draws\n\nThe following cell refits the core development bootstrap twice with the saved seed and verifies its numeric outputs against the first two recorded trials. It uses observed development data from the frozen model and does not produce new experiment runs.'),
        ('code', '''from src.models.recommend import PlayerRecommender
from src.models.validation import resampling_validation
rec=PlayerRecommender.load(ROOT/result['experiments']['core']['base_model_path'])
replayed=resampling_validation(rec,trials=2,seed=result['parameters']['seed'])
for suffix in ['cluster_bootstrap','pca_loading_bootstrap','pca_subspace_bootstrap','pca_variance_bootstrap','ranking_bootstrap']:
    expected=frame('core',suffix); expected=expected[expected.trial.lt(2)].reset_index(drop=True)
    actual=replayed[suffix].reset_index(drop=True)
    pd.testing.assert_frame_equal(actual,expected,check_dtype=False,check_exact=False,rtol=1e-9,atol=1e-10)
display(Markdown('Two whole-player real-data refits replayed successfully for all five diagnostic tables.'))
'''),
        ('md', '## Retrieval by position and evaluation season\n\nDF/MF/FW are the **previous-season query** positions; targets remain in the complete next-season candidate pool. Each method is compared with goals-and-assists on exactly the same identities, matched by source ID rather than row order. Five hundred paired query bootstraps give conditional subgroup intervals. They do not adjust for multiple exploratory slices or prove relevance for a club. A target disappearing under a hard cluster gate receives zero credit. Returning players above the minutes threshold exclude exits, injuries and other nonreturners.'),
        ('code', '''for name,info in result['experiments'].items():
    metrics=frame(name,'position_retrieval')
    selected=metrics[metrics.method.eq(info['selected_method'])]
    display(Markdown('### '+name))
    display(selected[['evaluation_season','position','queries','mrr','recall_at_5','mrr_delta_goals_assists','delta_ci_low','delta_ci_high']])
    # Independently reconcile subgroup means with the original complete holdout.
    hold=selected[selected.phase.eq('holdout')]
    assert int(hold.queries.sum())==base['experiments'][name]['holdout_queries']
    assert np.isclose(np.average(hold.mrr,weights=hold.queries),base['experiments'][name]['holdout_metrics']['mrr'])
    worst=hold.sort_values('mrr').iloc[0]
    display(Markdown(f"Lowest holdout identity/profile retrieval here: {worst.position}, MRR {worst.mrr:.3f} across {int(worst.queries)} queries. Position differences describe these archive cohorts and are not scouting accuracy estimates."))
figure('core','positions')
'''),
        ('md', '## Temporal drift and frozen-cluster transitions\n\nOriginal development transformations and centres are frozen for every season. Feature drift uses observed rates only, reports missingness separately and uses training quantile histogram bins with infinite outer tails. Jensen–Shannon divergence (base 2) is bounded between 0 and 1; no arbitrary alert threshold or independence-based significance test is applied. Mean shifts use the original training standard deviation. Silhouette on frozen labels is descriptive; it does not reselect K. Transition matrices include only returning source identities and use their prior position, so their changes can reflect roles, exposure or roster selection rather than a causal tactical change.'),
        ('code', '''for name in result['experiments']:
    display(Markdown('### '+name))
    display(frame(name,'temporal_cluster_quality'))
    changes=frame(name,'cluster_transitions')
    changes['changed']=changes.cluster_previous.ne(changes.cluster_future)*changes.returning_players
    summary=changes.groupby(['query_season','evaluation_season']).agg(returners=('returning_players','sum'),changed=('changed','sum'))
    summary['changed_fraction']=summary.changed/summary.returners
    display(summary)
    drift=frame(name,'feature_drift').copy()
    display(drift.sort_values('js_divergence',ascending=False).head(6))
    maximum=drift.sort_values('js_divergence',ascending=False).iloc[0]
    display(Markdown(f"Largest binned distribution difference: {maximum.feature} in {maximum.season}, JS divergence {maximum.js_divergence:.4f}, mean change {maximum.mean_shift_training_sd:+.3f} training SD. Archive/category comparability and changed player exposure must be considered before attributing this to football evolution."))
figure('core','drift')
'''),
        ('md', '## All six original expert-defined playing styles\n\nPossession, high pressing, vertical play, counterattack, defensive solidity and wing play remain separate scoring directions. They are not K-means clusters. The core model supports all six under the existing measured-weight rule (at least 60% absolute configured weight). Offensive tracks report limited support instead of assigning missing defensive features zero. Rankings below use a fixed last-development-season gallery and broad positions; they have no dated budget constraints. Resampling checks preprocessing sensitivity with fixed expert weights, not whether the weights represent real pressing, passing progression or transitions. Pairwise shortlist overlap can reveal redundant directions.'),
        ('code', '''for name in result['experiments']:
    display(Markdown('### '+name)); display(frame(name,'style_coverage'))
core=frame('core','style_coverage'); assert len(core)==6 and core.supported.all()
stability=frame('core','ranking_bootstrap').query('kind == "style"')
display(stability.groupby(['method','position']).top5_jaccard.agg(['mean','min','max']))
display(frame('core','style_shortlists'))
display(frame('core','style_overlap').sort_values('top5_jaccard',ascending=False).head(10))
figure('core','styles')
display(Markdown('All six core style rankings were exercised on real historical players. High overlap or bootstrap stability alone does not validate the style names or establish club fit.'))
'''),
        ('md', '## MLflow lineage and remaining validation\n\nValidation runs are separate from the original model-comparison runs and synthetic demonstrations. Each refers to its frozen model run and checksum, dataset/version, code hashes, Git commit and post-hoc design. Evaluation tables, plots and lineage are exported from finished logged artifacts using relative paths. Actual historical transfers, licensed dated budgets, independently reviewed identity labels and genuine scouting decisions are still required for external validation. No output here substitutes for those labels.'),
        ('code', '''import mlflow
from mlflow.tracking import MlflowClient
mlflow.set_tracking_uri('sqlite:///mlflow.db')
client=MlflowClient()
for name,info in result['experiments'].items():
    record=json.loads((ROOT/f'reports/mlflow_export/collected_validation_{name}_run.json').read_text())
    logged=client.get_run(info['mlflow_run_id'])
    assert record['status']==logged.info.status=='FINISHED'
    assert logged.data.tags['base_model_run_id']==info['base_run_id']
    assert logged.data.tags['validation_version']==result['validation_version']
    display(pd.DataFrame([dict(cohort=name,run_id=logged.info.run_id,base_run_id=info['base_run_id'],status=logged.info.status)]))
display(Markdown('Remaining limits: '+ '; '.join(result['limitations'])))
'''),
    ]
    document = nb.v4.new_notebook()
    document.cells = [nb.v4.new_markdown_cell(text) if kind == 'md' else nb.v4.new_code_cell(text) for kind,text in cells]
    document.metadata['kernelspec'] = dict(display_name='TFM Python 3.12', language='python', name='tfm-python')
    path = ROOT/'notebooks/07_collected_extended_validation.ipynb'
    nb.write(document, path)
    os.environ.setdefault('JUPYTER_PATH', str(ROOT/'.jupyter/share/jupyter'))
    NotebookClient(document, timeout=180, kernel_name='tfm-python', resources={'metadata': {'path': str(ROOT)}}).execute()
    nb.write(document, path)
    evidence = dict(notebook=path.relative_to(ROOT).as_posix(), status='executed',
        code_cells=sum(c.cell_type == 'code' for c in document.cells),
        error_outputs=sum(o.output_type == 'error' for c in document.cells if c.cell_type == 'code' for o in c.outputs),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (ROOT/'reports/collected_validation_notebook_execution.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(evidence)


if __name__ == '__main__':
    run()
