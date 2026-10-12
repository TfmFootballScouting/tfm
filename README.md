# TFM — Análisis y scouting de futbolistas

Football scouting project by Iván Galán López, Basma Marso and Carlos Valencia Sánchez. The existing architecture has been improved with source-separated data, reproducible preprocessing, chronological model evaluation, MLflow and the ScoutIQ Streamlit application.

ScoutIQ currently serves the **five-league trained Core model and six original playing styles**. Scouts can select multiple leagues, find similar players, compare several players and their histories, and explore adjustable player groups on a PCA profile map. See the [current interface](docs/SCOUTING_INTERFACE.md) and [new player development/shot-analysis views](docs/PLAYER_ANALYSIS_APP.md).

The latest complete real-data run is documented in [FIVE_LEAGUE_FULL_PIPELINE.md](docs/FIVE_LEAGUE_FULL_PIPELINE.md): 15,948 player-season observations, three trained experiments, 50 retrospective scouting scenarios and portable MLflow artifacts. The six-style app uses completed advanced-statistic galleries through **2023/24**. Additional offensive observations extend to 2024/25 but do not support all six styles; incomplete 2025/26 data is not served.

Reported player values are optional, dated market assessments from retained private uploads. Identity associations remain provisional; [valuation verification](docs/VALUATION_VERIFICATION.md) also found that EUR is assumed rather than explicitly stated in the raw upload. Missing values are not estimated; budget controls are hidden when valuation inputs are unavailable. These experiments evaluate statistical profile retrieval, **not actual transfer success**.

## Run the app

Use the `improve/reproducible-scouting` branch. The committed model and gallery files allow ordinary scouting without retraining or downloading new data.

```bash
python -m venv .venv
# Activate .venv using your operating system's command.
python -m pip install -r requirements.lock.txt
python -m streamlit run src/app/streamlit_app.py
```

Use **Python 3.12**. On Linux/cloud, `bash scripts/setup.sh` prepares dependencies, a local notebook kernel and runs the tests in the retained development workspace. Native Windows execution is not fully verified; source fingerprints are normalized for Windows/Unix checkouts.

`requirements.txt` lists pinned direct dependencies. `requirements.lock.txt` records the tested dependency closure; these two files have different purposes. `requirements-archives.txt` supplies optional RDS archive readers for ingestion and reproduction.

## Understand the repository

Start with the [folder-by-folder review](docs/REPOSITORY_REVIEW.md) and [file inventory](reports/repository_review/file_inventory.csv). The inventory describes every tracked file at the review snapshot; it distinguishes indexing from completed semantic review.

| Folder | Purpose |
|---|---|
| `src/app/` | Current scouting interface, verified model serving, optional valuation display and scenarios. |
| `src/data/`, `src/scraping/` | Source access, provenance, parsing, identity matching and valuation-date handling. |
| `src/preprocessing/`, `src/features/`, `src/models/` | Cleaning, football features, styles, recommendation and evaluation. |
| `src/process/` | Genuine search/review event instrumentation; private logs are ignored. |
| `scripts/` | Separate ingestion, experiment, notebook and verification commands. |
| `data/raw/` | Preserved original datasets and source responses. |
| `data/external/`, `data/processed/` | Source-separated tables and versioned prepared datasets. |
| `models/` | Current trained models and retained earlier artifacts. |
| `notebooks/` | Executed EDA, model analysis and scouting/process exploration. |
| `reports/` | Coverage, dictionaries, dataset hashes, evaluation tables, figures and portable MLflow exports. |
| `docs/` | Project account, source limitations, decisions and historical stage reports. |
| `tests/` | Automated checks for data contracts, identities, chronology, source guards, models and application behavior. |

## Reproduce the latest pipeline

Follow the commands and retained-input requirements in [FIVE_LEAGUE_FULL_PIPELINE.md](docs/FIVE_LEAGUE_FULL_PIPELINE.md). Its ordered entry points are:

1. `python -m scripts.five_league_pipeline` — cleaning, preprocessing, EDA, chronological model fits and MLflow.
2. `python -m scripts.five_league_comparison` — matched-candidate-pool comparisons against earlier models.
3. `python -m scripts.five_league_review` — provisional source links and retrospective budget scenarios using retained uploads.
4. `python -m scripts.five_league_pipeline_notebook` — executable analysis notebook generation and execution.

Raw RDS archives and private uploaded valuation inputs are retained locally and excluded from Git. A fresh clone may therefore run the app but cannot reproduce every ingestion/valuation experiment without those inputs. Never replace a missing download with synthetic football data. Source access restrictions and model-use guards remain enforced.

For the retained development workspace:

```bash
python -m pip check
python -m pytest -q
```

Several integration tests require retained source/private inputs and optional archive readers. The hosted CI configuration runs the full suite; a clean hosted run is not verified by local success. Historical test XML files record earlier executions rather than current readiness.

## Additional data for the four added leagues

[Four-league acquisition](docs/FOUR_LEAGUE_DATA_EXPANSION.md) provides 182,938 Understat shots, full retained FBref category fields and separate review-only recruitment context. New tables are retained locally with pinned provenance and coverage reports; current app models remain unchanged. Bundesliga/Serie A 2024/25 shot coverage has gaps, and 2025/26 is partial.

The [four-league preprocessing and EDA](docs/FOUR_LEAGUE_PREPROCESSING.md) now includes cleaned shots, player-season summaries, season-specific identity proposals and executed notebook 13. These proposals remain provisional; the current recommender is unchanged.

## Analysis notebooks

- [11: Full five-league pipeline](notebooks/11_five_league_full_pipeline.ipynb): quality, EDA, chronology, baselines, PCA/K-means interpretation, bootstrap robustness, scenarios and MLflow.
- [12: Adjustable scouting groups](notebooks/12_scouting_group_exploration.ipynb): descriptive grouping diagnostics; saved recommendation artifacts remain unchanged.
- [13: Four-league shot EDA](notebooks/13_four_league_shot_eda.ipynb): shot quality, attacking profiles, coverage exclusions, conservative identity proposals and advanced-feature readiness.
- Notebooks 01–10 retain earlier stages and their actual outputs. Their counts and limitations describe those earlier datasets/models. Each has corresponding documentation in `docs/`.

## MLflow and observed scouting events

From the repository root:

```bash
python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 127.0.0.1 --port 5000
```

The local SQLite database and runtime artifact directories are ignored. Portable exports of actual run metadata and artifacts are committed under `reports/`, including `reports/five_league_pipeline/mlflow_export/`. Real experiments and synthetic demonstrations are separated; no synthetic demonstration was used for final experiments.

Explicit app searches and review actions produce events with case IDs, activities and timestamps. `TFM_EVENT_LOG` selects the private destination. Automated test events verify instrumentation, but are not genuine scout sessions or evidence of a transfer decision. Process discovery requires genuine event data.

## Documentation and retained stages

Current entry points: [completion report](docs/COMPLETION_REPORT.md), [first-submission instructions](docs/FIRST_SUBMISSION.md), [data dictionary](docs/DATA_DICTIONARY.md) and [source access](docs/SOURCE_ACCESS.md).

Earlier stage evidence remains available: [archive acquisition](docs/WORLDFOOTBALLR_TRIAL.md), [collected preprocessing](docs/COLLECTED_PREPROCESSING.md), [collected models](docs/COLLECTED_MODELS.md), [extended validation](docs/COLLECTED_VALIDATION.md), [enrichment](docs/ENRICHED_PIPELINE.md), [uploaded values](docs/SALIMT_UPLOADED_AUDIT.md), [uploaded histories](docs/SALIMT_HISTORY_AUDIT.md), [budget interpretation](docs/REPORTED_VALUE_BUDGET.md) and [scouting scenarios](docs/SCOUTING_SCENARIOS.md). Original author documents and preliminary legacy artifacts are retained for traceability; they are not the app's current training dataset.

Work stays on `improve/reproducible-scouting`; main is not modified. Preserve the existing folder structure, raw provenance, source restrictions and historical experiment evidence. Cloud tasks already have isolated checkouts; use the existing repository rather than creating an unsolicited worktree.

## Source lineage and raw archive restoration

See [data sources and pipeline paths](docs/DATA_SOURCES.md), [player-season coverage](docs/DATA_COVERAGE.csv), [category coverage](docs/DATA_CATEGORY_COVERAGE.csv) and [raw archive restoration](data/raw/README.md). The raw source manifest records original providers, secondary download URLs, checksums and optional private uploads.

```bash
python -m src.scraping.raw_inputs --verify
python -m src.scraping.raw_inputs --download
```

The minimal serving branch is `minimal/scoutiq-runtime`; the full preparation, training, notebooks and research reports remain on this branch. Prepared valuation files and identity proposals are included for budget screening after cloning; provider-derived raw archives remain local.

The included prepared valuation files make the reported-value budget filter available after cloning. Source identity links remain provisional, values retain their dates, and currency remains assumed EUR. Valuations do not enter recommendation model fitting.

Scouting scenario evaluation remains in `notebooks/09_scouting_scenarios.ipynb` and `src/app/scenarios.py`. The separate Streamlit scenarios tab has been removed; everyday recruitment requirements are handled by the main recommendation filters.

## Transfer-likelihood feasibility

The real-data label audit and executed notebook are documented in [TRANSFER_LIKELIHOOD.md](docs/TRANSFER_LIKELIHOOD.md). It finds reported positive candidates but no verified negative labels; no transfer model has been trained.
