# ScoutIQ interface

The app serves one audited five-league Core recommender and the six original playing styles. Scouts choose football requirements; model type, training selection and technical model metrics are no longer app controls. Older model artifacts and experiments remain preserved.

- **Ligas:** select one or several of La Liga, Premier League, Bundesliga, Serie A and Ligue 1. An empty selection requests at least one league. Recommendations, reference players, comparisons, groups and scenarios respect the selected market. Changing filters clears stale search/scenario cases.
- **Estilo de juego:** retain the six original directions and weights. Complete profiles are available through 2023/24; the UI does not substitute incomplete newer data.
- **Football measurements:** readable Spanish labels, including “Goles por 90 min”, “Tiros a puerta por 90 min” and “Entradas ganadas por 90 min”, appear in tables, charts and scouting CSV exports. Position controls spell out the position.
- **Perfiles y comparación:** select any number of distinct players. Each selected player has a season profile and their own retained FBref history. A shared radar allows comparison using the same reference scale, with individual radars below it. Missing measurements are gaps, not zero.
- **Grupos de jugadores:** choose two to twelve groups, inspect group sizes and mean statistics, select a group and browse/export all its members. Grouping uses the chosen leagues and observed season with frozen training imputation/scaling; it fits a separate descriptive K-means and never mutates saved model clusters or recommendation rankings. Group identifiers can change with the market or group count.
- **Values:** retained uploaded reported market assessments are displayed with dates and provisional identity status. Unknown and ambiguous zero values are never estimated or accepted by the budget filter. When valuation files are absent or no positive linked valuations exist, valuation controls and budget scenarios are hidden. No private provider rows are committed to Git.

Technical PCA/K-means evaluation, temporal validation, baselines and robustness remain in [notebook 11](../notebooks/11_five_league_full_pipeline.ipynb). [Notebook 12](../notebooks/12_scouting_group_exploration.ipynb) executes descriptive separation diagnostics for the adjustable app groups and verifies that trained model artifacts remain unchanged. Exploratory silhouette diagnostics are not held-out transfer outcomes or optimal-group claims.

Run with `streamlit run src/app/streamlit_app.py`. Keep private valuation uploads and manifests on your local machine if you want price display/filtering; ordinary recommendations work without them. No pipeline rerun is required for this interface change.

Validation: **113 tests passed**, with no failures, errors or skips. Notebook 12 executed all three code cells without errors. Desktop/mobile browser checks found no JavaScript errors or mobile horizontal overflow, and both grouping/comparison tabs loaded. See `reports/scout_ui/verification.json` and `reports/scout_ui/tests.xml`.
