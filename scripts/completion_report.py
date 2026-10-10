"""Render the submission report from actual verification and run evidence."""
import json
import pandas as pd
from src.config import ROOT,MODELS_DIR


def run():
    v=json.loads((ROOT/'reports/verification.json').read_text())
    m=json.loads((MODELS_DIR/'metrics.json').read_text())
    robust=pd.read_csv(ROOT/'reports/experiments/robustness.csv')
    summary=robust[robust.perturbation=='training_bootstrap'].groupby('style').top10_jaccard.agg(['mean','min','max'])
    values='\n'.join(f'- {key}: {value:.6f}' for key,value in m['metrics'].items())
    boot='\n'.join(f'- {style}: mean top-10 Jaccard {r["mean"]:.3f}, range {r["min"]:.3f}–{r["max"]:.3f} over 30 training bootstraps.' for style,r in summary.iterrows())
    text=f'''# Completion report — first reproducible submission

Checked at {v['checked_at']} (UTC). Work branch: `improve/reproducible-scouting` in `valen28030/tfm_futbol`. Existing architecture retained; main unchanged. No changes have been pushed. The originally selected `TfmFootballScouting/tfm` checkout is still empty and was not overwritten. Breakout is retained as an unchanged reference.

## Completion by requirement

| Phase | Status | Genuine result and remaining prerequisite |
|---|---|---|
| 1. Data acquisition | **Partial / blocked** | Breakout reviewed. Original raw CSV/Parquet preserved. Current Transfermarkt first-page sample: 50 values (25/league), two profiles, raw history pages. FBref policy endpoint HTTP 403; Understat robots disallows all crawling; no Segunda coverage on Understat. Six-season football stats, full TM rosters/history/fees and historical values not acquired. |
| 2. Integration/preprocessing | **Implemented, integration partial** | Source-ID/club/season one-to-one joins; immutable hashes; missing≠zero; duplicate conflicts stop; transfer aggregates; stable observation IDs; outlier flags; training-only medians/scaling; cutoff and dated EUR budget guards. Conservative name+DOB/review proposals implemented/tested. No verified cross-source mapping or price merge available; legacy IDs are unverified local keys. |
| 3. EDA | **Executed, limited coverage** | Executed notebook with source mix, missingness, distributions, outliers, correlations and position comparisons; single-league/single-season comparisons explicitly limited. Separate current TM sample analysis. |
| 4. ML | **Exploratory only; final validation blocked** | Cosine/KNN/PCA/K-means preserved and repaired. Linear weighted, minutes and G+A baseline agreements; seed ARI, silhouette, weight perturbations and observed-row bootstraps; PCA loadings and cluster profiles interpreted. Legacy dataset provenance unverified; no final recommendation-quality claim. Temporal profile-retrieval benchmark implemented/tested on unit fixtures, unrun on multi-season real data. |
| 5. Real-world validation | **Partial / blocked** | Position/style/season/excluded-club scenarios executed; dated budget scenario refuses unknown historical values. No actual club mandates, eligible historical universe, verified transfer labels or fees: no retrospective transfer precision/recall/NDCG results. |
| 6. Process mining | **Instrumentation implemented / discovery blocked** | Case/activity/UTC timestamp/actor/attributes event log and directly-follows discovery implemented/tested. App logs actual search/review actions. No genuine human scouting sessions or club decisions; no simulated events used as evidence. |
| 7. MLflow | **Executed for exploration** | Separate legacy-exploratory, real and synthetic experiment routes. Actual run tags include owner/project/dataset hash/environment/Git commit+dirty state. Logged model, plots, evaluation CSVs, lineage and portable exported artifact paths. Local MLflow runtime resolves machine-local absolute URIs; the export omits those URIs and normalizes the source-name tag. Export downloaded from the recorded run. No synthetic demo used for submission. |
| 8. Project quality | **Completed locally; remote CI unverified** | Python 3.12 direct pins + resolved lock, reproducible setup, portable metadata, {v['tests']['tests']} tests, Streamlit functional AppTest and live health, MLflow live API, four executed notebooks and updated TFM docs. GitHub Actions added but not executed remotely. Cloud snapshot publication/fresh-task restoration remain user/product actions, not verified here. |

## Data evidence and safeguards

- Legacy raw input: 609 FBref-labelled La Liga 2023/24 rows + 840 synthetic rows. The originals are unchanged.
- Retained exploratory observations: {m['dataset']['rows']}. Every synthetic row is excluded. Suspect ancillary statistics from index-based joins are discarded, and no invented `budget_est` is used.
- Available fitted features: {', '.join(m['feature_cols'])}. Broad tactical styles are disabled below 60% measured absolute weight; only goals/assists profiles are offered.
- Original source HTML/retrieval dates are missing for legacy statistics. `real_legacy_unverified` is a provenance status, **not a claim of final verified real data**. Final training refuses this dataset unless explicitly exploratory.
- Current TM pages are not historical season data despite the requested season URL. Valuation effective dates remain unknown and no backdated price is inferred. Market values are not transfer fees.
- {v['raw_snapshot_checksums']['records_verified']} provenance records / {v['raw_snapshot_checksums']['unique_snapshots']} distinct raw response hashes verified against stored content. See `data/raw/provenance.jsonl`, `reports/source_coverage.csv`, `reports/transfermarkt_sample_access.csv`, `docs/SOURCE_ACCESS.md`.

## Actually executed exploratory results

Run ID: `{m['run_id']}`. Recorded source commit: `{m['git_commit']}`; recorded dirty state: `{m['git_dirty']}`. Dataset SHA-256: `{m['dataset']['dataset_sha256']}`. Full precision and tags are in `models/real/metrics.json` and `reports/mlflow_export/run.json`.

{values}

These are descriptive diagnostics, not predictive accuracy or successful transfer selection. Two PCA components on two features explain 100% by construction. K-means clusters describe attack-production levels, not discovered tactical roles. Baseline Jaccard agreements are in `reports/experiments/baselines.csv`.

{boot}

Single-feature positive weight perturbations preserve rankings by construction; the bootstrap refits preprocessing using sampled **observed** rows on an unchanged candidate set. These uncertainties remain conditional on the limited legacy dataset. No relevance labels, confidence-calibrated signing predictions or validated historical budget recommendations exist.

## Verification outcomes

- Tests: {v['tests']['tests']} executed, {v['tests']['failures']} failures, {v['tests']['errors']} errors, {v['tests']['skipped']} skipped; exit status {v['tests']['exit_code']}. Unit fixtures are artificial and isolated from experiments.
- Four notebooks executed, 17 code cells total. Some analyses intentionally display blocked prerequisites; notebook completion is not proof those analyses ran.
- Dependency consistency: {v['pip_check']}; setup script exercised repeatedly with locked installation and tests.
- Streamlit live health: {v['streamlit_service']}; AppTest exercised real exploratory rendering, FW filtering, similar players and temporary event instrumentation.
- MLflow API: {v['mlflow_service']}; artifact export validated against a FINISHED actual run.
- Default real pipeline without collected statistics: {v['default_pipeline_without_collected_stats']}; raw/processed data unchanged by the failed attempt.
- Final training on unverified legacy data: {v['final_training_with_unverified_legacy']}.
- Genuine process analysis: {v['genuine_process_log']}.
- No final multi-season recommendation experiment, historical transfer validation, organization process-mining result, remote CI run or fresh cloud restoration is claimed.

## Deliverable locations

1. Updated existing code: `src/`, `scripts/`, tests and requirements on the work branch.
2. Raw/source data: original `data/raw/players_raw.*`, immutable `data/raw/sources/`, current normalized `data/external/transfermarkt/`; precise source blockers in `docs/SOURCE_ACCESS.md`.
3. Executed notebooks: `notebooks/01_data_quality_eda.ipynb` through `04_process_mining.ipynb`.
4. Preliminary results/model/artifacts: `reports/experiments/`, `models/real/`, `reports/mlflow_export/`; runtime SQLite/MLflow stores are retained locally and ignored by Git.
5. Dictionary: `docs/DATA_DICTIONARY.md`.
6. TFM account: `docs/memoria_resumen.md`, updated use-case/process/evidence documents, `README.md`.
7. This completion report and machine-readable `reports/verification.json` / `reports/notebook_execution.json`.

## What remains to complete the final TFM

Obtain provider permission or authorized exports for the blocked football-statistics seasons and leagues, with stable player IDs and raw provenance. Obtain actual dated valuation records, historical roster membership and transfer/fee records (including explicit unknowns), then review identity mappings. Run the default real pipeline, temporal evaluation and labelled historical signing scenarios. Capture consented genuine scouting sessions before process discovery. No credential is presently proven necessary; do not provide secret values in chat.

Cloud setup/start instructions and repository membership are saved separately in the environment draft. Review/save the draft and publish through environment settings to retain the prepared snapshot. Saving configuration does not prove publication or restoration in a new task.
'''
    (ROOT/'docs/COMPLETION_REPORT.md').write_text(text)


if __name__=='__main__':
    run()
