# TFM — Análisis y scouting de futbolistas

Improved existing football scouting project: source-separated ingestion, auditable preprocessing, the original cosine/KNN/K-means/PCA engine, MLflow and Streamlit. Authors: Iván Galán López, Basma Marso, Carlos Valencia Sánchez.

**Submission status:** working **exploratory** application and executed notebooks. Six-season final validation is blocked by source access and historical data gaps. No synthetic data is substituted for downloads. See [completion report](docs/COMPLETION_REPORT.md), [source access](docs/SOURCE_ACCESS.md) and [data dictionary](docs/DATA_DICTIONARY.md).

## New data route: worldfootballR archives

The [11 October archive trial](docs/WORLDFOOTBALLR_TRIAL.md) successfully retrieved multi-season FBref tables, Understat shots and older Transfermarkt season-labelled records from publicly published GitHub assets. Provider pages were not crawled. See `reports/worldfootballr_coverage.csv` and the period-mismatch audit before using these records: 2025/26 is partial, some categories have incompatible 2024/25 exposure, and Segunda remains unavailable. The collected-data experiments below train separate FBref archive models; the application's earlier model remains in use.

```bash
.venv/bin/python -m pip install -r requirements-archives.txt
.venv/bin/python -m scripts.worldfootballr_archive --download
```

## Reproduce (Python 3.12, Linux/cloud)

```bash
cd tfm_futbol
bash scripts/setup.sh
source .venv/bin/activate
export MPLCONFIGDIR=/tmp/tfm-matplotlib
export XDG_CACHE_HOME=/tmp/tfm-cache
```

`requirements.txt` pins direct dependencies; `requirements.lock.txt` records the installed, tested dependency closure. Windows-only packages and unrelated browser/GUI dependencies were removed. `scripts/setup.sh` uses the lock, installs the local notebook kernel, runs pip consistency checks and tests. Existing raw files and old artifacts are preserved.

### Real-data acquisition and default pipeline

```bash
python -m src.scraping.collect
python -m scripts.transfermarkt_snapshots
python -m src.pipeline
```

The default pipeline **fails explicitly** when no eligible collected football statistics exist. The collector checks robots, caches successful raw responses with hashes, respects host delays and stops on denials/challenges. It does not bypass Understat/FBref restrictions. Coverage is recorded even when downloads are blocked. Current Transfermarkt values are not attached retrospectively to historical football statistics.

### Explicit legacy exploration (preliminary, not final results)

```bash
python -m src.pipeline --legacy-exploratory
python -m pytest -q
python -m streamlit run src/app/streamlit_app.py --server.headless true
```

The legacy raw file has 609 FBref-labelled La Liga 2023/24 rows and 840 synthetic rows. Exploration excludes every synthetic row, drops suspect row-merged statistics, applies the minutes/aggregate filter and retains 420 observations. Original HTML and retrieval dates are absent, so provenance remains unverified. The old mixed model is never loaded by the app. New outputs live in `data/processed/real/` and `models/real/`, with explicit `real_legacy_unverified` metadata.

Only the measured goals/assists profiles are exposed for this limited dataset. Six broad tactical styles require at least 60% measured absolute feature weight and are disabled here. Cosine direction is not transfer success, and can rank a balanced low-output player above a more productive one: inspect rates and baseline comparisons. Unknown prices are not free players; budgets require dated as-of EUR values.

### Executable notebooks

```bash
export JUPYTER_PATH="$PWD/.jupyter/share/jupyter"
export IPYTHONDIR=/tmp/tfm-ipython
export JUPYTER_RUNTIME_DIR=/tmp/tfm-jupyter
python -m scripts.execute_notebooks
```

Four executed `.ipynb` notebooks cover data quality/EDA, model interpretation/baselines, scouting scenarios and process mining. Their blocked sections display precise prerequisites; a successful notebook execution does not mean the blocked analyses were performed. `scripts/build_notebooks.py` is the authored source and regenerates notebooks without outputs.

### MLflow

```bash
python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 127.0.0.1 --port 5000
```

Use commands from the repository root. Real, unverified legacy exploration and synthetic demonstrations have separate experiments. Runs include owner/project/dataset/environment/Git tags (source/dependency dirty scope), dataset hashes, model artifact, plots and evaluation CSVs. Creation uses relative local locations; MLflow resolves runtime SQL-backed artifact URIs to absolute machine paths. The portable export makes artifact references and source paths relative, so copying it does not depend on that runtime store. `reports/mlflow_export/` is a portable JSON/CSV export of actual run metadata plus copied artifact files; runtime SQLite/MLflow directories are ignored and retained in the cloud snapshot. No synthetic demonstration was run for the submission.

### Process instrumentation

Explicit Streamlit searches append observed need/search/ranking events; the review button records an actual review action. `TFM_EVENT_LOG` can select a private destination. No signing decision is inferred. Logs are ignored to avoid publishing user scouting activity. There are no genuine human sessions in this submission, so process discovery is blocked; temporary AppTest logs only verify instrumentation.

## Repository layout

- `src/scraping/`: source access/policy, parsers and legacy compatibility.
- `src/data/`: immutable provenance, validated FBref joins, conservative identity proposals and as-of valuation selection.
- `src/preprocessing/`, `src/features/`, `src/models/`: existing architecture repaired; temporal proxy and descriptive evaluation added.
- `data/raw/`: preserved original datasets and content-addressed source responses.
- `data/external/`: separately normalized source samples.
- `reports/`: coverage, lineage, evaluation and executed-notebook evidence.
- `notebooks/`: EDA and analysis with actual outputs.
- `docs/`: updated first-submission TFM account and limitations.

Work is on `improve/reproducible-scouting`; main is unchanged. Existing legacy modules and author documents remain, but old claims should be read with the updated completion report. Cloud tasks already have isolated checkouts: use the existing repository, not a new worktree.

### Uploaded scraper trial and source rights

The additional toolkit was tested: it contains no data; new provider access is network-blocked. Transfermarkt terms explicitly prohibit automated copying and AI/ML use without permission. Its retained records are now restricted for model use. See [the evidence and next steps](docs/UPLOADED_SCRAPER_TRIAL.md).

### Collected-data preprocessing and mandatory features

The existing layout is preserved. Run `.venv/bin/python -m src.preprocessing.collected`, then `.venv/bin/python -m scripts.collected_eda`. New `collected_*` tables in `data/processed/real/` preserve 3,378 FBref player seasons and prepare 1,975 historical outfield baseline candidates. All ten core per-90 feature columns remain; unknown values and unavailable dated budgets remain missing. The current legacy model dataset is unchanged. Execute `notebooks/05_collected_data_preprocessing.ipynb` for multi-season EDA. See [the feature contract and preprocessing decisions](docs/COLLECTED_PREPROCESSING.md).


### Collected-data modelling and tracked experiments

Run `.venv/bin/python -m scripts.collected_models`, then `.venv/bin/python -m scripts.collected_model_notebook`. The new [model-analysis notebook](notebooks/06_collected_model_analysis.ipynb) compares chronological real-data profile retrieval, PCA, clusters, baselines and robustness. New models and reports use `collected_` prefixes in the existing folders. Matching proposals are retained for source-agreement exploration; trained features remain FBref-only. See [experiment scope, results and limitations](docs/COLLECTED_MODELS.md). These models do not overwrite the Streamlit application's previous model/data.

### Recorded value audit

The [salimt/football-datasets assessment](docs/FOOTBALL_DATASETS_ASSESSMENT.md) verifies repository access and six actual CSV paths using pinned metadata. Its advertised Transfermarkt performances/values/transfers could fill contextual gaps, but Spain/season coverage remains unverified, the linked licence returns 404 and the existing provider-use guard blocks acquisition/model use. Run `.venv/bin/python -m scripts.football_datasets_inventory` for metadata-only inspection; no provider CSVs or substitute data are downloaded.

The subsequently [uploaded Kaggle valuation archive](docs/KAGGLE_VALUE_AUDIT.md) has been inspected offline: 508 player summaries, 9,764 history records, 104 La Liga-listed players and no Segunda listing. Separate evidence tables, dictionaries and coverage reports are prepared; corrupt position/club fields, a systematic one-day date discrepancy, unknown historical availability and provider-use restrictions prevent budget/model admission. Run `.venv/bin/python -m scripts.kaggle_value_audit`, then `.venv/bin/python -m pytest -q --junitxml=reports/kaggle_value_tests.xml` and `.venv/bin/python -m scripts.verify_kaggle_values`. All 74 tests passed. Exact raw bytes and provider row tables remain local/ignored; no source-data or model overwrite, identity approval or price estimation occurred.

Run `.venv/bin/python -m scripts.valuation_audit` to audit retained amounts, identity proposals and date evidence offline. It recovers two explicit 2026 current-value dates from saved profile headers; the 1,925 archive amounts remain undated and cannot support target-season budgets. New audit tables stay in `data/processed/real/` and reports stay in `reports/`; original tables/models are preserved and no estimated prices are generated. See [exact coverage and verification commands](docs/VALUATION_AUDIT.md). The expanded suite has 68 passing tests.

### Extended real-data validation

Run `.venv/bin/python -m scripts.collected_validation`, then `.venv/bin/python -m scripts.collected_validation_notebook`. The executed [extended validation notebook](notebooks/07_collected_extended_validation.ipynb) adds person-block PCA/K-means refits, OOB agreement, seasonal drift/transitions, position-specific retrieval and all six original core playing styles. The existing folder structure and raw/model files are preserved. [Results and reproducible commands](docs/COLLECTED_VALIDATION.md) document the unstable core PC4 boundary and distinguish these post-hoc diagnostics from external transfer validation. Check evidence with `.venv/bin/python -m scripts.verify_collected_validation` after running the documented test command; the current suite has 62 passing tests.
