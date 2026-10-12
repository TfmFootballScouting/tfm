# Models included for review

- `recommender.joblib` is an unchanged copy of the current evaluated five-league Core artifact, under the original project's filename.
- `metrics.json` contains that model's actual holdout metrics, dataset version, original training Git commit and relative paths.
- `real/five_league_core_recommender.joblib` is the same binary used by Streamlit; the model/data/source checksum manifests remain authoritative.
- `real/five_league_offensive_recommender.joblib` and `real/five_league_attack_on_core_recommender.joblib` are actual comparison experiments, not app selectors.
- Earlier `real/collected_*` and `enrichment_*` artifacts support historical comparisons and preserved evidence.
- `historical/legacy_mixed_recommender.joblib` and `legacy_metrics.json` retain the original mixed/demo artifact for traceability only. They never serve the app or validate final experiments.

No new fit is claimed merely because these files were organized. No transfer-likelihood or value-estimation model is deployed. Six styles are expert weights; PCA/K-means are unsupervised components, not six supervised models.
