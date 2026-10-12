# Current trained models

- `recommender.joblib`: frozen real five-league Core model used by Streamlit.
- `offensive_recommender.joblib`: current offensive-feature comparison experiment.
- `attack_on_core_recommender.joblib`: attacking-feature comparison on the Core cohort.
- `metrics.json`: actual Core evaluation and portable serving metadata.
- `real/valuation_manifest.json`: verified paths/hashes for the reported-value display inputs; no valuation model is used.

The fitted Core contains the imputer, scaler, neighbors, PCA and K-means. Six styles are expert-defined weights. No legacy, synthetic or transfer-likelihood model is included. Original binary hashes and training commit are preserved in `reports/five_league_pipeline/pipeline.json`. MLflow artifact manifests refer to these same files instead of storing duplicate binaries.

`python -m scripts.five_league_pipeline` fits new experiments from bundled real CSVs and writes a separate timestamped folder, leaving these original served models unchanged.
