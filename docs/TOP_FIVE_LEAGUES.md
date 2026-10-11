# Five-league scouting and interface update

ScoutIQ now defaults to a five-league market: La Liga, Premier League, Bundesliga, Serie A and Ligue 1. The original La Liga gallery remains selectable. Real statistics come from six already retained, checksum-pinned FBref/worldfootballR archive categories; no provider was crawled, restriction bypassed or synthetic observation created for this extension.

## Usable coverage

| Model | Offered seasons | Latest season gallery |
|---|---|---|
| Core, all six original styles | 2020/21–2023/24 | 1,810 players across five leagues |
| Offensive, vertical/counterattack | 2020/21–2024/25 | 1,804 players across five leagues |

Core 2024/25 advanced categories are missing or incompatible with the standard exposure; only four complete profiles remain across all five leagues, so the season is not offered. The archive's 2025/26 snapshot is partial and excluded. Advanced Segunda coverage is still unavailable. Full source/league/season/category counts, missingness/cleaning, field dictionary and eligibility are in `reports/top_five_leagues/`.

Auxiliary category counts are accepted only when reported 90s match standard minutes/90 within 0.061, allowing source rounding. Incompatible counts stay unknown. Club stints sum only within the same source person, league and season; missing stint totals propagate. For players moving across leagues, historical rows remain separate; the gallery chooses the league with the highest observed minutes before feature eligibility. Ties use league name ascending. Counts/rates from different competitions are never blended. This selection changes some La Liga gallery membership compared with the original single-league output.

## Models and validation

Existing La Liga-trained models, preprocessing parameters, neighbor method, PCA and clusters remain frozen. Every new gallery uses those saved transforms. These models were not refitted on Europe, and scores are not adjusted for league strength.

Actual next-season same-player profile retrieval was executed separately for every league, including all existing profile methods, goals/assists and random baselines. Core evaluates 2022/23 →2023/24; offensive 2023/24 →2024/25. The selected method remains the one previously chosen on La Liga validation. This is an external-use diagnostic, not actual transfer validation or calibrated tactical relevance. Core and offensive use different years/cohorts and should not be compared as a controlled experiment. Detailed metrics and bootstrap intervals are in `evaluation.csv`; the executed notebook is `notebooks/10_top_five_leagues.ipynb`. No new model-training or MLflow model run is claimed.

## Interface behavior

The redesigned interface has a consistent dark theme, readable contrast, compact result cards, raw −1..1 affinity scores, optional detailed statistics/provenance, resettable filters and a two-column mobile summary. Guidance is available in a collapsible explanation. Full exports retain the available source/identity fields.

League choice limits recommendations, similar-player reference/candidate pools, cluster plots and comparison choices. All-league exploration remains available. Scenario league is an explicit adjustable requirement; changing gallery scope clears stale scenario cases. Model/galleries and original exploratory mode remain selectable. Search/review events occur only on explicit actions.

Existing provisional reported-value links are reused where supported. New foreign identities are not matched by name alone to assign prices. Unknown or unmatched values remain unknown and cannot pass budget screening. Without private uploads, ordinary five-league recommendations, similarity, clusters and comparisons work; budget scenarios remain unavailable. Price availability is not equivalent across leagues and must not be interpreted as a player-quality signal.

## Run the pushed application

Stop the current Streamlit process, then from your clone:

```bash
git pull --ff-only origin improve/reproducible-scouting
python -m streamlit run src/app/streamlit_app.py
```

Use Python 3.12 with `requirements.lock.txt` as before. No dependency change is needed to serve committed five-league galleries. `.gitattributes` preserves LF endings in source and generated CSV/JSON reports for Windows checksum portability. Native Windows execution of this update has not been independently verified here.

## Regenerate from real archives

For optional regeneration, install the existing `requirements-archives.txt` in addition to the main lock. From the retained workspace:

```bash
.venv/bin/python -m scripts.top_five_leagues
.venv/bin/python -m scripts.top_five_notebook
.venv/bin/python -m pytest -q --junitxml=reports/top_five_leagues/tests.xml
```

If pinned FBref archives are missing, `python -m scripts.top_five_leagues --download` attempts only those six existing FBref release URLs with checksum verification and pacing. Changed bytes, denied access or missing coverage stop the operation; no fallback data is generated. Mutable releases are not evidence that a pinned archive will remain downloadable. Preserve originals and provenance.

`python -m scripts.verify_top_five_leagues` verifies released code/data/evaluation fingerprints, notebook execution and recorded test results; its local health check expects a running Streamlit service on port8502. Raw archive checks are reported separately when originals are present. Full historical-pipeline audits still require retained private inputs, and earlier app/source fingerprint reports describe their historical versions.

This update supersedes the earlier single-league application and submission counts without rewriting immutable historical experiment artifacts. Actual transfer-success validation, genuine process data, private valuation restoration and advanced Segunda completeness remain separate limitations.
