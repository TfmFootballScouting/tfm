# Raw data for teacher review

Current review inputs are the CSVs in `fbref/`, `understat/` and `transfermarkt/`. `review_manifest.json` lists every file, source/provider, exact hash, row count, source columns and extraction rule.

- FBref: six source-preserving target-season CSV exports from the retained `JaseZiv/worldfootballR_data` RDS release assets.
- Understat: five source-preserving shot CSV exports from the same secondary GitHub repository.
- Transfermarkt: four unchanged CSV uploads with claimed origin `salimt/football-datasets`; exact upstream repository commit was not verified.

FBref/Understat files were downloaded as **RDS, not CSV**. CSV export preserves source columns/values while selecting the declared five-league/2020–2025 target range; it does not clean, merge or impute them. Archive URLs/checksums and original acquisition timestamps remain in the manifest; original RDS bytes are locally preserved under `sources/` and can be restored using `src/scraping/raw_inputs.py`. No new provider crawl or synthetic replacement occurs during packaging.

Older `players_raw.*` and HTML samples are historical original-stage evidence, including mixed/demo content. They are not listed in the review-input manifest and are never inputs to `python -m src.pipeline` or final model experiments. Original receipts and source-use restrictions are retained; GitHub hosting does not establish provider training permission.

Preprocessing: `src/preprocessing/review_dataset.py` and `collected.py`. Prepared outputs and their hashes: `data/processed/review/manifest.json`. Code to recreate these exports from retained archives/uploads: `scripts/build_review_csvs.py` (requires optional archive readers).
