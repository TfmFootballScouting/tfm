"""Create and execute the new source-enrichment EDA and model notebook."""
import json
import os

os.environ.setdefault('IPYTHONDIR', '/tmp/tfm-ipython')
os.environ.setdefault('JUPYTER_RUNTIME_DIR', '/tmp/tfm-jupyter')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/tfm-matplotlib')
import nbformat as nb
from nbclient import NotebookClient
from src.config import ROOT
from scripts.salimt_history_audit import sha


def run():
    cells = [
        ('md', '# Uploaded histories: cleaning, season-aware enrichment, EDA and model reruns\n\nThis notebook analyses real retained uploads and freshly rerun eligible FBref models. It keeps uploaded Transfermarkt histories separate from learned features. Proposed cross-source identities, retrospective reported prices and source publication dates are not verified. The enrichment is a review dataset, not an authorized model-training dataset.'),
        ('code', '''from pathlib import Path
import os, sys, json
ROOT = Path.cwd()
while not (ROOT/'src/config.py').exists():
    if ROOT == ROOT.parent: raise RuntimeError('Run inside the repository')
    ROOT = ROOT.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
import pandas as pd
import numpy as np
from IPython.display import display, Markdown, Image
from scripts.salimt_history_audit import sha
from src.config import PLAY_STYLES, FEATURE_COLS
from src.data.source_rights import require_model_data_use, SourceUseRestricted
report=json.loads((ROOT/'reports/enrichment/pipeline.json').read_text())
for name, digest in {**report['preserved_input_sha256'], **report['outputs_sha256'], **report['code_sha256']}.items():
    assert sha(ROOT/name)==digest, name
tables={name:pd.read_parquet(ROOT/f'data/processed/real/collected_enrichment_{name}.parquet') for name in report['counts']}
stints=tables['player_club_seasons']; seasons=tables['player_seasons']; events=tables['transfers']
display(pd.Series(report['counts'], name='rows').to_frame())
display(Markdown('Dataset version: `'+report['dataset_version']+'`; source-code commit: `'+report['git_commit']+'`.'))
'''),
        ('md', '## Identity, duplicates and temporal scope\n\nThe source key is `(Transfermarkt player ID, season, competition, club)` for statistics. Club stints are aggregated only within the same player, league and season. Any unknown stint value leaves the corresponding season total unknown; rates require positive observed minutes. Exact transfer duplicates are removed using the ten original fields and their original row numbers are retained as lineage. Loan and loan-return events remain distinct. FBref joins use proposed entity mappings plus exact season and league and preserve every original observation. These mappings still require review. Current position and club/profile fields do not establish historical roles or club membership.'),
        ('code', '''display(pd.DataFrame([{
    'base_FBref_observations': report['base_fbref_rows'],
    'same_season_proposed_enrichment_rows': report['joined_fbref_observations'],
    'identity_links_approved': report['approved_identity_links'],
    'exact_transfer_duplicates_removed': report['transfer_exact_duplicates_removed'],
    'budget_eligible_records': report['eligible_historical_budgets']}]))
assert not seasons.duplicated(['source_player_id','season','league']).any()
assert tables['integration_review'].observation_id.is_unique
assert not tables['reported_price_context'].historical_budget_eligible.any()
display(pd.read_csv(ROOT/'reports/enrichment/season_quality.csv'))
'''),
        ('md', '## Missingness and cleaning decisions\n\nNumeric count/minute parsing preserves raw text. Negative, nonfinite and fractional event counts are flagged and left unknown. Missing minutes are never replaced with zero, appearance count ×90 or global means. Players with no appearances have unknown minutes in this source; the next analysis separates these from missing minutes among players who did appear. Missingness can select the per-90 cohort, so this is not a representative completeness claim.'),
        ('code', '''numeric=['minutes_played','goals','assists','yellow_cards','nb_on_pitch']
display(stints[numeric].isna().agg(['sum','mean']).T)
apps=stints.assign(appearance_band=pd.cut(stints.nb_on_pitch,[-1,0,5,10,20,50]))
display(apps.groupby('appearance_band', observed=True).agg(rows=('player_id','size'),missing_minutes=('minutes_played',lambda x:x.isna().mean())))
display(Markdown(f"Missing stint minutes: **{report['minutes_missing_stints']}**; missing despite reported appearances: **{report['missing_minutes_with_appearances']}**. These rows remain in the descriptive data but cannot supply complete season rates."))
'''),
        ('md', '## Distributions, outliers and correlations\n\nFixed conservative checks flag >6,000 minutes or >60 goals/assists within a league-season stint and internally inconsistent counts. Flagging does not establish an error: rows remain available and no automatic winsorization or global outlier imputation is applied. Descriptive Spearman correlations use pairwise available observations; counts correlate with exposure, and per-90 ratios depend on the minute denominator. G+A is retained for reporting and excluded from model fitting because it repeats goals/assists.'),
        ('code', '''display(seasons[['minutes_played','goals','assists','gls_p90','ast_p90']].describe(percentiles=[.01,.25,.5,.75,.99]).T)
display(stints[[c for c in stints if c.endswith('_invalid')]].sum().rename('invalid').to_frame())
display(pd.Series({'inconsistent_counts':report['count_inconsistencies'],'outlier_rows_retained':report['outlier_rows_retained']}))
display(Image(filename=str(ROOT/'reports/enrichment/quality_distributions_correlations.png')))
'''),
        ('md', '## League, season and position comparisons\n\n2025/26 is a partial source snapshot and cannot be compared with completed seasons as final production. The minute floor is applied after all club stints have been aggregated. Position comparisons below use the uploaded current profile label: they are descriptive metadata groupings, not verified historical tactical roles. Large differences in availability between leagues or seasons should be investigated before league-wide recommendation claims.'),
        ('code', '''display(seasons.groupby(['season','league']).agg(rows=('source_player_id','size'),median_observed_minutes=('minutes_played','median'),median_observed_goals=('goals','median'),eligible_450_minutes=('minutes_eligible','sum')))
display(stints.groupby('position_source').agg(rows=('player_id','size'),missing_minutes=('minutes_played',lambda x:x.isna().mean())).sort_values('rows',ascending=False).head(15))
display(Image(filename=str(ROOT/'reports/enrichment/season_league_position_comparison.png')))
display(pd.read_csv(ROOT/'reports/enrichment/mandatory_feature_coverage.csv'))
display(Markdown('Original six styles remain: '+', '.join(PLAY_STYLES)+'. The uploaded source lacks shots, shots on target, crosses, interceptions, tackles won and foul statistics; it cannot independently support the full style contract.'))
'''),
        ('md', '## Transfers and valuation context\n\nReported positive numerical fees are distinct from market values. A numerical zero does not prove a free transfer, including for loans. Date/season conflicts are flagged rather than rewritten; the source season label is retained. The most recent reported valuation on/before season-end can be associated within this source for auditing only. Unknown publication dates, unverified identities and source-use status prevent this association from becoming a historical scouting budget. No future valuation is backfilled into earlier seasons.'),
        ('code', '''display(events.groupby(['transfer_type','fee_semantics']).size().rename('events').to_frame())
display(pd.Series({'ambiguous_zero_fee_events':report['ambiguous_zero_fee_events'],'date_season_conflicts':report['transfer_season_date_conflicts']}))
prices=tables['reported_price_context']
display(prices.groupby(['season','league']).agg(rows=('source_player_id','size'),reported_values=('reported_value_eur_not_budget','count'),reported_zero_values=('zero_value_ambiguous','sum')))
assert (prices.reported_value_date.dropna()<=prices.loc[prices.reported_value_date.notna(),'report_cutoff']).all()
display(pd.Series(report['model_input_rejections'],name='model_input_rejection').to_frame())
'''),
        ('md', '## Fresh eligible real-data experiments and validation\n\nThree models are refitted from the unchanged eligible FBref cohorts using the existing pipeline, with transformations fitted only on training seasons. New uploaded fields are excluded by the actual source and identity guards. Validation chooses the distance method; holdout remains chronological and frozen. Baselines include goals, goals+assists and seeded random ranking. These metrics measure next-season same-player profile retrieval, not scouting relevance or transfer success. The rerun tests reproducibility; it cannot demonstrate gains from blocked enrichment.'),
        ('code', '''original=json.loads((ROOT/'reports/collected_model_results.json').read_text())
for name, info in report['new_model_experiments'].items():
    scores=pd.read_csv(ROOT/f'reports/enrichment/{name}_retrieval.csv')
    display(Markdown(f"### {name}: validation-selected `{info['selected_method']}`"))
    display(scores[['phase','method','queries','candidate_count','mrr','mrr_ci_low','mrr_ci_high','recall_at_5','recall_at_10','selected_on_validation']])
    np.testing.assert_allclose(info['holdout_mrr'],original['experiments'][name]['holdout_metrics']['mrr'])
    display(Image(filename=str(ROOT/f'reports/enrichment/{name}_evaluation.png')))
display(Markdown('Rerun holdout MRR matches the original experiments. No new-data improvement is claimed.'))
'''),
        ('md', '## PCA, K-means, robustness and recommendations\n\nPCA loadings describe training covariance with arbitrary sign; they are not tactical roles. K-means cluster count is selected on training silhouette and differs conceptually from the six expert style directions. Seed agreement does not validate role accuracy. A hard cluster gate can exclude useful neighbours, so it is compared with unrestricted distance models. Training-row bootstrap shortlist overlap assesses sensitivity; it is not relevance accuracy. Earlier extended validation also found instability around core PC4, so interpretation of that component remains limited.'),
        ('code', '''for name, info in report['new_model_experiments'].items():
    display(Markdown('### '+name))
    display(pd.DataFrame([{'k':info['selected_k'],'first_two_PCA_variance':sum(info['pca_explained_variance'][:2]),'first_four_PCA_variance':sum(info['pca_explained_variance']),'bootstrap_top5_Jaccard':info['robustness_top5_jaccard_mean'],**info['cluster_diagnostics']}]))
    display(pd.read_csv(ROOT/f'reports/enrichment/{name}_pca_loadings.csv'))
    display(pd.read_csv(ROOT/f'reports/enrichment/{name}_cluster_centroids.csv'))
    display(pd.read_csv(ROOT/f'reports/enrichment/{name}_shortlists.csv').groupby('position').agg(recommendations=('entity_id','size'),references=('reference_entity','nunique')))
'''),
        ('md', '## MLflow and completed versus blocked work\n\nCompleted: numeric cleaning with raw preservation; safe season aggregation; exact-event deduplication; source-separated profile and valuation associations; proposed season-aware FBref enrichment; executable EDA; three eligible real-data model refits with baselines, uncertainty and robustness artifacts. Partial: fee semantics, identity validation and historical positional context. Blocked: new source fields entering model fitting until the existing source-use and identity requirements are resolved. No valuation model or transfer-success claim is invented.'),
        ('code', '''for name, info in report['new_model_experiments'].items():
    record=json.loads((ROOT/f'reports/enrichment/mlflow_export/{name}/run.json').read_text())
    assert record['status']=='FINISHED' and record['run_id']==info['mlflow_run_id']
    display(pd.DataFrame([{'model':name,'MLflow_run':record['run_id'],'status':record['status'],'downloaded_artifacts':info['exported_artifacts'],'real_dataset':record['tags']['dataset_kind']}]))
display(Markdown('; '.join(report['limits'])))
'''),
    ]
    doc = nb.v4.new_notebook()
    doc.cells = [nb.v4.new_markdown_cell(text) if kind == 'md' else nb.v4.new_code_cell(text) for kind, text in cells]
    doc.metadata['kernelspec'] = {'display_name': 'TFM Python 3.12', 'language': 'python', 'name': 'tfm-python'}
    path = ROOT / 'notebooks/08_enriched_data_pipeline.ipynb'
    nb.write(doc, path)
    os.environ.setdefault('JUPYTER_PATH', str(ROOT / '.jupyter/share/jupyter'))
    NotebookClient(doc, timeout=240, kernel_name='tfm-python', resources={'metadata': {'path': str(ROOT)}}).execute()
    nb.write(doc, path)
    evidence = {'status': 'executed', 'path': str(path.relative_to(ROOT)), 'sha256': sha(path),
                'code_cells': sum(cell.cell_type == 'code' for cell in doc.cells),
                'error_outputs': sum(output.output_type == 'error' for cell in doc.cells if cell.cell_type == 'code' for output in cell.outputs)}
    (ROOT / 'reports/enrichment/notebook_execution.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(evidence)


if __name__ == '__main__':
    run()
