"""Author and execute only the new collected-data analysis notebook."""
import json
import hashlib
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
os.environ.setdefault('MPLCONFIGDIR','/tmp/tfm-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME','/tmp/tfm-cache')
import pandas as pd
import numpy as np
from IPython.display import display, Markdown, Image
from src.data.provenance import sha256
from src.models.collected import EXPERIMENTS, cohorts, evaluate_pair
from src.models.recommend import PlayerRecommender
from scripts.collected_models import verified_inputs
manifest, identity, tables = verified_inputs()
result = json.loads((ROOT/'reports/collected_model_results.json').read_text())
for name, info in result['experiments'].items():
    assert sha256(ROOT/info['model_path']) == info['model_sha256']
    for path, digest in info['output_files'].items(): assert sha256(ROOT/path) == digest
display(Markdown('**Real collected FBref observations only.** Dataset version: `'+result['dataset_version']+'`. Matching method accepted; individual cross-source links remain unverified and are not learned features.'))
'''


def run():
    cells = [
        ('md', '# Collected-data recommendation models and temporal profile analysis\n\nResearch question: which measured profile representation best retrieves a returning player in the next season? This is an identity/profile-persistence proxy, not a test of transfer success, forecast production or club-fit relevance. Future candidate profiles are used solely for evaluation; they are unavailable at real scouting time.'),
        ('code', SETUP),
        ('md', '## Data and chronological experiment design\n\nOffensive development: 2020/21–2022/23; validation 2023/24; holdout 2024/25. Full-core development: 2020/21–2021/22; validation 2022/23; holdout 2023/24. Different holdout seasons prevent a direct comparison of the two main tracks. Partial 2025/26 and the sparse 2024/25 core snapshot are excluded. Aggregation precedes the 450-minute floor. Goalkeepers are excluded. Repeated player-seasons in development deliberately contribute observed exposure-year profiles; each evaluation season has one row per identity.'),
        ('code', '''for name,spec in EXPERIMENTS.items():
    parts = cohorts(tables[spec['table']],spec['split'])
    display(Markdown('### '+name))
    display(pd.DataFrame([{'split':k,'rows':len(v),'people':v.entity_id.nunique(),'seasons':', '.join(sorted(v.season.unique()))} for k,v in parts.items()]))
    display(parts['train'][spec['features']].isna().sum().rename('training_missing').to_frame())
'''),
        ('md', '## Training transformations and model selection\n\nMedians, standardization, PCA and K-means are fitted only on development observations. G+A is omitted because it is algebraically redundant. xAG remains its own feature, never xA. K is selected by training silhouette across 2–8 clusters, with a fixed seed. Profile method selection uses validation MRR only. The original training transformations remain frozen for holdout, including validation-season queries. Scores compare cosine/Euclidean distances, two/four PCA components, a hard cluster gate, goals-only, goals-and-assists and a seeded random baseline. Uniform tie handling gives tied targets expected reciprocal rank/hit probability, avoiding row-order bias.'),
        ('code', '''for name, info in result['experiments'].items():
    display(Markdown(f"**{name}:** validation-selected `{info['selected_method']}`; k={info['selected_k']}; features: "+', '.join(info['feature_cols'])))
    rec = PlayerRecommender.load(ROOT/info['model_path'])
    assert rec.neighbor_method == info['selected_method']
    spec = EXPERIMENTS[name]; parts = cohorts(tables[spec['table']], spec['split'])
    past = parts['train'][parts['train'].season == parts['train'].season.max()]
    before = rec.artifacts.scaler.mean_.copy()
    replay, _ = evaluate_pair(rec,past,parts['validation'],'validation')
    recorded = pd.read_csv(ROOT/f'reports/experiments/collected_{name}_retrieval.csv').query("phase == 'validation'")
    np.testing.assert_allclose(replay.set_index('method').mrr, recorded.set_index('method').mrr)
    np.testing.assert_equal(before, rec.artifacts.scaler.mean_)
print('All validation experiments replayed with frozen model transformations.')
'''),
        ('md', '## Baselines and uncertainty\n\nMRR, Recall@5/10 and NDCG@10 use one same-person target per returning-player query. Players absent from the next eligible cohort are reported by the returning-player fraction rather than assigned invented future profiles. The confidence intervals use 200 paired player-query bootstrap replicates and are conditional on these archive cohorts; they do not remove survival/selection bias.'),
        ('code', '''for name in result['experiments']:
    scores=pd.read_csv(ROOT/f'reports/experiments/collected_{name}_retrieval.csv')
    display(Markdown('### '+name));display(scores[['phase','method','queries','candidate_count','mrr','mrr_ci_low','mrr_ci_high','recall_at_5','target_available_fraction','selected_on_validation']])
    display(Image(filename=str(ROOT/f'reports/experiments/collected_{name}_retrieval.png')))
'''),
        ('md', '## PCA interpretation\n\nThe offensive PC1 loads strongly on goals, shots, shots on target and xG, while PC2 emphasizes assists/xAG. The core PC1 contrasts attacking rates with interceptions/tackles; PC2 mixes crossing, tackling, fouls and fouls drawn. These covariance axes are descriptive. Their signs are arbitrary and they are not labelled tactical roles. High explained variance alone does not justify using fewer dimensions for nearest-player recommendations.'),
        ('code', '''for name,info in result['experiments'].items():
    display(Markdown(f"**{name}:** first two components explain {sum(info['pca_explained_variance'][:2]):.1%}; first four explain {sum(info['pca_explained_variance']):.1%}."))
    display(pd.read_csv(ROOT/f'reports/experiments/collected_{name}_pca_loadings.csv'))
    display(Image(filename=str(ROOT/f'reports/experiments/collected_{name}_pca_loadings.png')))
display(Markdown('Both main tracks selected full standardized Euclidean profiles on validation. PCA alternatives reduced holdout retrieval MRR. Compression is retained for analysis, rather than imposed on recommendation distances.'))
'''),
        ('md', '## K-means interpretation and robustness\n\nTwo clusters are selected in the main tracks. They mainly separate stronger attacking output from the remaining profiles; position composition supports that description. They do not establish six tactical roles. Low season association in development does not prove absence of future drift. Seed agreement describes optimization stability, not scouting validity. The hard cluster gate loses correct same-player targets when their next-season cluster changes, so it is not selected as a shortlist filter.'),
        ('code', '''for name,info in result['experiments'].items():
    display(Markdown('### '+name));display(pd.read_csv(ROOT/f'reports/experiments/collected_{name}_cluster_search.csv'))
    display(pd.read_csv(ROOT/f'reports/experiments/collected_{name}_cluster_positions.csv'))
    display(pd.DataFrame([info['cluster_analysis']]))
    display(Image(filename=str(ROOT/f'reports/experiments/collected_{name}_cluster_profiles.png')))
    robustness=pd.read_csv(ROOT/f'reports/experiments/collected_{name}_robustness.csv')
    display(robustness.groupby(['position','method']).top5_jaccard.agg(['mean','min','max']))
'''),
        ('md', '## Same-cohort feature ablation\n\nThe additional `attack_on_core` experiment uses the same development, validation, holdout players and seasons as the core experiment, but only six attacking features. This is a post-hoc diagnostic added after the initial trials, not independent confirmatory validation. The Euclidean comparison holds the retrieval method constant.'),
        ('code', "display(pd.read_csv(ROOT/'reports/experiments/collected_feature_ablation.csv'))"),
        ('md', '## Qualitative scouting alternatives\n\nReference players are reproducibly chosen as the highest-minute player in each position in the last development season. Lists require the same broad position, age ≤27, a single known club, another club and a different identity. They are historical descriptive alternatives; market-value budgets and actual-transfer success remain unevaluated. Broad DF/MF/FW labels lack detailed roles. Offensive-only defender similarity is especially limited by the missing defensive dimensions.'),
        ('code', '''for name in ['offensive','core']:
    display(Markdown('### '+name))
    display(pd.read_csv(ROOT/f'reports/experiments/collected_{name}_shortlists.csv'))
'''),
        ('md', '## Accepted matching method and source agreement\n\nThe proposed identity mapping is retained for exploration. Comparing source goals and xG is an audit of joins and provider coverage, not an identity accuracy test. Different exposure periods or provider definitions can explain disagreement. No Transfermarkt values or unreviewed cross-source fields enter the trained models. No cross-provider xG values are summed.'),
        ('code', "display(pd.read_csv(ROOT/'reports/experiments/collected_source_agreement.csv'))"),
        ('md', '## MLflow and reproducibility\n\nCollected-data runs use their own experiment, distinct from the legacy and synthetic demonstrations. Runs record owner/project/dataset/environment tags, dataset version, code hashes, Git commit, parameters, comparison metrics, model files and evaluation figures. The portable exports are downloaded from genuinely logged MLflow artifacts. The existing Streamlit model remains unchanged pending a separate application integration step.'),
        ('code', '''for name,info in result['experiments'].items():
    record=json.loads((ROOT/f'reports/mlflow_export/collected_{name}_run.json').read_text())
    assert record['status']=='FINISHED' and record['run_id']==info['mlflow_run_id']
    display(pd.DataFrame([{'cohort':name,'run_id':record['run_id'],'status':record['status'],'dataset_version':record['tags']['dataset'],'model':info['model_path']}]))
display(Markdown('Remaining limits: '+ '; '.join(result['limitations'])))
'''),
    ]
    document = nb.v4.new_notebook()
    document.cells = [nb.v4.new_markdown_cell(text) if kind == 'md' else nb.v4.new_code_cell(text) for kind,text in cells]
    document.metadata['kernelspec'] = dict(display_name='TFM Python 3.12', language='python', name='tfm-python')
    path = ROOT/'notebooks/06_collected_model_analysis.ipynb'
    nb.write(document, path)
    os.environ.setdefault('JUPYTER_PATH', str(ROOT/'.jupyter/share/jupyter'))
    NotebookClient(document, timeout=180, kernel_name='tfm-python', resources={'metadata':{'path':str(ROOT)}}).execute()
    nb.write(document, path)
    evidence = dict(notebook=path.relative_to(ROOT).as_posix(), status='executed',
                    code_cells=sum(c.cell_type=='code' for c in document.cells),
                    error_outputs=sum(o.output_type=='error' for c in document.cells if c.cell_type=='code' for o in c.outputs),
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (ROOT/'reports/collected_model_notebook_execution.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(evidence)


if __name__ == '__main__':
    run()
