> Update, 11 October 2026: published worldfootballR archives now provide additional historical data without crawling provider sites. See [archive trial](WORLDFOOTBALLR_TRIAL.md) and `reports/worldfootballr_coverage.csv`. The original direct-access results and first-submission model below remain valid for their stated scope. No model retraining is claimed by the archive trial.

# Source access, coverage and provenance

Observed 10 October 2026. Coverage is in `reports/source_coverage.csv`: source × league × season × statistical category. Target seasons are 2020–2021 through 2025–2026, not evidence that every source has these seasons.

## FBref

The source `robots.txt` request returned HTTP 403 after the cloud domain was allowed. Its current crawl policy could not be established. The collector conservatively stops before league requests. The 72 statistical coverage cells are blocked at a shared prerequisite; they are not 72 failed player-table downloads. The first collector version rechecked the denied policy unnecessarily; the denial is now cached for the entire run. All response evidence is preserved; no control was bypassed.

The original repository commit `2cf3385cd8f3ddd41cbc608a5942564cba03100c` contains `data/raw/players_raw.csv`: 609 `fbref_cache`-labelled observations (La Liga 2023/24) and 840 `demo` rows. Original HTML, retrieval date and source player IDs are missing. The CSV/Parquet are unchanged. The original loader assigned shooting/misc rows by index, so those columns are discarded for exploration. Source identity inferred from legacy name/nation is local and unverified, never an automatic cross-source match. This subset is **not final validated real-data evidence**.

## Understat

`https://understat.com/robots.txt` returns `User-agent: *; Disallow: /`. No league pages are requested and no stealth browser is used. Six La Liga season cells are blocked by this policy; Segunda is explicitly unavailable. Obtain permission or an authorized export before further collection. The parser supports embedded `playersData` JSON where allowed; the current Breakout browser technique is not used to bypass restrictions.

## Transfermarkt

Observed robots policy permits the checked paths. Twelve season-labelled first-page market listings and a representative profile/valuation/history sample are preserved by SHA-256 under `data/raw/sources/transfermarkt/`, with URLs and retrieval timestamps in `data/raw/provenance.jsonl`.

The requested 2020/21 league page contains current players, e.g. Lamine Yamal with a current value and age. Thus a historical season URL does **not** prove a dated historical value or historical club membership. Normalized `current_market_sample.csv` has 25 first-page rows per league (50 total), NULL effective season and valuation date, and `temporal_scope=current_snapshot_not_historical`. This is a biased top-value sample, not complete league data. Two current profiles have parsed DOB, position, nationality, height and foot; they are not historical state.

The sampled market-value-history and transfer-history pages contain client-rendered components rather than dated records in the saved HTML. Those raw pages are retained, but no historical valuations, transfer dates or fees are inferred. `reports/transfermarkt_sample_access.csv` distinguishes parsed profiles from unparsed raw histories. The full historical source/league/season coverage remains unverified. Full pagination, historical chart ingestion and dated transfer/fee parsing are pending, not completed.

## Permissions and licensing

Robots permission is not a dataset redistribution license. Breakout has an MIT **software** license, which does not license provider datasets. The raw pages here are local research evidence with attribution, not an unrestricted licensed football dataset. Confirm provider terms and obtain authorized exports/permission before wider redistribution or commercial use. No login, CAPTCHA, user-agent rotation, stealth/UC mode or 403/429 retries are used. A fixed academic user-agent, current robots checks, at least three seconds between uncached requests per host, TLS verification and content-addressed caches are enforced.

## Reproduce or resume

From the repository root, after dependency setup:

```bash
.venv/bin/python -m src.scraping.collect
.venv/bin/python -m scripts.transfermarkt_snapshots
.venv/bin/python -m src.pipeline
```

Default training fails if no collected football statistics exist. It never substitutes synthetic data. Repeated requests reuse checksum-verified successful snapshots after the current robots check. The sample script parses existing preserved league responses and requests only two representative players' permitted endpoints. If an endpoint is denied, wait for a meaningful permission/policy change rather than bypassing it.

A separately labelled preliminary workflow is available with `--legacy-exploratory`; it is explicit, not a fallback. It must not be presented as a successful final real-data experiment.
