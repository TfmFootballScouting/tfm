# Módulo 9 — Evidencias ejecutadas y pendientes

## Evidencias existentes
- App y dependencia runtime separada: `requirements.txt` / `requirements.lock.txt`; research/test en `requirements-research*`.
- CSV raw con hashes/procedencia: `data/raw/review_manifest.json`; CSV/Parquet limpios: `data/processed/review/manifest.json`.
- Código de preprocessing: `src/preprocessing/review_dataset.py`, `collected.py`; CSV reconstruye las métricas de la galería congelada sin reentrenar.
- EDA por fuente: `notebooks/fbref_eda.ipynb`, `understat_eda.ipynb`, `transfermarkt_eda.ipynb`.
- Modelos reales y evaluación: `models/real/five_league_*`, `models/metrics.json`, notebook 11, `reports/five_league_pipeline/`.
- Run principal MLflow: `reports/five_league_pipeline/mlflow_export/core/run.json`; tags, parámetros, métricas y artefactos originales portables. El Git registrado corresponde al entrenamiento original.
- Tests implementados: `src/tests/`. El reporte de verificación de esta rama se guarda en `reports/teacher_review/` después de ejecutarlos.
- Registro de eventos y SQLite operativo: `src/process/events.py`, `store.py`; solicitudes, decisiones y feedback separados de MLflow. Véase `OPERATIONAL_TRACKING.md`.
- Capturas reales de MLflow: `docs/evidence/mlflow/core_run.png`, `core_artifacts.png`; hash y run ID en `capture.json`.
- Paquetes ciegos y análisis de expertos: `docs/expert_review/`, `notebooks/expert_validation.ipynb`; ratings pendientes.
- Hoja de costes ejecutable: `docs/evidence/cloud/`; tarifas sin evidencia quedan pendientes.

## Evidencias pendientes
- Ratings de scouts/entrenadores reales y validación de shortlist útil.
- Sesiones humanas para Process Mining y aceptación/decisiones.
- Captura/export oficial AWS, fecha y tipo de cambio verificado.
- Windows nativo y despliegue AWS no verificados por las pruebas Linux.

`TEACHER_FEEDBACK.md` detalla estados y acciones. No se inventan screenshots, tarifas actuales, precisión de fichajes ni proceso organizativo.
