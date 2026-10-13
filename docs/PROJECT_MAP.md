# Start here — project reading order

You do not need to read every file. Follow these three routes.

## 1. Use the scouting app

Follow README installation, then run:

```bash
python -m streamlit run src/app/streamlit_app.py
```

`src/app/streamlit_app.py` is the UI entry point. `model_loader.py` verifies and loads the saved model/data; `scouting_service.py` builds the selected season gallery; `market_value_filter.py` and `valuation_loader.py` handle reported-price screening; `player_analysis.py` handles histories/shots; `ui_helpers.py` and `ui_theme.py` handle labels/groups/presentation. `src/process/` holds operational events/feedback separately from MLflow.

## 2. Understand the data and results

Read notebooks in order:

| Notebook | Question answered |
|---|---|
| 01_fbref_data_exploration.ipynb | What are the performance data, coverage and quality issues? |
| 02_understat_data_exploration.ipynb | What shot/xG data exist and what are their limits? |
| 03_transfermarkt_data_exploration.ipynb | What profile/valuation data exist and how reliable are they? |
| 04_feature_comparison_and_model_validation.ipynb | Which feature sets and methods were tested, what was selected, and how do baselines/PCA/clusters/robustness perform? |
| 05_pca_and_player_clusters.ipynb | How does changing the number of groups affect separation and player membership? |
| 06_expert_recommendation_validation.ipynb | How will real scouts evaluate shortlist relevance? Ratings remain pending. |

Notebook 04 analyzes actual executed experiments. It compares two attribute sets on the same cohort, seven profile methods and training cluster counts. It does not automatically search every possible attribute combination. Re-run fitting separately with `python -m scripts.train_models`; simply opening the notebook does not refit or replace the saved model.

## 3. Follow the implementation

| Stage | Start file | Supporting files |
|---|---|---|
| Source inputs | data/raw/source_manifest.json | Raw provider CSVs; docs/DATA_SOURCES.md; src/scraping/ for original parsers/archive restoration/export |
| Cleaning | src/pipeline.py → src/preprocessing/prepare_datasets.py | football_stats.py: season aggregation/rates/quality; fbref_categories.py: category joins; src/data/ identity/provenance helpers |
| Training | scripts/train_models.py | src/models/experiments.py: feature/cohort definitions, method selection and baselines |
| Algorithms | src/models/recommender.py | Imputation, scaling, nearest profiles, PCA, K-means; src/features/styles.py defines six styles |
| Robustness | src/models/robustness_validation.py | Bootstrap, temporal/position analysis; current recorded results under reports/five_league_pipeline/ |
| Serving | src/app/streamlit_app.py | Current model/gallery/value loaders and presentation helpers |
| Verification | src/tests/ | python -m pytest -q |

`src/preprocessing/player_records.py` preserves the original scraper-record normalization contract, tested independently; `prepare_datasets.py` is the current included-CSV pipeline.

## Why one old filename remains

`src/models/recommend.py` is a two-line compatibility import for the original frozen joblib class paths. The implementation is `recommender.py`. Removing that compatibility file would break the original saved model; the binary is deliberately unchanged. Original training code hashes/Git commit remain in `experiment_manifest.json`; renamed serving code has a separate verified fingerprint map. Original MLflow lineage names remain historical facts, not current startup commands.

Other scripts are named by their purpose: `build_eda_notebooks.py`, `build_processed_dictionary.py`, `build_raw_dictionary.py`, `prepare_expert_review.py`, `estimate_cloud_costs.py`. Read `TEACHER_FEEDBACK.md` only when reviewing the professor's comments and remaining manual evidence.

Current deployment/training uses one recommender with six styles, without Core/Offensive model choices. Alternative attributes are compared only in notebook 04. The original saved binary and genuine metrics are unchanged.
