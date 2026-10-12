# Data sources used by ScoutIQ

This document describes the actual data served on `minimal/scoutiq-runtime`. The provenance baseline is research commit `a29e192933e70218de53d658e1b72b59844f751e`; source files and model artifacts were not recollected or retrained when making this branch.

| Application data | Original provider | How it was obtained | Actual use |
|---|---|---|---|
| Five-league statistics | [FBref](https://fbref.com/) | Six checksum-pinned RDS assets from [worldfootballR_data](https://github.com/JaseZiv/worldfootballR_data), release `fb_big5_advanced_season_stats` | Recommendations, tactical affinity, comparisons, clusters and player development |
| La Liga shots | [Understat](https://understat.com/league/La_liga) | `la_liga_shot_data.rds`, secondary release `understat_shots` in the same repository | Source-specific shot analysis; not fitted recommendation features |
| Optional four-league shots | Understat | `epl_shot_data.rds`, `bundesliga_shot_data.rds`, `serie_a_shot_data.rds`, `ligue_1_shot_data.rds` from the same secondary release | Shot analysis only when the local prepared file is present |
| Optional reported valuations and identity metadata | [Transfermarkt](https://www.transfermarkt.com/), via user-supplied [salimt/football-datasets](https://github.com/salimt/football-datasets) files | Uploaded `player_market_value.csv`, `player_profiles.csv`, `team_details.csv`, `team_competitions_seasons.csv`; upload-to-repository commit not verified | Included post-ranking screening through provisional identity proposals; never model training |

The raw metadata inventory is [data/raw/sources_manifest.json](../data/raw/sources_manifest.json). It provides exact URLs and file hashes rather than treating the original website and a secondary archive as the same acquisition source. The archival code commit is not proof of the collection date or historical public availability of each football observation. Raw archives are kept locally; [restoration instructions](../data/raw/README.md) are included without adding provider-derived archives to Git.

## FBref lineage and feature meaning

```text
big5_player_{standard,shooting,passing,defense,possession,misc}.rds
  → select target leagues/seasons and retain original FBref player IDs
  → align categories on source player ID + league + season + club
  → check playing-time compatibility before accepting auxiliary category statistics
  → normalize units and compute per-90 rates
  → aggregate compatible club stints within player + league + season
  → five_league_pipeline_player_seasons.parquet (15,948 rows)
  → model-eligible gallery; choose highest-minutes league per player/season
  → five_league_pipeline_core_gallery.parquet (7,398 rows)
  → frozen five_league_core_recommender.joblib
```

`standard` supplies names, age, position, club, minutes, appearances, goals and assists. `shooting` supplies shots and shots on target; `defense` supplies interceptions and tackles won; `misc` supplies crosses and fouls committed/received. Passing and possession archives supply additional observed fields, but these are not all fitted model inputs. The core recommendation model uses nine measured per-90 features: goals, assists, shots, shots on target, crosses, interceptions, tackles won, fouls committed and fouls received. Goals plus assists is excluded as redundant.

Same-source joins use FBref IDs, not names. `entity_id` identifies the player across seasons. Player histories remain separate per player/league/season, including transfers between leagues; the recommendation gallery chooses one league per player/season rather than blending competitions. Missing source observations remain unknown. Imputation/scaling are fitted only on training observations; served seasons use frozen transformations.

The requested range is **2020/21–2025/26**, but recent seasons lack sufficiently complete core statistical categories. Standard player-history rows are available for 2024/25 and partial 2025/26; this does not make those seasons complete recommendation galleries. [DATA_COVERAGE.csv](DATA_COVERAGE.csv) contains actual history and gallery counts for all five leagues and all six requested seasons, including zero coverage. [DATA_CATEGORY_COVERAGE.csv](DATA_CATEGORY_COVERAGE.csv) preserves the original raw/category alignment counts and status for every league, season and FBref category. The app offers complete recommendation galleries **2020/21–2023/24**. Training uses 2020/21–2021/22; validation uses 2022/23; the holdout uses 2023/24. The latest complete gallery contains 1,810 players. These are observed season cohorts, not live rosters.

## Understat lineage

The raw La Liga shot archive is parsed and filtered into a source-specific shot table, then normalized into `collected_understat_shots.parquet`: **45,847 observed shots**. Source player IDs and shot IDs are retained. Home/away conflicts are handled explicitly in the viewer; zero-xG shots remain real events. Optional four-league raw archives are prepared separately into `four_league_clean_shots.parquet`: **182,938 shots**, giving 228,785 locally available shots with La Liga. Those optional prepared/raw files are not bundled in Git.

Shots span requested seasons where observed; 2025/26 is partial. Some archived 2024/25 league coverage is incomplete. The app displays observed versus expected fixture counts and excludes partial seasons by default. Understat and FBref player identities are not automatically merged for recommendations. Shot records are descriptive source data, not historical transfer validation.

## Included valuations

Raw valuation observations are separate from transfer fees. Price screening selects a reported valuation dated on or before the selected cutoff. That date is not proof that the record was publicly known at the historical cutoff. Identity proposals remain unreviewed; source currency is assumed EUR and has not been independently established. These limitations prevent claiming verified historical affordability or using valuations as recommendation model features.

The optional loader requires `collected_salimt_values.parquet` and `europe_review_candidates.parquet` matching `models/real/runtime_manifest.json`. Their underlying user uploads are hashed in the raw manifest. Both prepared files are now included in Git, so a clean clone can use reported-value filtering without importing a separate local bundle. The uploaded Kaggle valuation dataset and historical transfer files are not necessary inputs for the currently served recommender, so they remain on the full research branch/local storage.

## Integrity and reproducibility limits

`models/real/runtime_manifest.json` preserves dataset versions, model/output fingerprints and original training-source fingerprints. `sources_manifest.json` records raw source fingerprints. The app's artifacts remain unchanged; this documentation does not create new evaluation outcomes. Restoration verifies exact archived bytes; preprocessing/training reproduction additionally requires the full research branch and its dependencies. The provider rights attached to raw data are not granted by the secondary repository's software licence. Transfermarkt source-use restrictions remain enforced by `src/data/source_rights.py`.
