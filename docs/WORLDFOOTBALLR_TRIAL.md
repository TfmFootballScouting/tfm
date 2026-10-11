> Update, 11 October 2026, uploaded scraper trial: Transfermarkt terms section 11.1 explicitly restrict automated copying and AI/ML use. Its retained datasets are blocked for model use pending an explicit licence. Three new providers require cloud network changes before access can be tested. See [uploaded scraper trial](UPLOADED_SCRAPER_TRIAL.md).

# worldfootballR archive trial — 11 October 2026

The pasted article was tested against the actual `JaseZiv/worldfootballR` code and `JaseZiv/worldfootballR_data` datasets. **The archive route works.** No blocked FBref or Understat provider pages were crawled. The upstream data repository is archived and explicitly says it will no longer be maintained. Its `load_understat_league_shots` function takes a league argument, not the article's `season_start_year` argument; filter the loaded archive by season instead.

## Retrieved and actually decoded

| Source/category | La Liga target-season observations | Coverage |
|---|---:|---|
| FBref standard | 3,443 player/club/season rows | 2020/21–2024/25 plus early 2025/26 |
| FBref shooting and passing | 3,443 rows each | Same labels; nine 2021/22 passing rows have inconsistent exposure |
| FBref defense, possession and misc | 2,874 rows each | 2020/21–2023/24; 470 rows in 2024/25, mostly partial-period; no 2025/26 |
| Understat shots | 45,847 shots | 2020/21–2024/25: 380 distinct matches per season; 2025/26: 997 shots over 41 matches, through 15 September 2025 |
| Transfermarkt season-labelled valuations/profiles | See `reports/worldfootballr_coverage.csv` | 2020/21–2022/23 only; no effective valuation date / known-at date |
| Transfermarkt transfers/fees | See `reports/worldfootballr_coverage.csv` | 2020/21–2022/23 only; arrivals/departures may describe the same movement twice; no exact transfer date |
| Published FBref–Transfermarkt ID mapping | See `reports/worldfootballr_inventory.json` | Upstream mapping, not a locally reviewed identity equivalence |

These assets do not provide Segunda coverage. The archive is not final 2025/26 data: release files were last modified in September 2025. Row counts include multi-club observations and repeated people across seasons, not that many unique players. Availability is not an assurance of complete seasons or compatible collection times.

## Reliability check that changes how we can use it

The standard table has full-season 2024/25 exposure while the defensive/possession/misc snapshots have earlier exposure. Across these three categories, **1,320 joined rows** disagree with standard minutes; another **nine passing rows** disagree in 2021/22. The loader checks source player ID, club and season plus published 90-minute exposure against minutes/90, allowing 0.061 units for rounding. The candidate table nulls incompatible statistics rather than dividing partial-season totals by full-season minutes. Missing keys stay missing. Original tables are preserved separately.

`data/external/worldfootballr/fbref_player_seasons.parquet` is an audited candidate input, not a fitted model dataset. It preserves unknown statistics and marks the partial 2025/26 period. The six provider tables are separately exported under the same directory. Understat is also retained at shot grain; its player shot totals have **no minutes or per-90 values**, and player names of assistants are not converted into verified assist IDs or xA.

Transfermarkt files contain numeric reported values and fees, but season labels alone do not establish when they were knowable. They cannot yet justify leakage-safe historical budget or transfer validation. The published identity mapping is labelled `upstream_published_not_locally_reviewed`; its missing/duplicate IDs are counted, not silently resolved.

## Preservation and reproduction

- Raw RDS/CSV bytes are retained under `data/raw/sources/*_worldfootballr/`, outside Git tracking because they are approximately 96 MB of provider-derived research data. They remain in this cloud workspace.
- `reports/worldfootballr_sources.json` pins each actual raw SHA-256, source URL, retrieval timestamp, archive location and available HTTP modification metadata. Release asset bytes are not assumed to match a repository Git commit; Git-blob assets are pinned to commit `2df143967509ff45584e261a2a033687346d654b`.
- `data/raw/provenance.jsonl` includes the original acquisition evidence. Initial guessed Transfermarkt release URLs returned 404; the actual pinned Git blobs were successfully read instead. No synthetic replacement was used.
- `pyreadr` reads the RDS files. The older transfer file needs the supported `rdata` parser with Latin-1 default decoding; original bytes are unchanged. The mapping has legacy non-UTF-8 text; only ASCII source IDs are used as identifiers, not decoded display names.

```bash
cd tfm_futbol
.venv/bin/python -m pip install -r requirements-archives.txt
.venv/bin/python -m scripts.worldfootballr_archive --download
.venv/bin/python -m pytest -q
```

Existing cached files are checksum-verified; missing files can be downloaded from their published URLs. A changed release checksum is an explicit error, not permission to change the expected checksum. No R installation or rewrite of the Python project is required. Provider rights are not granted by the package's GPL software license; keep the archive/derived tables as local research material until redistribution rights are established.

## Current model state

The Streamlit application and MLflow run still use the previous explicitly unverified 420-row legacy dataset. This trial has **not retrained the model** or manufactured new evaluation results. It has substantially improved the available data and provided a safe, period-audited candidate table. Integration must respect source-specific identities, partial seasons, missing category coverage and dated valuation knowledge before retraining or retrospective validation.

Full per-source/league/season/category counts: `reports/worldfootballr_coverage.csv`. Period mismatches: `reports/worldfootballr_merge_audit.csv`. Decoded schemas/counts and identity-map checks: `reports/worldfootballr_inventory.json`. Tests for the checksum and exposure safeguards are in `tests/test_worldfootballr_archive.py`.
