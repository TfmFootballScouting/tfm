> Historical application snapshot. The current scout-focused interface is documented in [SCOUTING_INTERFACE.md](SCOUTING_INTERFACE.md).

# Collected-model application integration

Streamlit now defaults to the evaluated **Core** model with all **six original playing styles**. An **Offensive** model and an explicit **Legacy exploration** option are also available. The existing folder structure, provider datasets, trained model artifacts and previous experiment results are preserved. The two limited goal/assist profiles remain available only in legacy exploration; no original style definition or coefficient was changed.

## What works

- Core offers the four sufficiently populated completed-season galleries from 2020/21 through 2023/24, with 2023/24 selected by default: **393 distinct player profiles**.
- Offensive offers five galleries from 2020/21 through 2024/25, with 2024/25 selected by default: **399 profiles**. Only vertical and counterattack style directions meet the measured-feature requirement for this model.
- Position, age, minimum-minute and league filters are available. Club exclusion checks all club stints in an aggregated season, rather than just its display label.
- Reported-value budget screening remains available after football ranking, before shortlist truncation. At the default value cutoff of 2025-09-11, **326/393 core profiles** and **337/399 offensive profiles** have positive reported values. Identity links remain provisional; unknown/ambiguous zero values are excluded when the filter is enabled.
- Similar-player searches use the selected model's distance method and the selected season's gallery. They exclude the reference identity, deduplicate people, support the same broad-position requirement and apply position, age, minutes, club and reported-budget constraints to candidates.
- Two-player comparison displays raw per-90 measurements and same-season reference radars. Unknown measurements are gaps, not zero; identical player selections render separate charts without duplicate-element errors.
- Player history shows retained FBref season, club, minutes, goals and assists, with partial-season flags. It does not infer historical position from current external profiles.
- The model/coverage tab displays actual held-out retrieval metrics, PCA variance, cluster count, robustness and season coverage, with the interpretation limits. Shortlist CSV export retains unscaled affinity scores, source IDs and price/date/match provenance.

## Serving without refitting the experiment

`src/app/collected.py` checks model, dataset and training-code fingerprints against existing manifests. It loads `models/real/enrichment_core_recommender.joblib` or `enrichment_offensive_recommender.joblib`, then copies the model for an observed-season gallery. The saved imputer, scaler, PCA and K-means stay frozen. Candidate features are transformed and a neighbour index is built for that gallery; no training median, scale, component or centroid is fitted on the new candidates. Tests verify the original model is not mutated and similarity distances equal direct Euclidean distances in the frozen standardized representation.

The core source has only one eligible advanced profile for 2024/25 and no final 2025/26 gallery. Seasons with fewer than ten candidates, or flagged as partial, are excluded from the selector. Advanced Segunda features are not available in the eligible source dataset, so Segunda's basic uploaded statistics are not presented as complete six-style profiles.

## Interpretation and remaining limits

This is retrospective exploration of observed full-season profiles. Selecting an early season does not simulate what a scout would have known then; the models use their documented development seasons. The default core model's transforms were fitted on 2020/21–2021/22; the offensive model's on 2020/21–2022/23. Future-season information remains excluded from their original training/evaluation folds, but historical decision-time scouting is not claimed by this UI.

Tactical affinity is cosine similarity to an expert direction, not probability of success. Neighbour distance is different: the selected collected models use Euclidean distance with display score `1/(1+distance)`. That score is not a probability or a percentage. K-means groups describe statistical profiles, not the six expert style directions. Core PC4 sensitivity from the earlier validation remains a limitation. Core and offensive holdout periods differ, so their displayed MRR values are not a controlled comparison of feature sets.

The reported-value screen is the user-authorized local display/filter feature documented in [REPORTED_VALUE_BUDGET.md](REPORTED_VALUE_BUDGET.md). It does not turn provider prices into model features, verify identity proposals or original publication dates, or predict transfer fees. Existing source-use/model guards remain intact. Earlier budget coverage reports describe the previous legacy-default app snapshot; `reports/collected_application_verification.json` describes this current serving configuration.

## Run and verify

Use the retained snapshot with its ignored provider uploads and normalized files. From the repository root:

```bash
.venv/bin/python -m streamlit run src/app/streamlit_app.py --server.headless true --server.port 8501
.venv/bin/python -m pytest -q --junitxml=reports/collected_application_tests.xml
.venv/bin/python -m scripts.verify_collected_application
```

The verification script checks preserved data/model evidence, all served seasons and their price coverage, frozen training transformations, actual completed tests and the running application health endpoint. The tests exercise the core default, all six styles, budget and club screening, same-season similarity, duplicate comparison selections, offensive mode, radar missingness and the explicit legacy workflow. Test events use temporary logs and are not human scouting evidence.

Completed: model serving, six-style core selection, source-season candidate galleries, budget retention, player comparisons/history, distance-correct similarity, coverage diagnostics and functional tests. Still partial/blocked: final 2025/26 and advanced Segunda coverage, verified cross-source identities, historical-budget availability, trained value estimation and actual transfer-success validation.
