# Transfer-likelihood feasibility and label audit

Run on the full research branch:

```bash
python -m scripts.transfer_label_audit
python -m pytest -q tests/test_transfer_label_audit.py
```

The audit performs no model fitting. It preserves raw data, verifies input identities at the supported-proposal level, and keeps unknown outcomes separate from non-transfers. Provider source-use restrictions remain in force; none of these cases are authorized training inputs.

The prediction question is: **at 30 June of a season, will this player have a reported permanent club-to-club transfer during the next 12 months?** This first audit uses the existing five-league core gallery from 2020/21 through 2023/24 (7,394 player-season cases). The four sparse 2024/25 gallery rows are excluded. Loans, loan returns, drafts, retirement, becoming unattached, and unknown destinations are not permanent club-to-club transfers. Missing dates and source season/date conflicts are not accepted as positive-event evidence pending review.

Inputs:

- `data/processed/real/five_league_pipeline_core_gallery.parquet`: FBref baseline cohort.
- `data/processed/real/europe_review_candidates.parquet`: provisional source-ID proposals supported by normalized name and birth-year agreement.
- `data/processed/real/collected_salimt_transfer_history.parquet`: audited user-uploaded Transfermarkt-derived events, filtered previously to source-labelled target seasons. This is not proof of complete global history or complete individual follow-up.
- Original history: `data/raw/sources/salimt_uploaded/histories/transfer_history.txt` and its ZIP. Raw rows remain unchanged.

Outputs on the research branch:

- `reports/transfer_likelihood/label_audit.json`: definitions, exact input hashes, script hash, base Git commit, counts and blockers.
- `reports/transfer_likelihood/label_coverage.csv`: aggregate label availability by season and league.
- `reports/transfer_likelihood/event_quality.csv`: event types and date-quality counts.
- `data/processed/real/transfer_likelihood_label_candidates.parquet`: local per-player review cases; not used to fit models.
- `notebooks/14_transfer_likelihood_feasibility.ipynb`: executed interpretation of the aggregate audit.

Current results:

| Status | Player-season cases |
|---|---:|
| Reported permanent-transfer candidate, pending review | 1,726 |
| No recorded qualifying permanent transfer; follow-up unknown | 5,036 |
| Identity unmapped | 632 |
| Total | 7,394 |

`observed_positive_candidate` is 1 only when there is qualifying reported evidence, otherwise missing. `verified_binary_target` remains missing for every case. We do **not** encode the 5,036 unknown cases as zero. Identity links are provisional; `model_use_eligible` remains false. Positive candidates are not independently confirmed transfers. Cases span multiple seasons, so these counts are not distinct-player counts.

The 365,957 target-season event rows become 365,920 distinct event identities after deduplication. There are 134 missing/unparseable dates and 2,282 source season/date conflicts. Some conflicts are plausible June/July boundary assignments, not necessarily incorrect transfers. Their exclusion is conservative and must not be interpreted as proof that no transfer occurred.

Before training:

1. Establish permitted use of the event source for model training.
2. Review cross-source identity links and conflicting event dates.
3. Establish full follow-up for each proposed negative using a documented, sufficiently complete registration/transfer source. Seeing a player at the same club later does not exclude an intervening move and return.
4. Resolve the permanent-transfer definition, including special club-name/ID placeholders and contract-boundary events.
5. Freeze features at the prediction date. Do not use destination, fee, later club, future performance or future valuations. Original publication dates are unknown; dated values alone cannot establish historical knowledge.
6. Count reliable positive/negative examples by prediction year and league. Only then design chronological training, validation and holdout windows and confirm adequate sample sizes.

Planned evaluation, not executed: historical-rate baseline, logistic regression and gradient boosting; chronological model selection; PR-AUC, shortlist precision/recall, Brier score and calibration; player-block uncertainty estimates and league/position slices. No forecast accuracy or transfer probability is claimed by this audit.

The minimal branch continues to serve the existing recommender. Its scenario-page removal and budget filter are unaffected. The full audit code, notebook and aggregate outputs remain on `improve/reproducible-scouting`.
