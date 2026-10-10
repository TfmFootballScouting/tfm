# Completion report — first reproducible submission

Checked at 2026-10-10T15:23:42.646132+00:00 (UTC). Work branch: `improve/reproducible-scouting` in `valen28030/tfm_futbol`. Existing architecture retained; main unchanged. No changes have been pushed. The originally selected `TfmFootballScouting/tfm` checkout is still empty and was not overwritten. Breakout is retained as an unchanged reference.

## Completion by requirement

| Phase | Status | Genuine result and remaining prerequisite |
|---|---|---|
| 1. Data acquisition | **Partial / blocked** | Breakout reviewed. Original raw CSV/Parquet preserved. Current Transfermarkt first-page sample: 50 values (25/league), two profiles, raw history pages. FBref policy endpoint HTTP 403; Understat robots disallows all crawling; no Segunda coverage on Understat. Six-season football stats, full TM rosters/history/fees and historical values not acquired. |
| 2. Integration/preprocessing | **Implemented, integration partial** | Source-ID/club/season one-to-one joins; immutable hashes; missing≠zero; duplicate conflicts stop; transfer aggregates; stable observation IDs; outlier flags; training-only medians/scaling; cutoff and dated EUR budget guards. Conservative name+DOB/review proposals implemented/tested. No verified cross-source mapping or price merge available; legacy IDs are unverified local keys. |
| 3. EDA | **Executed, limited coverage** | Executed notebook with source mix, missingness, distributions, outliers, correlations and position comparisons; single-league/single-season comparisons explicitly limited. Separate current TM sample analysis. |
| 4. ML | **Exploratory only; final validation blocked** | Cosine/KNN/PCA/K-means preserved and repaired. Linear weighted, minutes and G+A baseline agreements; seed ARI, silhouette, weight perturbations and observed-row bootstraps; PCA loadings and cluster profiles interpreted. Legacy dataset provenance unverified; no final recommendation-quality claim. Temporal profile-retrieval benchmark implemented/tested on unit fixtures, unrun on multi-season real data. |
| 5. Real-world validation | **Partial / blocked** | Position/style/season/excluded-club scenarios executed; dated budget scenario refuses unknown historical values. No actual club mandates, eligible historical universe, verified transfer labels or fees: no retrospective transfer precision/recall/NDCG results. |
| 6. Process mining | **Instrumentation implemented / discovery blocked** | Case/activity/UTC timestamp/actor/attributes event log and directly-follows discovery implemented/tested. App logs actual search/review actions. No genuine human scouting sessions or club decisions; no simulated events used as evidence. |
| 7. MLflow | **Executed for exploration** | Separate legacy-exploratory, real and synthetic experiment routes. Actual run tags include owner/project/dataset hash/environment/Git commit+dirty state. Logged model, plots, evaluation CSVs, lineage and relative artifact paths. Portable export downloaded from the recorded run. No synthetic demo used for submission. |
| 8. Project quality | **Completed locally; remote CI unverified** | Python 3.12 direct pins + resolved lock, reproducible setup, portable metadata, 24 tests, Streamlit functional AppTest and live health, MLflow live API, four executed notebooks and updated TFM docs. GitHub Actions added but not executed remotely. Cloud snapshot publication/fresh-task restoration remain user/product actions, not verified here. |

## Data evidence and safeguards

- Legacy raw input: 609 FBref-labelled La Liga 2023/24 rows + 840 synthetic rows. The originals are unchanged.
- Retained exploratory observations: 420. Every synthetic row is excluded. Suspect ancillary statistics from index-based joins are discarded, and no invented `budget_est` is used.
- Available fitted features: gls_p90, ast_p90. Broad tactical styles are disabled below 60% measured absolute weight; only goals/assists profiles are offered.
- Original source HTML/retrieval dates are missing for legacy statistics. `real_legacy_unverified` is a provenance status, **not a claim of final verified real data**. Final training refuses this dataset unless explicitly exploratory.
- Current TM pages are not historical season data despite the requested season URL. Valuation effective dates remain unknown and no backdated price is inferred. Market values are not transfer fees.
- 146 provenance records / 103 distinct raw response hashes verified against stored content. See `data/raw/provenance.jsonl`, `reports/source_coverage.csv`, `reports/transfermarkt_sample_access.csv`, `docs/SOURCE_ACCESS.md`.

## Actually executed exploratory results

Run ID: `fc22dbab233241de97abf5caa3ba4cb8`. Recorded source commit: `2cf3385cd8f3ddd41cbc608a5942564cba03100c`; recorded dirty state: `True`. Dataset SHA-256: `05e6266ab5f45651ff69c763413d3fbb196de6fd061d44bb48899b09b305fc6c`. Full precision and tags are in `models/real/metrics.json` and `reports/mlflow_export/run.json`.

- silhouette_kmeans: 0.438766
- pca_explained_variance_sum: 1.000000
- mean_top10_jaccard_overlap: 0.000000
- cluster_seed_ari_mean: 0.905694

These are descriptive diagnostics, not predictive accuracy or successful transfer selection. Two PCA components on two features explain 100% by construction. K-means clusters describe attack-production levels, not discovered tactical roles. Baseline Jaccard agreements are in `reports/experiments/baselines.csv`.

- creator: mean top-10 Jaccard 0.668, range 0.333–1.000 over 30 training bootstraps.
- finisher: mean top-10 Jaccard 0.656, range 0.333–1.000 over 30 training bootstraps.

Single-feature positive weight perturbations preserve rankings by construction; the bootstrap refits preprocessing using sampled **observed** rows on an unchanged candidate set. These uncertainties remain conditional on the limited legacy dataset. No relevance labels, confidence-calibrated signing predictions or validated historical budget recommendations exist.

## Verification outcomes

- Tests: 24 executed, 0 failures, 0 errors, 0 skipped; exit status 0. Unit fixtures are artificial and isolated from experiments.
- Four notebooks executed, 17 code cells total. Some analyses intentionally display blocked prerequisites; notebook completion is not proof those analyses ran.
- Dependency consistency: passed; setup script exercised repeatedly with locked installation and tests.
- Streamlit live health: passed; AppTest exercised real exploratory rendering, FW filtering, similar players and temporary event instrumentation.
- MLflow API: passed; artifact export validated against a FINISHED actual run.
- Default real pipeline without collected statistics: expected_failure_no_synthetic_fallback; raw/processed data unchanged by the failed attempt.
- Final training on unverified legacy data: expected_failure_provenance_guard.
- Genuine process analysis: absent_discovery_blocked.
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
