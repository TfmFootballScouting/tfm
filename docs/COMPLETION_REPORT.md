> Collected-data preprocessing update: real retained archives are now cleaned and audited across seasons without changing the original folder structure or fitted model. See [mandatory features, cohorts and executed EDA](COLLECTED_PREPROCESSING.md).

> Latest uploaded-data update, 11 October 2026: the Kaggle candidate ZIP is preserved and inspected offline (508 player summaries, 9,764 history records). Completed: source-separated audit tables, dictionary, listing/season coverage, unreviewed mapping packets and 74 passing tests. Its 104 La Liga-listed players provide retrospective price observations, but there is no Segunda listing or performance/fee table. Corrupt profile fields, unresolved one-day date discrepancies, unknown historical availability, unreviewed identities and missing provider authorization prevent model/budget admission. No price estimates, model refits or existing-data overwrite occurred. See [executed evidence and commands](KAGGLE_VALUE_AUDIT.md). Collected-model Streamlit integration remains pending.

> Update, 11 October 2026, uploaded scraper trial: Transfermarkt terms section 11.1 explicitly restrict automated copying and AI/ML use. Its retained datasets are blocked for model use pending an explicit licence. Three new providers require cloud network changes before access can be tested. See [uploaded scraper trial](UPLOADED_SCRAPER_TRIAL.md).

> Update, 11 October 2026: published worldfootballR archives now provide additional historical data without crawling provider sites. See [archive trial](WORLDFOOTBALLR_TRIAL.md) and `reports/worldfootballr_coverage.csv`. The original direct-access results and first-submission model below remain valid for their stated scope. No model retraining is claimed by the archive trial.

# Completion report — first reproducible submission

**Latest evidence (11 October):** collected-data modelling, extended validation and the [recorded valuation audit](VALUATION_AUDIT.md) supersede earlier diagnostic status below. The current suite has 68 passing tests; seven executed analysis notebooks document the successive modelling phases. The audit recovers two dated current values while confirming zero target-season budget attachments. Historical sections remain an audit trail; actual transfer, historical budget, Segunda and genuine process validation remain incomplete.

Checked at 2026-10-10T15:27:45.570417+00:00 (UTC). Work branch: `improve/reproducible-scouting` in `valen28030/tfm_futbol`. Existing architecture retained; main unchanged. No changes have been pushed. The originally selected `TfmFootballScouting/tfm` checkout is still empty and was not overwritten. Breakout is retained as an unchanged reference.

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
| 8. Project quality | **Completed locally; remote CI unverified** | Python 3.12 direct pins + resolved lock, reproducible setup, portable metadata, 24 tests, Streamlit functional AppTest and live health, MLflow live API, four executed notebooks and updated TFM docs. GitHub Actions added but not executed remotely. Cloud snapshot publication/fresh-task restoration remain user/product actions, not verified here. |

## Data evidence and safeguards

- Legacy raw input: 609 FBref-labelled La Liga 2023/24 rows + 840 synthetic rows. The originals are unchanged.
- Retained exploratory observations: 420. Every synthetic row is excluded. Suspect ancillary statistics from index-based joins are discarded, and no invented `budget_est` is used.
- Available fitted features: gls_p90, ast_p90. Broad tactical styles are disabled below 60% measured absolute weight; only goals/assists profiles are offered.
- Original source HTML/retrieval dates are missing for legacy statistics. `real_legacy_unverified` is a provenance status, **not a claim of final verified real data**. Final training refuses this dataset unless explicitly exploratory.
- Current TM pages are not historical season data despite the requested season URL. Valuation effective dates remain unknown and no backdated price is inferred. Market values are not transfer fees.
- 146 provenance records / 103 distinct raw response hashes verified against stored content. See `data/raw/provenance.jsonl`, `reports/source_coverage.csv`, `reports/transfermarkt_sample_access.csv`, `docs/SOURCE_ACCESS.md`.

## Actually executed exploratory results

Run ID: `7931521312e34ea981241165f423977c`. Recorded source commit: `602f883bae3ee6feadfea2c51cab551ec619692b`; recorded source/dependency dirty state: `False`. Dataset SHA-256: `05e6266ab5f45651ff69c763413d3fbb196de6fd061d44bb48899b09b305fc6c`. Full precision and tags are in `models/real/metrics.json` and `reports/mlflow_export/run.json`.

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

## Collected-data preprocessing and EDA update

Phase 2 cleaning is now executed across retained real archives, with stable IDs, source-separated outputs, mandatory schema/coverage, units, missingness, multi-club aggregation, lineage and two chronological cohort designs. Cross-source enrichment remains partial: 2,371 review candidates, no approved mappings, and no eligible dated historical budget attachments. Source flags remain explicit.

Phase 3 now has an executed multi-season real-data notebook, `05_collected_data_preprocessing.ipynb`: ten code cells, zero error outputs. It includes distributions, outliers, training-period correlations, position/season comparisons and source-specific interpretation. A full real league comparison remains unavailable because the 25-row Segunda leaderboard is a biased sample.

Prepared FBref observations: 3,378 player seasons, 1,975 historical outfield baseline candidates, and 1,577 fully measured core-proxy candidates. All 43 tests passed, with no failures/skips. Repeated preprocessing produced identical bytes for all 13 exported tables, and ten raw archive checksums were verified. Existing legacy raw files, served dataset/database and model are byte-for-byte unchanged. Phases 4/5 were not rerun; no new model performance or transfer-success results are claimed. Evidence is in `collected_preprocessing.json`, `collected_preprocessing_verification.json`, `collected_eda.json`, and `collected_notebook_execution.json` under reports.


## Multi-feature identity matching update

A real-data offline trial now resolves candidate identities using normalized names, explicit club aliases, season/league history and comparable birth years. It produces a stable FBref-anchored person key, scored crosswalk proposals and a separate source-prefixed club-season join preview. Latest-cutoff supported proposals: 977 Understat and 803 Transfermarkt; preview attachments: 2,317 and 1,420 club-season rows respectively. Score confidence is uncalibrated and matching accuracy is unmeasured. Human identity approval and final model integration remain incomplete; proposals cannot enter model fitting/transformation. No raw, previously processed source table or fitted model is overwritten. See `docs/COLLECTED_PREPROCESSING.md` and `reports/identity_resolution.json`.


## Collected recommendation modelling update

Completed: three real FBref archive experiments (offensive, core and a post-hoc attack-on-core ablation); chronological development/validation/holdout separation; training-only median/scaler/PCA/clustering; goals, goals-and-assists and random baselines; MRR/Recall@5/10/NDCG@10 with uniform tie handling; paired bootstrap intervals; K selection, seed stability, centroid/position/season analysis; selected-method shortlist robustness; historical position/age/club scouting examples; ten executed notebook code cells; three finished MLflow runs with genuinely downloaded portable artifacts; 57 passing automated tests. The recommender now persists the validation-selected neighbour representation, retaining compatibility with the existing model.

Both main tracks selected full standardized Euclidean profiles. Offensive holdout 2024/25: 243 returning queries, MRR 0.0855, Recall@5 10.7%. Core holdout 2023/24: 249 queries, MRR 0.2234, Recall@5 33.7%. The different holdout seasons prevent a direct comparison. The post-hoc same-cohort six-feature ablation has holdout MRR 0.0659, compared with 0.2234 for nine core features. PCA compression loses retrieval information and hard cluster filtering removes some correct targets. Two development clusters describe attacking-output differences, not validated tactical roles.

Partial: the accepted identity matching method supports provisional source-agreement diagnostics; individual cross-source links remain unverified. Model features and temporal identity labels remain FBref-only. Historical shortlist examples have age/position/club constraints but no eligible dated budgets. The Streamlit app remains operational with its earlier dataset/model; integration of the new models is a separate outstanding step.

Blocked/unverified: independent recommendation relevance, actual historical transfer success, complete Segunda coverage, goalkeeper-specific evaluation, strict historical as-of availability, budget validation and genuine event-process discovery. These retrieval results do not constitute transfer-quality validation. See `docs/COLLECTED_MODELS.md` and `reports/collected_model_results.json` for precise scope and artifact paths.

## Extended PCA, K-means and recommendation validation update

Completed: 30 whole-player development bootstrap refits per model track; training-only median/scaler/PCA/K-means; OOB cluster agreement and aligned centroids; sign/order-aware PCA loading analysis, subspace angles and full eigenvalue spectra; frozen-cluster seasonal distributions/transitions and descriptive feature drift; seasonal DF/MF/FW retrieval with identity-paired baseline intervals; all six original core style rankings, shortlist overlap and bootstrap stability; notebook 07 executed nine code cells without errors; three selected finished validation MLflow runs with 57 checked logged/exported artifacts; 62 passing tests, no failures/errors/skips. Raw archives, source tables, identity proposals, baseline fitted models and original application files remain unchanged.

Core mean OOB cluster ARI is 0.9731 and mean neighbor top-five Jaccard is 0.9444. Core PC4 has a bootstrap loading cosine as low as 0.1303, with a maximum top-four subspace angle of 82.54°; eigenvalue diagnostics identify sensitivity near the component cutoff. Core holdout Recall@5 is 29.0% for DF, 36.8% for FW and 37.6% for MF. All six original styles were exercised; mean style top-five Jaccard is 0.9026. These are measured stability/profile-persistence diagnostics rather than labelled tactical or transfer quality.

Partial/unverified: the diagnostics are post hoc on previously examined cohorts, conditional on selected K/component width and archive coverage. They do not supply new independent confirmation. Dated budgets, full Segunda, transfer labels, source as-of proof, human identity accuracy and genuine scouting events remain unavailable. Streamlit still uses the earlier dataset/model; collected-model application integration is the next implementation step. See `docs/COLLECTED_VALIDATION.md`, `reports/collected_validation_results.json` and `reports/collected_validation_verification.json`.

## Recorded-value identity/date audit update

Completed offline: verified 2,018 archive records (1,925 amounts, 1,125 source identities); inspected raw date fields; replayed six retained source headers to recover two explicit current update dates missed by the older parser; consolidated repeated headers; exported source/league/season/cutoff coverage and review packets; added conservative recorded-value import selection and six semantic tests. The full suite has 68 passes, zero failures/errors/skips. All 171 preserved source/model/evaluation/notebook files and 13 audit outputs were checked. No downloads, estimates or model fitting were performed.

New date evidence: Lamine Yamal source assessment €220m, header update 2026-07-22; Andrei Rațiu €24m, header update 2026-10-05. First retained observations are 2026-10-10. These are source-reported current assessments, not fees or historical series. Both name/birth-year links to FBref are supported proposals, not human approvals. The dates are later than every target season-end cutoff; zero historical budget attachments are eligible. Archive season labels, DOB, joining and contract dates cannot replace valuation dates. Existing source-use restrictions remain.

Partial/blocked: source amounts and provisional identity context exist; dated historical valuations, independent identity review and eligible use authorization remain absent. Current evidence is stored separately and never backfills historical rows. App/model files remain unchanged. Details and reproducible commands are in `docs/VALUATION_AUDIT.md` and `reports/valuation_audit_verification.json`.
