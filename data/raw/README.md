# Raw real data and provenance

Only the 15 source CSV inputs and `review_manifest.json` are part of this clean submission:

- `fbref/`: six statistical categories exported without cleaning from checksum-pinned `JaseZiv/worldfootballR_data` GitHub release RDS files; five leagues and target season subset.
- `understat/`: five league shot CSVs exported from the same repository's release archives; original source values retained.
- `transfermarkt/`: four byte-preserved user-uploaded CSVs; `salimt/football-datasets` origin declared by the uploader, not commit-verified.

The manifest records source URL/claimed repository, exact CSV and source-archive SHA256, acquisition timestamp, export reader/filter and columns. FBref/Understat were downloaded as RDS, then exported; they were not directly scraped or downloaded as CSV. Transfermarkt inputs were uploaded. Original scraper implementations remain under `src/scraping/`; they were not the acquisition route for the served models.

Raw CSVs are never rewritten by the cleaning/training pipeline. Historical mixed/demo samples, failed scraper trials and unused transfer/Kaggle datasets were removed from this review branch. Earlier versions remain in Git history. Source archives are optional, not needed to reproduce cleaning or training. `src/scraping/raw_inputs.py` can restore recorded GitHub archive bytes with exact SHA verification; it does not crawl provider pages. Source access/rights restrictions remain documented and enforced.
