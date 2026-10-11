# Uploaded player and transfer histories

The two uploaded ZIPs are retained byte-for-byte locally under `data/raw/sources/salimt_uploaded/histories/`, with extracted CSV payloads, original file IDs, first receipt time and SHA-256 checksums. No attached code was executed, no downloads were substituted, and prior audited datasets and trained models were preserved. Source repository/version and provider licence for these uploaded bytes remain unverified.

## Actual coverage

The performance file contains **1,878,719 global rows**. The six target seasons contain **8,252 La Liga/Segunda player–club–season records**, **2,993 distinct source players**, and **402 player-seasons spanning multiple clubs**. All twelve league-season combinations contain records: 20 La Liga clubs and 22 Segunda clubs each year. There are no exact duplicates or duplicate `(player_id, season, competition_id, team_id)` keys in this target subset. Season-level club records remain separate; no unsafe summing across clubs or competitions is performed.

The transfer file contains **1,101,440 global rows**, including **365,957 records** in the six target seasons worldwide. This is not a count of Spanish transfers. Historical Spanish club-season membership is joined separately on `(source club ID, season)` for origin and destination; one event may have multiple contexts. Context coverage counts distinct original rows, not duplicated context rows. The target transfer subset contains **37 exact duplicate rows**, retained and flagged in the report, and **15,513 distinct player IDs absent from the uploaded profile table**. These unmatched events cannot be attached to profiles by an unsafe inner join.

## Limits and preprocessing decisions

2025/26 is a partial snapshot. Missing minutes prevent reliable per-90 calculations for affected records. Source strings, missing values, reported zero fees and transfer types are preserved; zero fees do not automatically prove a free transfer. Fee/value currencies and event types need validation before valuation experiments. Shots, shots on target, crosses, interceptions, tackles won, fouls committed/drawn, xG and xAG are absent from the actual headers. This source supplements the FBref performance base; it cannot support all six playing styles alone.

Unsupported season labels, including calendar-year formats from other leagues and missing values, are counted with their exact labels in the audit. They are excluded from the supported Spanish YY/YY season selection, rather than treated as fabricated seasons. Original raw rows remain available for later handling.

Source player IDs permit joins within the uploaded Transfermarkt tables, but existing FBref mappings remain unreviewed. No cross-source approvals, model retraining, estimated prices, transfer-success metrics or historical budget eligibility are created by this audit. Original publication dates are unknown; full-season histories cannot be used as preseason information. Genuine reported transfer events are available for later historical validation design, but no outcome validation has yet been executed.

## Reproduce and inspect

From the repository root:

```bash
.venv/bin/python -m scripts.salimt_history_audit
.venv/bin/python -m pytest -q --junitxml=reports/salimt_history_tests.xml
```

First receipt uses `--transfers <uploaded ZIP path> --performances <uploaded ZIP path>`. Subsequent executions use checksum-verified retained raw files. Large raw/normalized provider rows remain ignored by Git; a fresh machine needs the retained snapshot or the same uploads.

Reports: `salimt_history_audit.json`, `salimt_history_coverage.csv`, `salimt_history_field_coverage.csv`, `salimt_history_dictionary.csv`, and the executed test XML. Earlier audit documents are historical evidence: their TXT-size blocker has now been resolved by these ZIP uploads.

Completed: raw preservation, actual coverage, source-separated history subsets, historical club-context joins, field quality/dictionary and tests. Partial: semantic cleaning and identity integration. Pending: reviewed cross-source joins, reliable per-90 features, fee semantics, historical availability checks and transfer-outcome validation. Provider-use authorization remains unresolved for model consumption.
