# Current completion report

Reviewed 11 October 2026. Branch: `improve/reproducible-scouting`. The existing folder structure, raw data and provenance are retained. Nothing has been pushed to main. Earlier statements are preserved in [completion history](COMPLETION_HISTORY.md).

This is a working first submission using retained real observations. It does not claim that every requested source, season, validation task or fresh-checkout workflow is complete.

| Requirement | Status | Current outcome and limit |
|---|---|---|
| Data acquisition | Partial | Retained FBref and Understat archives plus uploaded profiles, valuations and histories. Uploaded basic La Liga/Segunda records cover all six target seasons; 2025/26 is incomplete. Advanced Segunda statistics remain unavailable. Source/category coverage reports retain gaps and access restrictions. |
| Integration and preprocessing | Completed for available fields; identities partial | Source-separated raw preservation, unit/date checks, missing≠zero, duplicate handling, outlier flags, club-stint aggregation and season-aware observation keys. 1,119 supported cross-source identity pairs remain unreviewed. New provider fields are review-only and do not enter training. |
| EDA | Executed | Nine executed notebooks cover successive data, model and scenario analyses. Missingness, distributions, correlations and observed cohort comparisons are documented. This does not imply full representative coverage of both leagues. |
| Machine learning | Evaluated on a profile-retrieval proxy | Three eligible real-FBref model reruns with training-only preprocessing, chronological validation/holdout, baselines, PCA/K-means analysis and robustness. MRR measures next-season same-player profile retrieval, not signing success or tactical relevance. |
| Scouting scenarios | Completed as retrospective requirements | Ten real-observation cases, configurable club/position/style/age/minutes/value ceilings, strict exclusion funnels, CSV shortlists, same-pool baselines and sensitivity. Requirements are illustrative; one vacancy contains alternative players. |
| Actual transfer validation | Blocked | Requires reviewed identities, historical publication evidence, defensible outcome labels and realistic fees/club requirements. No transfer-success score is invented. |
| Process mining | Instrumentation complete; empirical discovery blocked | Formal case/activity/UTC timestamp/actor/attributes log and directly-follows discovery. Explicit app execution/review actions are logged. Tests use temporary logs; batch analyses are not human sessions. Insufficient genuine human scouting/decision cases for empirical validation. |
| MLflow | Completed for existing real-data experiments | Three latest FINISHED runs with owner/dataset/environment/project/Git tags, model artifacts, plots and portable exports. Scenario/app phases did not retrain models or claim new model runs. |
| Project quality | Verified in retained workspace | Pinned requirements/lock, 101 passing tests, Streamlit functional tests and live health, executed notebooks and reproducible commands. Fresh checkout, remote CI and cloud snapshot restoration remain unverified. |

## Current application and budget behavior

Core is the default with all six original expert playing styles and complete galleries 2020/21–2023/24. Offensive supports vertical and counterattack with galleries through 2024/25. Sparse/partial seasons are excluded. Legacy exploration remains explicitly selectable.

Six tabs provide recommendations, similar players, PCA/clusters, profiles/history/comparison, model coverage and scouting scenarios. Model fitting and reported-price screening are separate. Positive dated reported market assessments may screen shortlists after ranking; identities remain provisional, publication time unknown and model-use restrictions visible. Market value is not an actual fee or total acquisition cost. Unknown/zero prices are excluded from budget screening; no estimated value is substituted.

## Real model results

| Model | Holdout MRR | Recall@5 | Interpretation |
|---|---:|---:|---|
| Core | 0.223352 | 0.337349 | Next-season profile retrieval; holdout 2023/24 |
| Offensive | 0.085516 | 0.106996 | Next-season profile retrieval; holdout 2024/25 |
| Attack on Core cohort | 0.065909 | 0.084337 | Restricted-feature comparison on Core cohort |

Core and offensive periods/cohorts differ, so these rows do not establish a controlled comparison. PCA components and statistical clusters are not the six playing styles. Core PC4 showed sensitivity in extended validation. Detailed metrics and uncertainty remain in the immutable model reports and notebooks; enrichment did not demonstrate a recommendation-performance gain.

## Deliverable index

- Updated code: `src/`, `scripts/`, `tests/`; app entrypoint `src/app/streamlit_app.py`.
- Data and provenance: retained `data/raw/sources/`; collected/review outputs in `data/processed/real/`. Provider-derived raw/row data remain private local files where licensing is unresolved.
- Executed analysis: [notebooks 01–09](../notebooks/).
- Real model results/artifacts: `reports/enrichment/pipeline.json`, `reports/enrichment/mlflow_export/`, `models/real/enrichment_*_recommender.joblib`.
- Data dictionary: `reports/enrichment/dictionary.csv`, plus source and collected-preprocessing dictionaries. Dictionary coverage describes existing tables, not uncollected variables.
- Scenario results: `reports/scouting_scenarios/`; private individualized `shortlist.csv` is excluded from Git.
- Current submission verification: `reports/submission/audit.json` and `tests.xml`.
- TFM documentation: [enriched pipeline](ENRICHED_PIPELINE.md), [collected application](COLLECTED_APPLICATION.md), [scenarios](SCOUTING_SCENARIOS.md), [execution instructions](FIRST_SUBMISSION.md).

## Remaining priorities

Review proposed player identities before stronger cross-source claims. Use actual app scouting/review/decision sessions to establish genuine process data. Validate source permission, historical publication timing and actual fee/outcome semantics before claiming historical transfer success. Obtain advanced Segunda coverage and fuller 2025/26 observations if accessible. Verify an authorized data-restoration workflow before claiming fresh-checkout or remote-CI reproducibility.
