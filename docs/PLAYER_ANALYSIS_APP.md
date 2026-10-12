# ScoutIQ: player development and shot analysis

Two new source-specific analysis tabs extend the current six-style app. Recommendation model artifacts, training statistics, prices and identity approval rules are unchanged.

## Player evolution — FBref

Select one or several players from the sidebar's chosen leagues. The picker uses FBref identities, with the last observed club/season stated explicitly. The first default player is an available recommendation, not an automatically joined Understat profile.

Choose a statistic, minimum observed season minutes, whether to include partial seasons, and whether to include retained history in other leagues. The chart and CSV show the player's actual stored FBref history. Per-90 measurements use existing verified FBref exposure, with missing measurements shown as gaps.

A source identity can have multiple leagues in one season. Each **player/league has a separate series**, so rates and counts are not blended between competitions. Missing seasons insert only unknown display gaps, not fabricated observations. Numbered chart labels distinguish selected source identities, including players with identical names; the number reflects selection order, not player quality. The history table retains observed league and club labels.

This is descriptive development context, not proof of improved talent. Minutes, club, league and role can change between observations. Complete-season selection and minimum-minute controls support cautious comparisons.

## Shot analysis — Understat

The retained workspace has **228,785 source shot events**: 182,938 from the four newly prepared leagues and 45,847 retained La Liga events. All five leagues can be explored independently of the FBref recommendation IDs.

Choose a league within the sidebar's market, a source season, a source player and shot situations. The view shows:

- Observed attempts, goals, summed xG and xG per attempt.
- An interactive shot map with outcome colors, xG-based marker sizes and readable hover details. True zero-xG attempts remain visible.
- A match-date xG chart and a downloadable readable shot table.
- Source match-count coverage and warnings for incomplete/partial seasons.

Own-goal events are excluded from the attacker's attempts and goals. No appearance counts or per-90 shot rates are inferred from shot-only data. Coordinates are normalized source coordinates, not measured pitch meters. Dates without recorded shots are not invented as player appearances.

Partial 2025/26 is hidden by default, and is available only with the explicit partial-season checkbox. Bundesliga 2024/25 and Serie A 2024/25 show missing-match warnings. An expected match count is not independent proof of every shot's completeness.

Cross-source links remain provisional. The app does not silently attach Understat stats to a FBref recommendation, infer player age/position from an unapproved match or refit the model with these observations. The scouting season and the shot-analysis season have separate visible labels; source shooting coverage extends beyond complete six-style profile coverage.

## Files and missing local data

`src/app/player_analysis.py` contains the source-specific loader, history chart preparation and two renderers. `src/app/streamlit_app.py` adds the tabs; the existing sidebar layout is unchanged.

The loader checks data fingerprints. If locally prepared four-league shot data is absent, retained La Liga analysis still works. If none of the selected leagues has local shot data, the app explains the prerequisite commands rather than inventing a fallback:

```bash
python -m pip install -r requirements-archives.txt
python -m scripts.four_league_acquisition --download --public-only
python -m scripts.four_league_preprocessing
```

Restart Streamlit after preparing files, so cached availability refreshes. Keep the pinned archive manifests and their checksum validation. Current source policy and private-data exclusions are retained.

## Verification

The full retained-workspace regression run passed **124 tests**. After a final refinement of distinct player labels and translated hover labels, **five focused tests passed** on the final analysis module. Tests cover real data, zero-xG visibility, unknown-season display gaps, separate cross-league transfer observations, multiple-player comparison, empty filters, partial/missing coverage, and absence of optional four-league files. Tests and evidence are in `reports/player_analysis_app/`.

This is Linux/cloud validation; no new claim of native Windows validation or verified historical transfer success is made.

Desktop/mobile browser checks confirmed development and shot-map rendering, no JavaScript errors and no mobile horizontal overflow. The default shot example rendered 130 observed attempts. Full-suite deprecation warnings were retained; no checks were disabled. Local documentation links were verified.
