# Verification of reported player valuations

Verification was executed offline against the retained original uploads and two saved primary-source profile pages. No new provider downloads, automated identity approvals, estimated values or model refits were performed.

## Completed checks

- Verified original upload and retained history payload checksums.
- Compared **all 901,429 normalized valuation records** one-to-one against raw player ID, effective date and amount. No rounding, scale conversion, duplicate key or missing/extra normalized record was accepted.
- Checked finite, nonnegative amounts, unique player/date keys and effective dates no later than receipt.
- Counted **853,420 positive** records and **48,009 ambiguous zero** records. A zero does not establish a free player or a zero transfer fee.
- Checked whether valuation source IDs have an uploaded profile.
- Corroborated source identity proposals against same-season club histories from the retained global performance upload, using five source league IDs and conservative club-name normalization.
- Reparsed two retained primary Transfermarkt profile snapshots, checking their hashes, canonical player IDs, page titles and dates of birth against uploaded profiles. Lamine Yamal and Andrei Rațiu have matching uploaded full birth dates. These pages were retained in 2026; they do not verify older market-value amounts or original publication times.

## Identity findings

There are **5,405 proposed pairs**, of which **4,869** pass the previously defined source-ID/name/birth-year agreement checks:

| Status | Pairs | Meaning |
|---|---:|---|
| Supported plus matching club-season history | 1,650 | Stronger secondary evidence; still provisional. |
| Supported, club evidence unresolved | 3,219 | No matching retained club-season spelling/context was established. This is not automatic rejection. |
| Original matching evidence conflicts or is ambiguous | 536 | Excluded from supported matching; retain for investigation. |

Two current primary profiles corroborate uploaded names/IDs/full birth dates. FBref does not independently supply verified full dates of birth for these matches. **No complete cross-source identity was automatically approved.** The review queue records evidence per pair without weakening source/model-use guards.

## What remains unverified

**Currency:** raw `player_market_value.csv` contains only `player_id`, `date_unix` and `value`. The previous normalizer labels amounts EUR, but the file contains no explicit currency or per-row unit evidence. Amount round-trip verification proves accurate copying, not that the source amount is euros. App captions now disclose this EUR assumption. Do not treat these as verified euro budgets until source documentation or primary valuation evidence confirms units.

**Primary valuation evidence:** none of the 901,429 historical amounts/effective dates was independently confirmed against an exact primary valuation entry. Current primary profile values cannot verify older amounts.

**Publication time:** there are **zero known original publication timestamps**. Effective valuation dates and local receipt dates are different concepts. All records remain ineligible for a claim of historically known budgets. Verifying historical availability requires an archived primary valuation entry showing amount, currency, effective date and publication/observed-at evidence before the decision cutoff.

**Interpretation:** these are reported market assessments, not transfer fees, wages, agent fees or total signing costs. No fee was inferred from a market value.

The retained inputs cannot resolve these missing facts by computation alone. Source access restrictions remain enforced; absence of evidence is not an approval.

## Outputs and reproduction

Run `python -m scripts.verify_reported_valuations` from the repository root with retained private uploads and optional archive dependencies available. Then run:

```bash
python -m pytest -q tests/test_reported_valuation_verification.py tests/test_budget_screening.py tests/test_collected_app.py tests/test_scouting_scenarios.py
```

Public aggregate evidence is in `reports/valuation_verification/verification.json`, `date_coverage.csv`, `record_dictionary.csv` and test XML. Input/code hashes and the source Git commit are recorded. The report explicitly records a dirty source checkout during this new audit; it does not misrepresent a clean training run.

Private row-level outputs remain ignored:

- `data/processed/real/valuation_verification_records.parquet`: amounts/dates and explicit unresolved verification flags.
- `data/processed/real/valuation_verification_identities.parquet`: per-pair source, name, birth-year, club-season and primary-profile evidence.
- `reports/valuation_verification/identity_review_queue.csv`: review evidence, including retained primary snapshot hashes where available.

Original raw uploads, normalized tables, identity candidates, experiment outputs, trained models and earlier reports remain unchanged. These audit tables are rejected by the existing model-use guard. Existing optional price screening remains provisional; no verified valuation status is claimed.

Validation: **13 relevant verification, budget, app and scenario tests passed**, with no failures, errors or skips. All 335 protected earlier artifacts, critical training source hashes, four current pipeline datasets and three model hashes were checked unchanged.
