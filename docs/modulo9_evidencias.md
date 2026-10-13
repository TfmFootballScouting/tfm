# Módulo 9 — Evidencias ejecutadas y pendientes

## Evidencias existentes
- App y dependencia runtime separada: `requirements.txt` / `requirements.lock.txt`; research/test en `requirements-research*`.
- CSV raw con hashes/procedencia: `data/raw/source_manifest.json`; CSV/Parquet limpios: `data/processed/manifest.json`.
- Código de preprocessing: `src/preprocessing/prepare_datasets.py`, `football_stats.py`; CSV reconstruye las métricas de la galería congelada sin reentrenar.
- EDA por fuente: `notebooks/01_fbref_data_exploration.ipynb`, `02_understat_data_exploration.ipynb`, `03_transfermarkt_data_exploration.ipynb`.
- Modelos reales y evaluación: `models/scouting_recommender.joblib` y los dos modelos de comparación, `models/metrics.json`, notebook 04, `reports/five_league_pipeline/`.
- Run principal MLflow: `reports/five_league_pipeline/mlflow_export/scouting/run.json`; tags, parámetros, métricas y artefactos originales portables. El Git registrado corresponde al entrenamiento original.
- Tests implementados: `src/tests/`. El reporte de verificación de esta rama se guarda en `reports/teacher_review/` después de ejecutarlos.
- Registro de eventos y SQLite operativo: `src/process/events.py`, `store.py`; solicitudes, decisiones y feedback separados de MLflow. Véase `OPERATIONAL_TRACKING.md`.
- Capturas reales de MLflow: `docs/evidence/mlflow/main_experiment.png`, `evaluation_artifacts.png`; hash y run ID en `capture.json`.
- Paquetes ciegos y análisis de expertos: `docs/expert_review/`, `notebooks/06_expert_recommendation_validation.ipynb`; ratings pendientes.
- Hoja de costes ejecutable: `docs/evidence/cloud/`; tarifas sin evidencia quedan pendientes.

## Evidencias pendientes
- Ratings de scouts/entrenadores reales y validación de shortlist útil.
- Sesiones humanas para Process Mining y aceptación/decisiones.
- Captura/export oficial AWS, fecha y tipo de cambio verificado.
- Windows nativo y despliegue AWS no verificados por las pruebas Linux.

`TEACHER_FEEDBACK.md` detalla estados y acciones. No se inventan screenshots, tarifas actuales, precisión de fichajes ni proceso organizativo.
