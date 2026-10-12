# Teacher feedback: verified changes, proposed work and manual evidence

Review branch: `review/teacher-submission`. This assessment distinguishes code/data that exist from validations or screenshots that have not been performed. Current numerical evaluation is next-season statistical profile retrieval, not evidence of successful signings. Transfer likelihood is excluded from the application.

| # | Teacher comment | Current status and evidence | Remaining action |
|---|---|---|---|
| 1 | Simplify dependencies | Fixed for serving: 8 direct dependencies in `requirements.txt`; app lock separate from `requirements-research*`. Archive readers remain optional. | Research dependency closure and clean checkout are checked separately. Native Windows still needs a manual check. |
| 2 | Remove absolute paths | Active source code and current `models/metrics.json` use project-relative paths. Source fingerprints handle Windows line endings. | Historical-stage exports can contain old runtime paths; they are not the active model metadata. Archived originals remain preserved; the portability audit records findings and supplies relative presentation copies when needed. |
| 3 | Expert validation | Chronological baselines, uncertainty and qualitative profile checks exist. A human-review protocol is described in Module 2. | No expert ratings exist. Blinded packets/forms and executed analysis notebook added; recruit actual football experts and collect their judgments. |
| 4 | Clarify market values | App uses dated reported amounts after ranking, with missing/zero handling and provisional identity warnings. No heuristic estimate or valuation model is active. | Independently verify identity and currency. EUR is assumed, and valuation event date is not historical publication proof. |
| 5 | Data dictionary | Field catalogs and source-specific dictionaries exist; this review explains core rates, units, keys and valuation semantics. | Prepared glossary completed; raw catalog added. Two unused team points fields remain pending provider clarification. |
| 6 | Process case ID | `src/process/events.py` records `case_id`; the app creates a UUID per request and stores it as `scouting_case`. | Documented equivalence to a scouting-request ID. Implemented: iterative searches reuse a request until the scout starts a new one. |
| 7 | Event log | Actual explicit searches/reviews log case, activity, UTC timestamp, role and attributes; styles/filters and result counts are included. | Declared aliases and player IDs are now persisted; aliases are not authenticated identities. |
| 8 | Process variations | Directly-follows discovery, per-case duration and edge waiting-time code exists. | No genuine human sessions are supplied; no organizational process findings are claimed. Collect real sessions before analysis. |
| 9 | Event collection | Module 9 explains the exact Streamlit triggers and JSONL destination. Automated tests use isolated logs. | Automatic filter previews are not logged as deliberate scouting searches. |
| 10 | Operational store vs MLflow | Operational JSONL events are separate from the MLflow experiment SQLite DB. | Implemented separate requests/events/feedback SQLite database; MLflow remains separate. See operational tracking document. |
| 11 | AWS calculator evidence | Original cloud architecture/estimate retained and labelled historical assumptions. | Obtain official calculator screenshot/export, date, region, currency and dated exchange-rate evidence. No current price is invented. |
| 12 | Cloud cost detail | Original compute, disk and transfer estimates exist. | Detailed tested worksheet includes backups and request charges; official unit-price evidence remains blocked/pending. |
| 13 | MLflow versioning | Real five-league runs record dataset SHA/version and original training Git commit. Source/data/model fingerprints remain preserved. | The teacher-review commit is not falsely substituted for the original training commit. |
| 14 | MLflow tags | Real run JSON includes owner, dataset, environment, project, Git and evaluation-purpose tags. | Completed for current exported experiments. |
| 15 | Evaluation plots | Actual evaluation figures and diagnostic CSVs are exported under `reports/five_league_pipeline/mlflow_export/`. | Completed; artifacts are original executed evidence, not newly generated metrics. |
| 16 | Synthetic separation | Final pipeline uses real FBref; synthetic demo is separately named and excluded. Unit fixtures are labelled artificial tests. | Original mixed/demo files remain historical evidence only and are not review-pipeline inputs. |
| 17 | Portable MLflow metadata | Current run exports use relative artifact paths and `artifact_root="."`; runtime DB/caches are ignored. | Fresh-clone serving is tested. Existing local MLflow DB is not packaged; UI screenshots/reproduction must not be claimed from a clone without running/importing evidence honestly. |
| 18 | MLflow screenshots | Actual FINISHED run metadata/metrics/artifacts are available. | Actual main-run screenshot captured in docs/evidence/mlflow with run ID and screenshot hash. No new training claimed. |
| 19 | Production improvements | Original cloud document now distinguishes current prototype from proposed production controls. | Authentication, HTTPS, monitoring, managed DB, backups and scaling are discussed, not falsely presented as deployed. |

## Approved additions and external evidence still needed

**A — Priority TFM evidence:** complete the field-by-field raw/processed dictionary; create a blind expert-rating form and analysis notebook; capture actual MLflow screenshots; sweep remaining historical metadata for local paths without changing original results.

**B — Operational traceability:** enrich event payloads with source player IDs, filters, model/dataset versions and participant aliases; add a separate SQLite scouting-request/decision/feedback store; export a formal event log and analyze genuine sessions when supplied. Preserve MLflow solely for ML experiments.

**C — Cost documentation:** prepare a detailed compute/storage/egress/backup/request cost workbook and evidence checklist. Fill official prices only from verified dated calculator results; original estimates are not a current quote.

The user approved A, B and C. Implemented: prepared/raw field glossaries (two unused raw team fields remain unverified), real-data blinded expert packets, executed human-analysis notebook with pending status, actual Core MLflow screenshot, separate operational SQLite store with player decisions/ratings and iterative request lifecycle, and the cost formula worksheet with tests. See `OPERATIONAL_TRACKING.md`, `expert_review/README.md`, `evidence/mlflow/README.md` and `evidence/cloud/README.md`.

Still manual: collect independent expert judgments and consent; collect genuine scouting sessions; verify currency and provisional player identity; obtain official AWS calculator/export and dated exchange quote (network requests returned 403); run native Windows verification. No transfer prediction or new model fit was added.

## What you need to do manually

### Expert evaluation

1. Recruit football scouts/coaches/analysts and record their relevant experience. Non-expert usability testers must not be labelled scouting experts.
2. Agree recruitment briefs and evaluation criteria before looking at results: position, style, league, age and budget assumptions.
3. Have experts rate randomized/blinded system and baseline shortlists using video/context, not only our own input statistics. Record fit, further-investigation relevance and rationale.
4. Retain dated anonymous ratings and consent as appropriate. Actual ratings are necessary for Precision@K/relevance and inter-rater agreement; no ratings are fabricated.

### Genuine process evidence

Ask participants to perform explicit searches and click shortlist review. Use the real app log (`data/events/scouting.jsonl` or `TFM_EVENT_LOG`); keep automated tests separate. Record which sessions were human and what aliases mean. JSONL timestamps capture app actions; they do not establish a real club's signing process. The event/database improvements are implemented; collect multi-step human cases before studying repetitions or waiting times.

### AWS evidence

Open [AWS Pricing Calculator](https://calculator.aws/). Choose region `eu-west-1`, Linux On-Demand, and the documented demo workload (initial assumptions: t3.medium, 730 h/month or a separate 40 h demo scenario, 50 GB gp3). Confirm whether these assumptions fit your deployment. Add estimated egress, retained snapshots/backup storage and request counts. Do not assume free tier or credits unless the calculator explicitly applies them. Save a screenshot and calculator export/share link with the actual capture date. Record tax assumptions.

Obtain a dated exchange rate from an authoritative source such as the [ECB](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html). If the quote is **1 EUR = X USD**, divide the USD total by X; do not accidentally multiply. Preserve the rate's publication date, which may differ from the screenshot date. Put evidence under `docs/evidence/cloud/`. Old 0.92 EUR/USD assumptions are not today's verified rate.

### MLflow evidence

Install research dependencies. From the project root, start `python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 127.0.0.1 --port 5000`. In the retained workspace select the actual five-league Core FINISHED run and capture (1) run overview with tags/parameters, (2) metrics, and (3) evaluation/model artifact views. Put images under `docs/evidence/mlflow/` with date and run ID. A fresh clone does not contain the ignored local DB; the committed portable `run.json`/artifacts remain the original evidence. A replay/import must be labelled replay, never a new training execution.

### Local Windows verification

Use Python 3.12, a clean clone of this branch and the app lock. Run `python -m pip check`, start Streamlit, exercise all five-league filters, values, comparisons and shot plots. Report exact errors if any; Linux checks do not establish a Windows pass.
