"""Experimento minimo MLflow para el TFM de scouting."""
import mlflow
import hashlib
import platform
import subprocess
from src.config import ROOT
import mlflow.sklearn
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

def main() -> None:
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    experiment = "tfm-scouting-synthetic-demonstrations"
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location="./mlartifacts/synthetic-demonstrations")
    mlflow.set_experiment(experiment)

    rng = np.random.default_rng(42)
    n_players, n_features = 200, 12
    X = rng.normal(size=(n_players, n_features))

    n_neighbors = 5
    metric = "cosine"

    with mlflow.start_run(run_name="knn_cosine_demo_v1"):
        mlflow.set_tags({"dataset_kind": "synthetic_demonstration", "project": "tfm-scouting", "owner": "tfm-team", "dataset": hashlib.sha256(X.tobytes()).hexdigest(), "environment": platform.python_version(), "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()})
        mlflow.log_param("dataset", "sintetico_demo")
        mlflow.log_param("n_players", n_players)
        mlflow.log_param("n_features", n_features)
        mlflow.log_param("algoritmo", "NearestNeighbors")
        mlflow.log_param("metric", metric)
        mlflow.log_param("n_neighbors", n_neighbors)

        pipe = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("nn", NearestNeighbors(n_neighbors=n_neighbors, metric=metric)),
            ]
        )
        pipe.fit(X)

        distances, _ = pipe.named_steps["nn"].kneighbors(
            pipe.named_steps["scaler"].transform(X[:10])
        )
        mean_dist = float(np.mean(distances[:, 1:]))
        mlflow.log_metric("mean_neighbor_distance_sample", mean_dist)
        mlflow.sklearn.log_model(pipe, name="model")
        print(f"Run OK. mean_neighbor_distance_sample={mean_dist:.4f}")

if __name__ == "__main__":
    main()
