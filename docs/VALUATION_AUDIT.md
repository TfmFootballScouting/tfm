# Recorded values: identity and date audit

Recorded values take priority over estimates when their player identity and date are suitable for the scenario. This offline audit separates available monetary amounts from eligible historical budget attachments. It uses only retained files, without downloading data, training a valuation model, generating estimates or altering the existing source tables/models.

## Available amounts and provisional season context

The Transfermarkt archive has **2,018 rows for 1,125 source identities**, with **1,925 nonmissing amounts** and 93 missing amounts. Its raw R object and normalized records contain no valuation effective dates or historical known-at dates. The available date-related fields are `season_start_year`, `player_dob`, `date_joined` and `contract_expiry`; these describe seasons, births, club joining and contracts, rather than valuation dates.

| Season label | Source rows | Source people | Nonmissing amounts | FBref player-seasons with provisional nonmissing value context | Eligible historical budget attachments |
|---|---:|---:|---:|---:|---:|
| 2020/21 | 734 | 716 | 703 | 491 | 0 |
| 2021/22 | 784 | 765 | 723 | 507 | 0 |
| 2022/23 | 500 | 500 | 499 | 387 | 0 |
| 2023/24 | 0 | 0 | 0 | 0 | 0 |
| 2024/25 | 0 | 0 | 0 | 0 | 0 |
| 2025/26 | 0 | 0 | 0 | 0 | 0 |

These are season-labelled source records, not proved as-of historical prices. Provisional context matches source person and season, without reviewed identity approval or historical price eligibility. There are 73 rows in repeated person/season groups, reflecting multiple club records; their nonmissing amounts do not conflict within person/season. No arbitrary first/max price creates dated valuation events. Complete historical Segunda valuation coverage remains absent for all six requested seasons.

## Explicit current dates recovered

The earlier profile parser omitted `.data-header__last-update`. Six retained profile/history/transfer-page headers corroborate **two current values**:

| Source player | Recorded source market assessment | Explicit header update date | First retained header observation |
|---|---:|---|---|
| Lamine Yamal, ID 937958 | €220,000,000 | 2026-07-22 | 2026-10-10 15:12:17 UTC |
| Andrei Rațiu, ID 527966 | €24,000,000 | 2026-10-05 | 2026-10-10 15:12:27 UTC |

These amounts are quoted from retained headers, not project estimates or agreed transfer fees. They agree with the corresponding retained current-market sample amounts. Three pages corroborate each value; repeats are not six price changes. A current header on a market-history URL does not constitute a dated historical series. The retained graph components have no extracted historical series; no client endpoints are requested.

`valuation_date` records the explicit header update date; `valuation_known_at` conservatively records the earliest retained observation of that dated header. A July update does not prove our pipeline had the evidence in July. Both update dates follow the final requested season cutoff, 2026-06-30, and both were observed in October 2026. Neither supports any target season-end budget scenario. Current dates are saved separately and never backfill archived player-season records.

## Identity evidence

The latest archive matching trial contains **803 high-support proposals**, 122 pairs requiring review and 38 conflict pairs. Of the supported proposals, **781** combine exact normalized names, birth-year agreement and the pinned upstream ID mapping. These are evidence counts, not measured matching accuracy or independent human verification. A review queue is exported without creating approvals.

The two dated current profiles have unique normalized-name/birth-year candidates:

- Lamine Yamal → `fbref:82ec26c1`, birth year 2007, FBref Barcelona observations in 2022/23–2025/26.
- Andrei Rațiu / Andrei Ratiu → `fbref:b1b99435`, birth year 1998, FBref Rayo Vallecano observations in 2023/24–2025/26.

FBref supplies birth years, so this is not an exact full-DOB match. Both remain `provisional_not_reviewed`. Current profile evidence observed in 2026 is not historical as-of proof. Rațiu's requested Segunda-page context also demonstrates that a requested league URL does not establish current league membership.

## Conservative recorded-value import

`src/data/valuations.py::select_recorded_values` prepares a future import route requiring source/canonical person IDs, record ID, finite nonnegative EUR amount, effective/known-at dates, reviewed identity status/time, and explicit use authorization evidence. All applicable dates must precede the decision cutoff; effective dates cannot follow observation dates. Strict mode also requires identity review by the cutoff and does not assert a later review was historically available.

It preserves missing amounts, excludes unknown/future dates and unreviewed links, and selects the latest eligible observation per canonical person. Conflicting values on the same effective date or non-one-to-one identity assignments require review. Existing source-use guards apply; no authorization changed in this audit. It does not generate heuristics, confidence intervals or fees, or treat missing prices as zero.

## Reproduce and inspect

From the repository root, use the existing Python 3.12 environment with retained snapshots present:

```bash
.venv/bin/python -m scripts.valuation_audit
.venv/bin/python -m pytest -q --junitxml=reports/valuation_audit_tests.xml
.venv/bin/python -m scripts.verify_valuation_audit
```

No new dependencies, network access or folder hierarchy are required. Missing or changed provenance evidence causes an explicit failure. New tables remain in `data/processed/real/`:

- `collected_valuation_record_audit.parquet`: 2,068 archive/current records with amount/date/identity/use checks and independent blocking reasons.
- `collected_valuation_header_evidence.parquet`: six replayable raw-header observations with URLs, hashes and source restrictions.
- `collected_dated_valuation_evidence.parquet`: two consolidated current observations and corroborating hashes.
- `collected_current_value_identity_candidates.parquet`: two provisional current-profile proposals.

Reports stay in `reports/`. `valuation_audit.json` records dataset/code/Git versions, tags and hashes; `valuation_audit_dictionary.csv` describes every new field. CSV reports cover records, source/league/season coverage, target cutoffs, raw date fields and identity review.

`valuation_audit_verification.json` verifies **171 preserved source/evaluation/notebook/model files**, **13 outputs**, replay of six headers and **68 passing tests**, with zero failures/errors/skips. Historical cutoff selections remain empty. Existing raw data, source tables, identity proposals, recommendation models, notebooks and application data remain unchanged.

Completed: offline amount/date/identity audit, two recovered current dates, coverage/review reports, safe import selection, dictionary and verification. Partial: proposed matches and current-value context. Missing: dated historical series, independently reviewed links and eligible use authorization. No estimated prices, transfer success or valuation prediction accuracy are claimed.
