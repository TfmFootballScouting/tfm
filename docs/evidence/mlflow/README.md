# Actual MLflow run evidence

`main_experiment.png` is an unmodified browser screenshot of the existing local MLflow run `85b7e82117814713b9094a5385308f6f`, experiment 6, FINISHED. Capture metadata and SHA256 are in `capture.json`. It shows the original dataset hash, training Git commit, parameters and five recorded metrics. The short logged run duration is the logging interval; it must not be described as total training wall time.

`evaluation_artifacts.png` shows the original evaluation artifact directory in the same run; its SHA256 is also recorded.

The portable experiment export remains at `reports/five_league_pipeline/mlflow_export/scouting/`: `run.json` and `artifact_manifest.json`, referencing the single-copy original figures/CSV files in `reports/five_league_pipeline/` and model files in `models/`, with exact SHA256 hashes. This screenshot is evidence of that existing local run; a fresh clone does not contain the private local MLflow SQLite database. Training/relogging is a separate reproducible workflow documented in README. No new fit or improvement in metrics is claimed by capturing this evidence.

The original run name visible in these historical screenshots predates the single-recommender correction. It is preserved as evidence and is not a current app model choice.
