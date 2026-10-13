# Single six-style scouting recommender

`scouting_recommender.joblib` is the only saved recommendation model in this submission. It contains the fitted imputer/scaler, nearest-profile index, PCA and K-means. The six original styles are expert weights, not six separate classifiers.

`metrics.json` records the actual evaluation; `valuation_manifest.json` verifies the reported-value/identity inputs used after ranking. There is no separate value estimator or transfer predictor.

The notebook `04_feature_comparison_and_model_validation.ipynb` compares alternative attribute sets on the same cohort using the existing genuine results. Alternate fitted model files are not part of the current app or training workflow. `python -m scripts.train_models` fits one six-style recommender and writes a separate timestamped run without replacing this frozen artifact.

The original MLflow run name/code hashes remain immutable historical lineage. Current packaged source fingerprints are recorded separately. `src/models/recommend.py` is the compatibility import required by this original joblib; implementation lives in `recommender.py`.
