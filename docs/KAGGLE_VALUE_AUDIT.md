# Uploaded Kaggle valuation archive audit

Candidate: [Football Transfer Value Intelligence 2024](https://www.kaggle.com/datasets/kanchana1990/football-transfer-value-intelligence-2024). The user supplied `archive.zip` after the cloud proxy blocked Kaggle. No new network download or attachment-supplied instructions were executed. Kaggle version, publication metadata and licence are not supplied or independently verified.

## Contents and consistency

The 190,228-byte ZIP SHA-256 is `edb88617d152526f042e2ede9992a86ae58518a2953baf6117bcba1e5cc5b3fd`. Four members contain a 34-field dictionary, a 508-row/36-column summary in CSV and Parquet, and a 9,764-row/8-column valuation history. Summary versions agree after string-ID and empty-nationality normalization with numeric tolerance 1e-12. There is no README, licence, scraper or upstream snapshot. Provider authenticity remains uploader-declared rather than independently verified.

Both summary/history have 508 source identities, no orphan history IDs and no duplicate player/date keys. Summary point counts and peak amounts reconcile with all history records. `data_source` declares Transfermarkt.com. The declared build date is **2026-02-21**, not 2024; last summary assessments span 2025-12-01 to 2026-02-10. Current amounts equal last history amounts. No transfer-fee or performance-statistics table exists.

## Coverage

Current league listings: La Liga 104, Premier League 103, Serie A 101, Bundesliga 100, Ligue 1 100. **No Segunda listing exists.** Unknown selection and near-100-per-league counts preclude complete-league claims. History clubs can include former second-division clubs, but that does not establish historical Segunda membership or coverage.

The 104 La Liga-listed people have 1,964 history records across all years. Counts below use reported history dates in July–June windows and refer to currently listed people, **not verified historical La Liga membership**:

| Window | History rows | Source players |
|---|---:|---:|
| 2020/21 | 246 | 73 |
| 2021/22 | 212 | 78 |
| 2022/23 | 260 | 91 |
| 2023/24 | 303 | 101 |
| 2024/25 | 302 | 103 |
| 2025/26, partial | 145 | 104 |

`reports/kaggle_value_coverage.csv` lists all six windows for each listing, including zero Segunda rows. It also gives separate counts under the one-day-earlier date hypothesis; boundary observations can change season windows.

## Quality, temporal and identity findings

- **508/508 position fields contain euro prices**; all groups are `Other`. Positions are quarantined.
- **501 current-club fields equal nationality**, with seven missing nationalities. The entire current-club field is quarantined; peak club is not substituted for current club.
- All history dates parse as DD/MM/YYYY, spanning **2009-05-27 to 2026-02-11**. Every person's first and last history dates are **one day later** than summary dates. Each peak amount is also found one day later than its summary peak date. Redundant month/year fields disagree in **234 rows**, including **24 year disagreements**. Subtracting one day reconciles all redundant month/year fields. This suggests a systematic conversion problem, but its mechanism and authoritative date are unverified. Preserve both dates and label the offset as a hypothesis; operational effective dates stay null.
- **138 `is_at_peak` flags disagree** with current/peak amount equality despite the dictionary's definition. Retain uploader-derived features as evidence, not trusted predictors.
- Six history amounts are reported zero with unverified semantics, not transfer fees. Seven current ages are missing. Unknown values are never replaced by synthetic data.
- Career peaks, growth, trajectory, volatility, decline and current age/league incorporate future information relative to historical decisions. Keep these summary fields out of historical predictors. Build/inspection dates do not establish historical public availability.

Upstream mapping supplies **130 candidate pairs for 129 uploaded source people**, including **94 La Liga-listed people**. One source ID has multiple FBref candidates. **110 source identities** have normalized-name agreement, retained-history club overlap and no candidate ID ambiguity. These checks use all retained dates; they are neither as-of evidence nor measured matching accuracy. No DOB is supplied by this upload. All candidates remain provisional and unreviewed.

A separate packet overlaps 61 earlier proposals (48 La Liga-listed); 60 agree with a normalized name alias. Candidate packets overlap and their counts must not be summed. No identity approval or use authorization is created. Existing Transfermarkt restrictions remain for its Kaggle copies. **Zero uploaded records currently qualify for historical budgets or model use.**

## Saved data and commands

The original ZIP, four raw members and first inspection receipt stay in ignored `data/raw/sources/kaggle_transfer_values/`. Five separate `collected_kaggle_value_*.parquet` tables use existing `data/processed/real/`: `profiles`, `history`, `summary_consistency`, `identity_review`, `upstream_identity_candidates`. These provider row tables are ignored by Git because no redistribution licence was supplied; they are retained locally. Existing datasets, fitted models, app data and notebooks are preserved.

`reports/kaggle_value_dictionary.csv` defines every field in all five tables. Corrupt profile fields are preserved beside null `position_clean`/`current_club_clean`. History retains raw strings, parsed reported dates and explicitly named `valuation_date_one_day_earlier_hypothesis`. Operational `valuation_date` remains null; `valuation_known_at` is first local inspection, and `source_publication_known_at` remains unknown. All use/eligibility flags are false.

From the repository root:

```bash
.venv/bin/python -m scripts.kaggle_value_audit
.venv/bin/python -m pytest -q --junitxml=reports/kaggle_value_tests.xml
.venv/bin/python -m scripts.verify_kaggle_values
```

The audit defaults to the retained pinned ZIP. If absent, use `--uploaded-archive /path/to/archive.zip` with the exact uploaded bytes; checksum changes fail. No automatic download or substitute data occurs. **74 tests passed with zero failures/errors/skips.** Verification replays transformations and checks source/output/old-input/code hashes and test evidence. Reports: `kaggle_value_audit.json`, `kaggle_value_verification.json` in `reports/`.

Completed: preserved upload, executed quality audit, separate normalized evidence, source/listing/season coverage, full dictionary, candidate review packets, regression checks. Partial/blocked: authoritative dates, historical availability, provider licence, identity approval, complete league coverage and independent authenticity. No valuation model was trained and no historical transfer validation is claimed. Recommendation-model Streamlit integration remains pending separately.
