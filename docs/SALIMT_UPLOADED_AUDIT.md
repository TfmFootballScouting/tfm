# Uploaded salimt files: executed audit and review-only integration

Four user uploads were transferred and preserved on 11 October 2026: `team_details.csv`, `team_competitions_seasons.csv`, `player_market_value.csv`, `player_profiles.csv`. The original bytes, file IDs, sizes, SHA-256 checksums and local UTC receipt are retained under ignored `data/raw/sources/salimt_uploaded/`. The uploaded bytes have not been verified against an exact GitHub commit. No licence was supplied. This is offline inspection of retained evidence, with existing provider-use restrictions preserved.

The `transfer_history.txt` and `player_performances.txt` uploads both exceed the executor's **32 MiB transfer limit**. They could not be inspected for CSV content, LFS pointers or coverage. Renaming alone does not change size. Provide individually compressed ZIPs under the limit or CSV parts split on complete records with the same original header in each part. No downloads, invented statistics or substitute rows fill these gaps.

## Measured contents

| Table | Actual records | Additional facts |
|---|---:|---|
| Profiles | 92,671 | Unique source IDs; 1,006 missing DOBs |
| Value history | 901,429 | 69,441 people; dates 2003-12-14 through 2025-09-11 |
| Team details | 2,175 | Unique club IDs |
| Team/competition seasons | 58,247 | 252 target Spain team-season rows |

The actual value/season counts differ from the README's advertised 901,457 and 196,378. Do not substitute advertised totals for measured counts or assume a reason for the differences. Profile columns also differ from the README example; normalization uses the actual uploaded schema.

## Spain coverage

For **each** season 2020/21 through 2025/26, the actual competition IDs `ES1` and `ES2` identify **20 La Liga clubs and 22 Segunda clubs**, respectively. Team-season primary competition/season fields agree with their nested league fields. Target Spain club/competition/season keys have no duplicates.

For 2020/21–2024/25, the team-season tables report 38 matches per La Liga club and 42 per Segunda club. For 2025/26 they report only 8–9 and 9–10 matches, respectively: these are partial snapshots. Team counts are measured from supplied records; no independent roster/completeness validation is claimed. Global raw history has 360 exact duplicate rows and 371 repeated club/competition/season keys. These remain in the raw file and do not affect the validated target-season subset.

**Segunda is now present at team-history level. This does not establish player-performance coverage.** Player profiles contain current club context; valuation rows contain no historical club/league. Do not assign all past prices to a player's current league. `reports/salimt_uploaded_coverage.csv` separates team evidence, unassigned global valuation events, inaccessible performance/transfers and unknown historical profile/price league coverage. Missing/uninspected categories have blank counts, not fabricated zero coverage.

## Normalization and identity join

- Source person IDs remain Transfermarkt IDs. A profile's trailing `(ID)` name annotation is removed only when it matches that row's ID; raw names remain preserved.
- DOBs are strict ISO dates and support birth-year comparisons. They are not valuation dates or proof of historical source availability.
- Uploaded height is numeric **centimetres**, not the metres in the older README prose. **18,867 zero heights** become unknown in `height_cm`, with original numbers retained in `height_raw_cm`. Unknown foot/position remain unknown.
- Value `date_unix` is actually ISO calendar text. It parses into an uploader-reported `valuation_date`; no epoch conversion or invented season date is used. The 48,009 numeric zero amounts remain explicitly reported zeros with unverified semantics. EUR follows repository schema; values are market assessments, not transfer fees or model estimates.
- Original source-publication time is unknown. `valuation_known_at` is conservative first local receipt in October 2026, not an inferred 2020–2025 public timestamp. No price is eligible for historical budget attachment.

The retained upstream ID map produces **1,317 candidate pairs** against our FBref people. **1,119 pairs** have exact normalized-name alias agreement, consistent birth-year agreement and no source/FBref ID ambiguity. Six birth-year conflict pairs are retained and excluded from the supported subset. These are review candidates, not approvals; no identity accuracy is measured.

The new `collected_salimt_identity_join_preview.parquet` left-joins only those supported profile candidates to existing FBref `entity_id`, preserving all **3,378 player-season rows**, their observation/person IDs and seasons. It attaches source-prefixed profile evidence to **2,779 rows**. Multiple seasons remain separate observations of the same person. Current club attributes are explicitly source-prefixed and never replace historical FBref clubs. Original FBref performance, prices and budget fields remain unchanged. No prices are backfilled or inferred from current profiles.

All joined identities remain `provisional_not_reviewed`. The preview preserves Transfermarkt attribution and `restricted_pending_explicit_license`, with model-use flags false. Existing fitting/transformation guards reject it. Independent identity review, applicable source-use authorization and actual historical availability are required before final enrichment/model/budget use.

## Corroboration of the earlier Kaggle date issue

Matching source person IDs, the earlier Kaggle **reported dates have zero exact-date matches** to this upload. Its clearly labelled one-day-earlier hypothesis produces **8,887 equal-date, equal-amount matches across 491 people**. This strongly corroborates the systematic offset interpretation. Both copies derive from Transfermarkt, so it is not independent provider validation or proof of public availability. The previous Kaggle tables, original date strings and frozen audit reports are preserved unchanged; this new comparison is in `reports/salimt_uploaded_date_corroboration.csv`.

## Files, execution and verification

Six locally retained/ignored tables use existing `data/processed/real/` with `collected_salimt_` names: `profiles`, `values`, `team_details`, `spain_team_seasons`, `identity_candidates`, `identity_join_preview`. Row-level provider content remains local because no redistribution licence is supplied. Raw CSVs stay unchanged. `reports/salimt_uploaded_dictionary.csv` defines every new output field, including source prefixes and evidence status.

After initial receipt, run from the existing repository root:

```bash
.venv/bin/python -m scripts.salimt_uploaded_audit
.venv/bin/python -m pytest -q --junitxml=reports/salimt_uploaded_tests.xml
.venv/bin/python -m scripts.verify_salimt_uploads
```

First receipt on a machine without retained files requires all four `--team-details`, `--team-competitions-seasons`, `--player-market-value`, `--player-profiles` paths. A partial argument set, missing inputs, LFS pointers or changed checksums fail. No new dependencies, network collection, model training or synthetic fallback is used.

**82 tests passed, zero failures/errors/skips**, including actual-row unit/date semantics, duplicate/missing/future/negative valuation rejection, multi-season grain preservation, unchanged prices, source-use rejection and conflict handling. Verification replays normalized profile/value tables, checks four raw uploads, all prior input hashes and nine outputs, and verifies dictionary coverage and actual test evidence. Results: `reports/salimt_uploaded_audit.json`, `reports/salimt_uploaded_verification.json`.

Completed: four raw receipts, actual data quality/units, source separation, Spain team coverage, explicit partial-season status, profile review packets, season-aware review-only joins, date corroboration and regression verification. Partial: historical player/league membership and as-of budget evidence. Blocked/unverified: transfer/performance uploads, source authorization, human identity approval, complete tactical features and actual-transfer validation. Existing fitted models, MLflow artifacts, app data and notebooks are unchanged; recommendation-model Streamlit integration remains pending separately.
