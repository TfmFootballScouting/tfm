# Four-league shot preprocessing and EDA

The newly acquired Premier League, Bundesliga, Serie A and Ligue 1 data has now passed a separate cleaning, preprocessing, EDA and identity-proposal stage. [Notebook 13](../notebooks/13_four_league_shot_eda.ipynb) was executed against the real retained tables. The existing recommendation models, app and earlier datasets are unchanged.

## What was cleaned and prepared

- **182,938 source events**, all retained with quality and season-coverage flags.
- Required shot/player IDs, names, dates, teams, coordinates, xG and minute fields are present. Shot IDs are unique within league; coordinates/xG are bounded [0,1]; observed minutes are 0–105.
- **638 own-goal events** remain in the source table, but are excluded from attempts, shooting goals and shooting-xG aggregates. There are **182,300 attempts excluding own goals**.
- **10,087 player-season summaries** and **10,314 player-club-season summaries** preserve Understat source identities and multi-club observations.
- Summaries include observed attempts/goals/xG, non-penalty totals, xG per attempt, conversion rate, goals-minus-xG and dates. `matches_with_shots` is not appearances. No per-90 rates were fabricated without verified minutes.
- Missing optional source fields remain missing. There was no synthetic substitution or arbitrary outlier deletion.

Source-specific normalized tables are private/local under `data/processed/real/four_league_*.parquet`. Raw inputs and the acquisition manifests remain preserved.

## Coverage and EDA decisions

All 2025/26 data is partial. Bundesliga 2024/25 is missing one expected fixture; Serie A is missing six. These cohorts remain in cleaned tables with their observed schedule fraction, but are excluded from completed-season descriptive comparisons.

The EDA comparison cohort contains **2,906 player-season observations**, using completed seasons with the expected match count and at least 20 observed attempts. This is a descriptive support rule, not a validated optimal threshold or a future-outcome tuning choice. Expected-match-count agreement does not independently prove complete shot capture.

The notebook/report figures show distributions, outcome and situation frequencies, goals versus xG, finishing residuals and source-coordinate shot maps. Maps use normalized source coordinates rather than actual pitch meters. Goals and xG have a descriptive Pearson correlation of approximately **0.908** in this cohort; both share shot volume, so this does not establish predictive skill. Goals-minus-xG remains noisy, and neither a residual nor a map validates scouting or transfer success.

## FBref identity review

Match only the same league, season, exact normalized player name and conservatively normalized club. Explicit observed spelling equivalents, such as Manchester United/Manchester Utd, Bayer Leverkusen/Leverkusen and Paris Saint Germain/Paris S-G, are recorded in `club_aliases.csv`. No fuzzy player match or generic club-prefix stripping was added.

Reject one-to-many identities within a season. The resulting **9,223 supported player-season proposals** cover about 91% of the 10,087 shot-taking player-season observations:

| League | Shot-taking player-seasons | Supported proposals | Unresolved |
|---|---:|---:|---:|
| Premier League | 2,545 | 2,372 | 173 |
| Bundesliga | 2,294 | 2,139 | 155 |
| Serie A | 2,679 | 2,454 | 225 |
| Ligue 1 | 2,569 | 2,258 | 311 |

The evidence is name plus club/league/season, not independent shared full DOB or an approved crosswalk. **Approved cross-source identities: zero.** These are player-season counts, not globally unique verified people. Per-club pairs are stored separately in the private review queue; no source ID was silently replaced with a canonical FBref ID.

A temporal test verifies that adding later seasons does not change earlier-season proposals. Existing model-use guards reject the unreviewed cross-source table.

## Advanced FBref feature readiness

The 2024/25 four-league passing and shooting tables have **2,253 exposure-compatible rows each**. Defense, possession and miscellaneous categories have only **118 compatible rows out of 1,710 each**. This is an exposure check, not proof that every individual feature is present or every row passes minutes/age eligibility.

This explains why merely retaining richer archive columns does not make a complete 2024/25 six-style gallery available. Misaligned statistics cannot be treated as full-season values, and Understat shots do not replace missing defensive metrics. `advanced_feature_eligibility.csv` records each league/season/category status.

## Reproduce and inspect

With the acquisition outputs available:

```bash
python -m scripts.four_league_preprocessing
python -m scripts.four_league_eda_notebook
python -m pytest -q tests/test_four_league_preprocessing.py tests/test_four_league_acquisition.py
```

The public reports in `reports/four_league_preprocessing/` include:

- `preprocessing.json`: input/output/source-code hashes, counts and interpretation limits.
- `quality.csv`, `outcomes.csv`, `situations.csv`, `shot_types.csv`: source-separated quality/descriptive tables.
- `player_distributions.csv`, `correlations.csv`, `attacking_eda.png`, `shot_maps.png`: EDA outputs.
- `identity_coverage.csv`, `club_aliases.csv`: aggregate proposal coverage and explicit spelling equivalents.
- `advanced_feature_eligibility.csv`: category exposure readiness.
- `dictionary.csv`: output field types, missingness and definitions.
- `notebook_execution.json`, test XML and verification metadata: actual execution evidence.

The row-level identity queue and normalized datasets remain ignored in Git. Original provider-use restrictions are preserved; no Transfermarkt values or fees enter these shooting summaries.

## Next application boundary

Source-specific shooting analysis can be added using Understat IDs and clear coverage labels. FBref player development can use its own existing IDs. Attaching Understat measures directly to a FBref recommendation remains contingent on reviewing the source identity crosswalk. Neither new model metrics nor a transfer-success outcome is claimed by this preprocessing stage.

Validation: **four real-data tests passed**, including own-goal accounting, absent per-90 fabrication, temporal identity invariance, source-use rejection and preservation of 335 older artifacts. Notebook 13 executed all **six code cells without errors**. Matplotlib/pyparsing emitted deprecation warnings; no checks were disabled. Input/output/source hashes and local document links were verified.
