# salimt/football-datasets: repository metadata inspection

Source: https://github.com/salimt/football-datasets, pinned HEAD `da9227e1f42baf74561324290dbf1ad2e3c00edd`, observed on 11 October 2026. The uploaded ZIP could not be transferred because it exceeds the executor's 32 MiB Sediment limit; its contents/hash are unverified. The GitHub repository is accessible with existing authentication/network settings. No additional secret or network change is needed for the metadata inspection.

## What was actually inspected

Read-only `git ls-remote`, pinned README/schema examples, the advertised licence URL, Git attributes and six category-directory listings. Eleven pinned HTTP responses are saved locally with status, URL, UTC observation time and SHA-256 under ignored `data/raw/sources/football_datasets_metadata/`. No repository checkout, full ZIP, provider CSV or new model was downloaded/created. Documentation examples were inspected; full CSV row counts and Spain/season coverage were not verified.

The README advertises 92,671 player profiles, 1,878,719 performances, 901,457 market-value observations, 1,101,440 transfer histories, 196,378 team/competition seasons and 2,175 teams. These are **publisher claims**, not counts measured by our pipeline. It describes Transfermarkt data rather than FBref/Understat measurements.

The actual pinned paths differ from the README's `/raw/` paths:

| Category | Confirmed repository path |
|---|---|
| Performance | `datalake/transfermarkt/player_performances/player_performances.csv` |
| Value history | `datalake/transfermarkt/player_market_value/player_market_value.csv` |
| Profiles | `datalake/transfermarkt/player_profiles/player_profiles.csv` |
| Transfers | `datalake/transfermarkt/transfer_history/transfer_history.csv` |
| Historical competitions | `datalake/transfermarkt/team_competitions_seasons/team_competitions_seasons.csv` |
| Teams | `datalake/transfermarkt/team_details/team_details.csv` |

Git attributes mark performance and transfer CSVs as Git LFS content. Confirming a path does not verify that its payload was obtained. Any later authorized acquisition must resolve actual LFS objects and reject pointers/HTML masquerading as CSV.

## Potential value for the TFM

- Profiles advertise source player IDs, names, DOB, position, foot and height, which could improve identity matching after actual field validation/review. Example names include `(player_id)` suffixes; names alone remain insufficient.
- Historical values advertise `player_id`, `date_unix` and `value`. Despite its name, the documentation example shows ISO calendar dates rather than Unix epoch numbers. Validate the actual file before parsing or assigning currency/publication time. Historical event dates alone do not prove availability before a decision.
- Transfers advertise player/transfer IDs, season, exact date fields, origin/destination club URLs, market assessment at transfer and transfer-fee text. Market assessments and fees must remain distinct. `-`, `free transfer`, loans and currency/scale require explicit parsing rules; missing fees cannot become zero.
- Performance advertises competition/season/team context, appearances, goals, assists, minutes, disciplinary and goalkeeper counts. This could supply basic Segunda observations **if actual competition IDs and seasons confirm them**. Global coverage and a current team division do not establish Segunda league-season coverage.
- Team-season history could establish league membership using actual competition IDs and seasons. It should replace guesses from a player's current club, not be used as proof until the relevant rows are inspected.

The advertised performance schema could derive goals/assists/G+A per 90 from validated exposure. It does **not advertise** shots, shots on target, crosses, interceptions, tackles won, fouls committed/drawn or xG/xAG. This source cannot yet be claimed to replace FBref/Understat or support all six tactical styles. Feature status is documented in `reports/football_datasets_feature_assessment.csv` as schema evidence only.

**La Liga and Segunda presence and every 2020/21–2025/26 source/category count remain unverified.** No complete league coverage, current-season completeness, valid valuation dates, clean identities or transfer-validation results are claimed.

## Actual blocker

The README links `LICENSE`, but that pinned URL returns **HTTP 404**; no root licence file was found in the inspected tree. A badge/link is not a verified licence. This is independent of technical GitHub access and the attachment size limit.

The existing `src/data/source_rights.py` guard rejects Transfermarkt repository data acquisition/model use pending a reviewed provider licence. `reports/source_rights.json` preserves observed terms section 11.1 restricting automated copying and AI/ML use. The guard was executed and raised `SourceUseRestricted`; it was not removed or bypassed for a GitHub mirror. Repository documentation inviting experiments does not establish upstream authorization. No assertion is made that a 404 alone establishes the complete legal status; authorization for our intended use remains unverified.

To proceed with acquisition/use, establish a reviewed licence or authorization applicable to the provider-derived dataset and intended work. A smaller local upload can be preserved and inspected as retained evidence, like the previous archive, while use restrictions remain explicit; that alone does not authorize model training. No messages to the publisher or provider were sent.

## Reproduction and completion

From the existing project root, run `.venv/bin/python -m scripts.football_datasets_inventory`. The command reads only fixed pinned metadata endpoints on first use, then verifies/reuses preserved local responses; it never follows data/provider links or downloads CSVs. No dependencies or service startup commands changed. `reports/football_datasets_assessment.json` records evidence, claims versus verified facts, source-use rejection and preserved input/output hashes. `reports/football_datasets_file_inventory.csv` lists the six actual paths.

Completed: GitHub connectivity, metadata/schema inspection, real file-path inventory, feature-gap assessment, precise licence/source-use blocker and old-input preservation. Partial: historical value/transfer/basic-performance potential. Blocked/unverified: provider acquisition/use, Spain/season coverage, identity joins, actual data quality, historical budgets and model/transfer evaluation. Existing datasets/models/notebooks are unchanged. Streamlit integration of our already evaluated FBref models remains pending separately.
