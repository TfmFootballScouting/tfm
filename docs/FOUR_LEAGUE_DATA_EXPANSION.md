# Additional data for Premier League, Bundesliga, Serie A and Ligue 1

Four additional real Understat shot archives were downloaded from the published `JaseZiv/worldfootballR_data` GitHub release. Existing checksum-pinned FBref archives and retained uploaded Transfermarkt histories were also prepared into separate four-league tables. No provider website was crawled, synthetic data substituted, current recommender retrained or old dataset overwritten.

## New attacking data

| League | Shot records, 2020/21–partial 2025/26 | Distinct source players |
|---|---:|---:|
| Premier League | 49,970 | 1,051 |
| Bundesliga | 40,518 | 1,032 |
| Serie A | 48,673 | 1,160 |
| Ligue 1 | 43,777 | 1,240 |
| Total shot records | **182,938** | Player counts are league-specific, not globally deduplicated. |

The source includes shot coordinates, expected goals, shot outcome, minute, shot type, situation, match IDs/dates, home/away clubs, source player IDs, assisted-by names and last action. This provides the fields needed to begin shot maps and attacking-profile analysis for the added leagues. It does **not** approve a join to FBref identities.

Observed match coverage equals the expected league schedule in 2020/21–2023/24 for all four leagues and in 2024/25 for Premier League and Ligue 1. **Bundesliga 2024/25 has 305 of 306 match IDs; Serie A has 374 of 380.** The missing expected home/away pairings are documented in `missing_fixture_pairs.csv`; no dates, results or shot records were fabricated to fill them. Matching an expected match count does not independently prove every shot is present.

All 2025/26 shot sets are early snapshots, with 40 Premier League, 27 Bundesliga, 30 Serie A and 36 Ligue 1 matches. The release assets were last modified in September 2025; downloading them in 2026 does not update their contents to completed 2025/26 seasons.

## Richer FBref fields already available

Prepared all original columns from six categories rather than only the small feature subset used by the app:

- Standard and shooting: 12,891 player-club-season rows per table.
- Passing: 12,891 rows, including pass distances, short/medium/long passing, key passes, penalty-area entries and progressive-pass fields.
- Defense, possession and miscellaneous: 10,790 rows per table, including tackle/block zones, touches, take-ons and other retained source measures.

Tables use explicit source player IDs, league, season and club keys. Auxiliary exposure is checked against standard minutes, with `category_exposure_compatible` flags. Incompatible raw category values are retained for audit, **not declared usable full-season features**. Missing or stale advanced exposure remains a reason not to offer newer six-style app galleries.

## Recruitment context from retained uploads

Prepared review-only source tables:

- **462 club-season contexts**, covering the four leagues and six target season labels.
- **15,208 player-performance records** in those four league competitions.
- **20,316 transfer/club contexts**, matched to origin or destination clubs within the same season.

A transfer between two target clubs may generate two contexts; this is **not 20,316 unique transfers**. These records retain Transfermarkt IDs and raw reported transfer fields. No FBref identity approval, fee verification or historical publication-time proof is implied. Current profile attributes must not be represented as historical state. Source/model-use restrictions remain enforced.

## Files and reproduction

Source-separated parquet tables are retained locally under `data/external/four_league_expansion/`. Raw Understat bytes are retained under `data/raw/sources/understat_worldfootballr/`. They are ignored in Git: secondary publication does not establish a provider redistribution license, and uploaded context remains private.

Committed reproducibility evidence lives in `reports/four_league_acquisition/`:

- `understat_sources.json`: exact asset URLs, hashes, byte sizes, acquisition times, release headers and reader choice.
- `acquisition.json`: input/output hashes, row counts, source Git/code metadata and limits.
- `coverage.csv`: source × league × season × category coverage, exposures and match counts.
- `dictionary.csv`: source field names, types and missingness. Source field units are not silently unified.
- `missing_fixture_pairs.csv`: seven expected pairings absent from retained shot data.
- `access_attempts.json`: successful public GitHub route, blocked GitHub API route, and blocked official match-results-source access.

Install the standard dependencies plus `requirements-archives.txt`, then:

```bash
# Retained workspace, including private uploaded histories:
python -m scripts.four_league_acquisition

# Reproduce source archives without the private Transfermarkt uploads:
python -m scripts.four_league_acquisition --download --public-only
```

Downloads are checked against pinned hashes. A changed release asset is rejected rather than silently replacing expected hashes. Existing FBref/Understat raw files and original provenance manifests remain unchanged; the new collection has a separate manifest. Reader adaptations support the original R string encodings without editing source bytes, and resolve the source's alternate home/away fields without guessing missing teams.

## What is ready and what is next

The added leagues now have source-separated shot data and richer football-statistic tables suitable for a scoped EDA/coverage review. Player development can use existing FBref source identities; shot analysis can use Understat source identities. Combined player dashboards require conservative identity reconciliation between those sources. Recruitment analysis remains a separate restricted-source review. No new model metrics or transfer-success outcomes are claimed by this acquisition step.

Verification: **two real-data integration tests passed**, checking shot IDs, coordinates/xG, team-side resolution, partial coverage, restricted context tables, new output hashes and all 335 protected earlier artifacts. Input hashes and document links were also checked.
