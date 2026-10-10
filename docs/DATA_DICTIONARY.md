# Data dictionary and grain

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
