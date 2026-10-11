Latest pipeline: [cleaning, season-aware enrichment, EDA and eligible model reruns](ENRICHED_PIPELINE.md). New histories are integrated in a review dataset; three eligible FBref models were refitted. Transfermarkt fields remain excluded from fitting by the existing source and identity checks. Full dictionary: `reports/enrichment/dictionary.csv`.

Latest upload audit: [player statistics and transfer histories](SALIMT_HISTORY_AUDIT.md). Segunda player records are now confirmed for all six target seasons; advanced features and model integration remain incomplete. See `reports/salimt_history_dictionary.csv` for the new source-separated tables.

# Data dictionary and grain

## Uploaded salimt profiles, values and team history

`reports/salimt_uploaded_dictionary.csv` covers all fields in six isolated `collected_salimt_*` tables. Profile IDs are Transfermarkt person keys; value observation keys add the explicit ISO event date; Spain team-history keys add competition and season start year. Centimetre heights retain raw zero sentinels alongside null clean heights. Value dates are reported events, while known-at is first local receipt and original publication remains unknown. Values are EUR market assessments, not fees; explicit zeros retain unknown semantics. Review-only profile joins use the stable FBref `entity_id` across seasons and preserve FBref observation grain, with all source fields prefixed `salimt_`. Current clubs never become historical clubs and current prices never backfill earlier seasons. Source/mapping restrictions and provisional identity statuses remain. See [exact counts, key semantics and coverage limits](SALIMT_UPLOADED_AUDIT.md).

## Uploaded Kaggle valuation evidence

Five isolated `collected_kaggle_value_*` tables preserve the existing structure and datasets. `reports/kaggle_value_dictionary.csv` defines every field in `profiles`, `history`, `summary_consistency`, `identity_review` and `upstream_identity_candidates`. Source IDs are uploader-declared Transfermarkt person IDs, not approved canonical joins. Profile position/current-club fields are corrupt and retained alongside null clean fields. History `valuation_date_raw` is the original DD/MM/YYYY string; `valuation_date_reported` is its parsed form; `valuation_date_one_day_earlier_hypothesis` is an audit hypothesis, not a correction. Operational `valuation_date` is null because summary/history dates disagree. `valuation_known_at` records first local inspection only; original historical public availability is unknown. All use/budget eligibility flags remain false. League labels refer to current uploader listings, not historical membership. Review packets use unreviewed upstream mappings and all-retained-date club overlap, never final model features. Career/current summaries contain future information for historical decisions. See [executed audit and coverage](KAGGLE_VALUE_AUDIT.md).

**Legacy raw files** are preserved byte-for-byte. **Source snapshots** are immutable HTML (including failed policy responses), named by SHA-256. **Normalized source tables** remain separate. The current model uses only the explicitly unverified legacy FBref standard subset; it does not join Transfermarkt prices or Understat estimates.

An observation is one source entity × league × season × team. `player_id` identifies an observation, not a universal person. `entity_id` identifies a source-specific person. Source all-club totals are preferred over the same player's individual club stints to avoid double counting; raw stints remain available. Without a source total, stints are retained and must be aggregated before temporal evaluation. Names alone cannot resolve a cross-source identity.

## Canonical observations (`data/processed/real/players.*`, SQLite `players`)

| Field | Type/unit | Meaning / missing-value rule |
|---|---|---|
| player | string | Source display name, not an identity key |
| source | string | `fbref_cache` (legacy), `fbref`, `understat`; demo rejected |
| source_player_id | string | Provider ID; legacy name/nation-derived key is explicitly local/unverified |
| entity_id | string | Source + source player ID; no cross-source equivalence implied |
| observation_id | string | Entity/team/season/league key |
| player_id | integer | Stable 52-bit SHA-256-derived observation key; collisions rejected |
| team | string | Reported team or source aggregate `N squads`; never infer transfer dates |
| league | string | La Liga or Segunda; source-specific coverage reported separately |
| season | YYYY-YYYY | Consecutive years; denotes entire season, not availability on a decision date |
| pos | string | Source position; canonical FW/MF/DF/GK, optional comma-separated multi-position |
| pos_main | string | First normalized position; not a learned role |
| age | years | Age at source observation; unknown/implausible values remain NULL |
| nation | string | Source nationality label; may contain source prefix, not a normalized citizenship ID |
| minutes | minutes | Nonnegative recorded season exposure; missing/negative is NULL |
| mp | matches | Recorded appearances; missing/negative is NULL |
| nineties | 90-minute units | Exact minutes/90, not rounded provider 90s |
| gls | goals | Recorded nonnegative total, including penalties where source does |
| ast | assists | Source-defined assists; definitions can differ across providers |
| ga | goals+assists | gls+ast only when both observed |
| sh | shots | Recorded total; legacy value discarded due to row-order merge |
| sot | shots on target | Recorded total; legacy value discarded |
| crs | crosses | Recorded total; legacy value discarded |
| int | interceptions | Recorded total; legacy value discarded |
| tklw | tackles won | Recorded total; legacy value discarded |
| fls | fouls committed | Recorded total; lower direction for discipline styles, not a pressure measure |
| fld | fouls drawn | Recorded total; legacy value discarded |
| xg, xa | expected goal/assist totals | Provider-specific model outputs; never backfilled across sources |
| `<count>_p90` | count per 90 minutes | Each of gls/ast/ga/sh/sot/crs/int/tklw/fls/fld/xg/xa divided by nineties; NULL stays NULL |
| gls_p90_raw, ast_p90_raw, ga_p90_raw | provider rate | Retained legacy source values for audit only; not used in model fitting |
| quality_outlier | boolean | Flags minutes>4500, goals/90>3 or shots/90>15; review flag, not automatic clipping |
| provenance_status | string | `legacy_unverified` or `direct_snapshot` |
| snapshot_sha256 | SHA-256 hex | Parent raw response/input hash; not a license or truth guarantee |
| source_snapshot | relative path | Normalized source input or original legacy CSV |

Missing statistics are never encoded as zero. Exact duplicate rows are removed; conflicting duplicate observation keys stop preprocessing. Rates use a 450-minute eligibility floor. Model imputation/scaling fit only on training data; constant/all-missing columns are removed. G+A is excluded from fitting because it duplicates two inputs.

## Transfermarkt current sample

`data/external/transfermarkt/current_market_sample.csv`: `source_player_id`, `player`, `profile_path` (source-relative URL), `pos` (source prose), `team`, `age` (years), `market_value_eur` (integer EUR, unknown=NULL), `currency` (EUR), `valuation_date` (NULL unless explicit), `temporal_scope` (current_snapshot_not_historical), `source`, `league`, `snapshot_sha256`, `retrieved_at` (UTC ISO-8601), `requested_season` (request provenance only), `season` (NULL, historical state unverified).

`current_profiles_sample.csv`: source identity/name/league/hash/retrieval time plus `date_of_birth` (ISO date), `height_cm` (centimetres), `position` (source prose), `foot`, `nation`. No historical age/team/contract is inferred. The sample is two players, not full profile coverage.

For authorized **historical** valuations the supported as-of schema is: `source_player_id`, `valuation_date`, `known_at`, `currency`, `value_eur`. Both dates must be at/before the decision cutoff. Current retrieval time does not establish past availability. Budgeted recommendations require attached `market_value_eur`, `valuation_date`, `valuation_known_at` and an explicit cutoff; NULL prices are excluded. Market value is not a transfer fee. `budget_est` in legacy processed outputs is an invented heuristic and is **never used** in the new workflow.

## Source normalizations

FBref `player/team/position/nationality/age/minutes/games/goals/assists` map to canonical fields; additional tables join by source ID, team, league and season with one-to-one validation. Understat `id/player_name/team_title/position/time/goals/assists/shots/xG/xA/games` map to source_player_id/player/team/pos/minutes/gls/ast/sh/xg/xa/mp. Understat F/S→FW, M→MF, D→DF, GK→GK. Understat counts and FBref counts are not concatenated as duplicate estimates of one player's season.

## Provenance, evaluation and events

- `data/raw/provenance.jsonl`: source, URL, retrieval UTC timestamp, SHA-256, relative snapshot path, HTTP status, category and available league/season/player context. Failed network handshakes have no HTTP response body; source coverage records the error.
- `reports/source_coverage.csv`: source/league/season/category, rows, status, reason, check timestamp, optional requested URL. Blocked shared prerequisites do not imply every endpoint was requested.
- `reports/dataset.json`: dataset kind, row count, sources, raw hashes, processed hash and limitations.
- Model-only columns: cluster (arbitrary K-means label), pc1…pcN (standardized PCA coordinates), affinity (cosine −1…1), similarity (cosine neighbor score); scores are not probabilities.
- Baselines: style, absolute measured weight fraction, supported/unsupported status and top-10 Jaccard overlap with linear weighted, minutes and goals+assists rankings. No relevance metric implied.
- Robustness: style, perturbation trial, top-10 Jaccard. Seed stability: seed and adjusted Rand index. PCA loadings/components and per-cluster raw-rate means have accompanying position counts.
- Temporal proxy: train_through, evaluation_season, method, queries, candidate_count, recall_at_5, mrr. Uses real common source entities when available; an empty CSV means **unrun**, not zero recall. Profile persistence is not transfer success.
- Scenarios: style, position, rank, player/team/season, affinity, budget_status. No fabricated club mandate or fee.
- Event log: case_id, activity, actual UTC timestamp, actor, event_kind, attributes JSON. Only actual app actions enter `data/events/`; simulation/test files are separate. DFG edge counts/median elapsed seconds and incomplete cases are descriptive and require genuine events.

Checked-in model paths and portable-export metadata are repository-relative. Local SQL-backed MLflow normalizes runtime artifact URIs to machine-local absolute paths; those URIs are omitted from the export and its source-name tag is normalized without altering metrics. Git commit, dirty status, dataset fingerprint, environment and owner tags identify each actual run.


## Published worldfootballR archive trial

`data/external/worldfootballr/` is a separate source-acquisition route. Each provider/category Parquet retains its original named R fields plus source IDs, canonical `season`, source, acquisition and parent snapshot SHA-256. FBref retains `Season_End_Year`, `Squad`, `Comp`, `Player`, `Nation`, `Pos`, `Age`, `Born`, `Url` and category-specific named metrics. Normalized `source_player_id` is extracted from the provider URL, not inferred from names. Detailed original column names and data sizes are available by reading the separate Parquet files; their source documentation remains worldfootballR/FBref.

The audited `fbref_player_seasons.parquet` fields are: source_player_id, team, season; player, nation, pos, age, birth_year; minutes, mp, gls, ast, xg, xag; sh, sot, int, tklw, crs, fls, fld; passes_completed, passes_attempted, key_passes, touches, successful_take_ons; league, source, provenance_status and period_status. Counts are totals for their source period, xg/xag are expected-goal/assisted-goal totals, minutes are exposure, age is the unmodified source age text, and birth_year is not a date of birth. An auxiliary total is NULL if its own published 90s differs from standard minutes/90 beyond rounding tolerance. No rates, imputation or model fitting are done in this candidate table.

Understat shot fields retain minute, result, X/Y, xG, source player/match/shot IDs, situation, shotType, teams, date, lastAction and assistant display name. X/Y are the provider's normalized pitch coordinates, not metres. Shot time is match minute; date is provider match timestamp. The aggregate table has source_player_id, season, player, shots, goals (result exactly Goal), summed xg and coverage_note. It does not provide minutes, per-90 values, assists or xA.

Transfermarkt archived valuation/profile fields retain country/competition, squad, source start year, source age/DOB/nationality/position/height/foot, contract/joined dates, player URL and player_market_value_euro. Height is in metres, money in EUR, DOB is a source date string; none is silently converted into a verified as-of record. Transfers retain team_name, country/league, season, transfer_type (Arrivals/Departures), other club/country/league, transfer_fee, is_loan, notes/window and reported appearances/goals/minutes. Fee is the archived parser's EUR numeric output; unknown remains NULL, and neither a season/window nor date_joined is an exact transfer timestamp. Rows are not deduplicated into uniquely validated actual transfer events.

The upstream mapping retains PlayerFBref, UrlFBref, UrlTmarkt and TmPos, with extracted fbref_id/transfermarkt_id, mapping_status and archive_text_encoding. It is an upstream published proposal, not locally approved. Missing/duplicate IDs are reported in the archive inventory.

`worldfootballr_coverage.csv` adds the acquisition route, observed counts, snapshot/partial/mismatch status and actual Understat date/match ranges. `worldfootballr_merge_audit.csv` records matched/missing keys, incompatible exposure counts and maximum exposure differences. Source URL/hash/retrieval time and byte-preservation rules are in the archive manifest and trial report. Archives contain some incomplete and differently dated category snapshots; their presence does not upgrade the old model's validation status.

## Source-use restriction discovered in the uploaded scraper trial

`ml_use_status=restricted_pending_explicit_license` marks Transfermarkt valuations, transfers and the provider-derived player mapping. This is a rights restriction, separate from completeness or temporal validity. Do not use these records in ML experiments or redistribute them absent a reviewed licence. Previously acquired raw bytes are retained as evidence. `reports/uploaded_scraper_trial.json` contains policy URL, SHA-256 and quotes; the 25-row Segunda scorer response is access evidence only and has no player-statistics export.

## Recorded valuation evidence audit

Separate `collected_valuation_record_audit`, `collected_valuation_header_evidence`, `collected_dated_valuation_evidence` and `collected_current_value_identity_candidates` tables preserve the original outputs. `reports/valuation_audit_dictionary.csv` lists every new field/dtype. `market_value_eur` is a source-reported EUR assessment, not a fee or project prediction. `valuation_date` records explicitly parsed current-header update dates for two values; `valuation_known_at` is their conservative first retained observation in October 2026. Neither is inferred from a season, DOB, club join or contract. Snapshot-hash fields retain the raw proof. `date_evidence_kind`, `identity_match_status`, `use_authorized` and JSON `valuation_blockers` distinguish recorded amounts from eligible attachments. Both current identity proposals are unreviewed; all historical budget attachments remain ineligible. `requested_league_context` records the request context, not verified current membership. See [the audit and exact coverage](VALUATION_AUDIT.md).

## Collected-data outputs and mandatory feature contract

The existing ten `FEATURE_COLS` remain mandatory schema fields; source identity, observation ID, numeric `player_id`, provenance, position, age and minutes remain explicit. Budget fields are mandatory for budget scenarios, but all verified historical attachments remain unknown. See [the contract and decisions](COLLECTED_PREPROCESSING.md), `reports/mandatory_features.csv`, and `reports/mandatory_feature_coverage.csv`. `reports/collected_data_dictionary.csv` enumerates every field and dtype in the new `collected_*` and identity outputs alongside the existing real directory. Club stints aggregate before the 450-minute floor, with missing stint totals propagating; `player_id` identifies observations and `entity_id` identifies the source person. `core_proxy_split` uses an earlier holdout than the offensive `experiment_split` because 2024/25 defensive coverage is sparse. Raw inputs and the old model data remain intact.
