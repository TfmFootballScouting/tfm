# Real-data flow and reproducibility

## Acquisition / raw inputs

See `data/raw/source_manifest.json` for the individual source URLs, archive SHA256, retrieval timestamp, CSV SHA256 and export filters. FBref and Understat came from published `JaseZiv/worldfootballR_data` RDS assets on GitHub, then source-preserving CSV export. Four Transfermarkt CSVs were user uploads with declared `salimt/football-datasets` origin. No direct provider scraping produced the current model inputs. `src/scraping/collect.py`, `fbref.py` and `transfermarkt.py` preserve the original scraper implementations; `raw_inputs.py` verifies/restores recorded archive bytes. `export_csv.py` reproduces source-preserving RDS exports, verifies exact CSV hashes, and never replaces a mismatching output. Optional readers: `requirements-archives.txt`. Respect provider access restrictions; a public secondary repository is not proof of unrestricted data licensing.

Paths: `data/raw/fbref/`, `data/raw/understat/`, `data/raw/transfermarkt/`. Raw files remain unmodified. Historical original RDS bytes/receipts are not necessary in the clone; their recorded hashes and acquisition metadata remain in the manifest.

## Cleaning and joining

Entry point: `python -m src.pipeline`. Code: `src/preprocessing/prepare_datasets.py`, `football_stats.py`; category alignment helpers: `src/preprocessing/fbref_categories.py`; profile/value normalization: `src/data/salimt_uploaded.py`; identity matching: `src/data/identity.py`, `matching.py`.

FBref statistical categories join on source player ID, league, season, club and checked exposure; aggregate club stints into player/league/season. Cross-league stints remain separate in history; the gallery chooses the highest-minutes league per source identity and season. Missing counts remain unknown; per-90 rates use minutes/90; invalid values are flagged/quarantined. Understat is a separate shot dataset, not an extra input to the fitted models. Transfermarkt identity proposals use supporting name/club/season metadata; they are provisional, not universal name-only keys.

Outputs: `data/processed/review/`. Frozen app inputs: `data/processed/real/`. Dictionary: `DATA_DICTIONARY.md`, `data_dictionary_raw.csv`, `data_dictionary_review.csv`.

## Models and app

Training entry point: `python -m scripts.train_models`; orchestration now uses the included raw CSVs and writes new timestamped outputs separately. Fitting/evaluation algorithms: `src/models/experiments.py`, `validation.py`, `recommend.py`. Chronological splits prevent future-season fitting. Models are in `models/`; the original recorded training commit/hashes and evaluation are in `reports/five_league_pipeline/`. This packaging change does not change original numerical results or pretend the adapted orchestration was used in the earlier recorded run.

Streamlit: `src/app/streamlit_app.py`; frozen serving/checks: `model_loader.py`, `scouting_service.py`; budget/value integrity: `market_value_filter.py`, `valuation_loader.py`; source shot/history views: `player_analysis.py`. The single recommender has six expert-weighted styles, not six supervised classifiers. Reported values are post-ranking filters with provisional identities and unverified EUR assumption, not transfer fees or historical publication evidence.

## Review

Six notebooks cover source EDA, actual temporal/baseline/PCA/cluster validation, editable group exploration and human expert review. Human ratings and operational sessions remain pending. MLflow metadata and single-copy artifact SHA manifests, genuine screenshots, the cloud cost worksheet and original teaching documents remain included. Earlier abandoned experiments can be consulted at Git commit `252e0304a54216eb77bcdfb5c5ef73731043f158`; they are deliberately absent from this clean submission.
