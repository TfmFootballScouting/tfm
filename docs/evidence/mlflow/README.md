# MLflow — evidencia de la ejecución actual

Experimento: `tfm-scouting-six-styles-real`. Run: `five_league_scouting_real_refit`, ejecutado localmente el **13/10/2026**, estado **FINISHED**.

La ejecución actual usa `scripts/train_models.py`, datos reales FBref de cinco ligas y un único recomendador de seis estilos. El entrenamiento registra parámetros, métricas, tags (`owner`, `project`, `dataset`, `dataset_kind`, `environment`, `git_commit`) y artefactos bajo `evaluation/` y `models/`.

Métricas mostradas en las capturas facilitadas:
- Holdout MRR: **0,09549844955925278**
- Recall@5: **0,12954186413902052**
- Recall@10: **0,19510268562401265**
- Ranking bootstrap top-5 Jaccard: **0,9740740740740741**
- Cluster bootstrap ARI: **0,9819258990337122**

Estas métricas miden recuperación de perfiles estadísticos futuros y estabilidad, **no éxito de fichajes**. El experimento utiliza 30 repeticiones bootstrap y selecciona `euclidean_profile`, con K-Means `k=2`. Los seis estilos son criterios tácticos definidos por expertos, no seis clusters.

## Capturas actuales pendientes de incorporar al repositorio
1. `00_experiment_overview.png` — lista de runs y estado.
2. `01_run_details.png` — run ID, fecha, estado, dataset hash y Git commit.
3. `02_parameters_metrics.png` — siete parámetros y cinco métricas.
4. `03_artifacts.png` — artefactos `evaluation/` y `models/`.
5. `04_evaluation_graph.png` — comparación MRR, PCA y estabilidad.

**Importante:** las capturas anteriores de `docs/evidence/mlflow/` correspondían a un run histórico diferente y no deben utilizarse para acreditar la ejecución actual. La base de datos SQLite local no se versiona en Git.

Para reproducir: `python -m scripts.train_models`. Los resultados nuevos se guardan en `reports/retraining/<timestamp>/`. La interfaz se abre con `python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 127.0.0.1 --port 5000`.
