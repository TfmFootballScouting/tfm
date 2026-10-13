# Current prepared data

`review/` contains the eight source-specific cleaned tables, their CSV (large tables compressed as `.csv.gz`) and Parquet files, and `manifest.json` with hashes/counts/quality decisions. Reproduce from included raw CSVs with `python -m src.pipeline`.

`real/` contains only the three original frozen FBref training/gallery/history tables and two checksum-verified valuation/identity tables (the value loader reuses the same frozen player-season history) required by the app. The frozen tables preserve the actual experiment's byte hashes; the review outputs independently reproduce their numerical features. Understat shot analysis reads `review/understat_shots.parquet` directly, avoiding older duplicate shot datasets.

FBref club stints join by provider ID + league + season + club and compatible minutes. Season aggregation preserves identity across clubs and seasons; rates use observed exposure only. Understat remains source-separated; reported values use provisional identity links after ranking and do not enter model training. Missing/zero values are not silently estimated.

No demo/synthetic or obsolete processed datasets are included.
