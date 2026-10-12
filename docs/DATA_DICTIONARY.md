# Data dictionary — current teacher-review datasets

Machine-readable catalogs: `docs/data_dictionary_review.csv` (prepared tables), `data/raw/review_manifest.json` (every raw column, source, selection and checksum), and `docs/data_dictionary_raw.csv` (source-field glossary). Some extended/raw definitions still require provider-glossary verification; those entries are explicitly marked pending rather than guessed.

## Grain and keys

| Dataset | One row represents | Key |
|---|---|---|
| FBref club seasons | A source player, club, league and season stint | source_player_id + team + league + season |
| FBref history | Aggregated compatible club stints within a league/season | entity_id + league + season |
| Core gallery | Eligible player in one selected league per season | entity_id + season; dominant league by minutes |
| Understat shots | An observed source shot event | league + shot_id |
| Understat summaries | Observed shots for a player in a league/season | league + source_player_id + season |
| Transfermarkt profiles | Current uploaded source profile | source_player_id |
| Transfermarkt values | Reported dated market assessment | source_player_id + valuation_date |

`entity_id` is source-specific person identity; `observation_id` identifies the season/league observation; `player_id` is a stable derived observation key. Neither player names nor equal-looking IDs across providers establish equivalence. Provisional FBref/Transfermarkt proposals remain separate. Understat is not joined into fitted model data.

## Performance variables and calculation

For each count C with observed positive minutes M, **C_p90 = C × 90 / M**. Unknown counts/exposure remain missing; missing is not zero. No global EDA imputation. Model imputation/scaling is fitted only on training seasons.

| Fields | Meaning | Unit / source |
|---|---|---|
| minutes, mp | Recorded playing exposure and appearances | minutes; matches; FBref standard |
| age, birth_year | Source season age and birth year; not an inferred exact DOB | years; calendar year |
| gls, gls_p90 | Goals including source-defined penalties | goals; goals/90; standard |
| ast, ast_p90 | Source-defined assists | assists; assists/90; standard |
| ga, ga_p90 | gls + ast, only if both observed | events; events/90; excluded as redundant from Core fitting |
| sh, sh_p90 | Shots | shots; shots/90; shooting |
| sot, sot_p90 | Shots on target | shots; shots/90; shooting |
| crs, crs_p90 | Crosses | crosses; crosses/90; misc |
| int, int_p90 | Interceptions | interceptions; interceptions/90; defense |
| tklw, tklw_p90 | Tackles won according to provider | tackles; tackles/90; defense |
| fls, fls_p90 | Fouls committed | fouls; fouls/90; misc |
| fld, fld_p90 | Fouls drawn/received | fouls; fouls/90; misc |
| xg, xg_p90 | Expected goals as supplied by FBref for that observation | expected goals; /90; source model differs from Understat |
| xag, xag_p90 | Expected assisted goals, when supplied | expected goals; /90; source-specific definition |
| passes_completed, passes_attempted | Provider recorded passes | counts; passing |
| pass_completion_pct | completed / attempted × 100 with positive observed denominator | percent |
| key_passes, touches, successful_take_ons | Provider recorded attacking involvement | counts; extended fields are not all used by Core |
| pos, pos_main | Source position and broad normalized GK/DF/MF/FW | category; no fine tactical role inferred |
| club_count, clubs | Number/list of observed clubs aggregated within league/season | count; JSON list |
| partial_season | 2025/26 partial source snapshot indicator | boolean; does not certify other seasons' completeness |

Core uses nine per-90 fields: gls, ast, sh, sot, crs, int, tklw, fls, fld. Expert style affinity is a weighted standardized score, not a probability. Distances, PCA coordinates and cluster labels are model outputs, not observed football statistics.

## Understat-specific fields

`X` and `Y` are normalized provider pitch coordinates in [0,1], not metres; the app converts to percentages for display. `xG` is the provider shot's expected-goal value in [0,1]; real zeros remain zero. `minute` is the minute of the shot, not total player playing time. `shot_date` is parsed source match date; original timezone/publication time is not independently established. `result`, `situation`, `shotType` and home/away fields are source categories. Own goals are retained but excluded from attacking attempt/xG totals. Summary `xg_per_shot = attacking xg / attacking shots` with a positive denominator. Minutes are unavailable in shot-only summaries; per-90 rates are not created. Unknown/inconsistent sides or invalid coordinates are quarantined without inventing a team.

## Market values and profiles

`market_value_eur` is a nonnegative reported market assessment, **with currency assumed EUR because the raw CSV does not declare it**. It is not a paid transfer fee or an estimated model output. Zero is reported-but-ambiguous, not proof that a player is free. `valuation_date` is the uploaded ISO effective date; `valuation_known_at` is first local receipt, and `source_publication_known_at` is unknown. Historical affordability is therefore not validated.

`date_of_birth` is uploaded profile DOB; `height_raw_cm` preserves source zero sentinels while `height_cm` maps nonpositive/invalid values to missing. Current club/position fields do not establish past membership/role. Provider restrictions and provisional identity flags remain visible; valuation fields are excluded from model fitting.

## Model evaluation fields

MRR is the mean reciprocal rank of the same player's next-season identity; Recall@5/10 is its top-K hit probability, including fair tie handling. They are not transfer success rates. Silhouette describes clustering separation; adjusted Rand index describes partition stability; top-five Jaccard compares shortlist overlap; PCA explained variance describes retained standardized-feature variation. Their cohorts and uncertainty limits are in notebook 11 and `reports/five_league_pipeline/`.

## Approved extended glossary

`docs/data_dictionary_review.csv` now defines every prepared-table field, including per-90 calculations, flags, shot aggregation and temporal provenance. Rebuild with `python scripts/complete_review_dictionary.py`.

`docs/data_dictionary_raw.csv` catalogs every retained raw CSV field and source-specific unit. Rebuild with `python -m scripts.raw_review_dictionary`. Two unused Transfermarkt team fields, `season_points_for` and `season_points_against`, remain explicitly unverified; no semantics or calculations are invented for them. FBref progressive metrics use the provider's definitions, which may change across seasons; distance metrics are yards. Current profile metadata must not be treated as historical knowledge. Raw values' currency is still unverified.


Clean submission update: obsolete stage files and duplicate artifacts were removed. Use `DATA_SOURCES.md` for current paths and `reports/teacher_review/CLEANUP_REPORT.md` for current verification. Earlier verification counts refer to the pre-cleanup branch snapshot.
