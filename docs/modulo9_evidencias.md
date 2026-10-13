# Módulo 9 — Evidencias y pendientes (revisión 13/10/2026)

## Evidencias actuales verificables en el repositorio
- **Datos y reproducibilidad:** `data/raw/source_manifest.json`, `data/processed/manifest.json`, `docs/DATA_SOURCES.md`, `docs/DATA_DICTIONARY.md`.
- **Modelado:** un único recomendador actual de seis estilos en `models/scouting_recommender.joblib`, evaluación en `notebooks/04_feature_comparison_and_model_validation.ipynb` y `reports/five_league_pipeline/`. Los métodos alternativos son comparaciones, no modelos desplegados.
- **MLflow histórico:** `docs/evidence/mlflow/` conserva capturas de la ejecución anterior `85b7e82117814713b9094a5385308f6f`. No representan la nueva ejecución local.
- **MLflow nuevo (capturas facilitadas, pendientes de subir):** experimento `tfm-scouting-six-styles-real`, run `five_league_scouting_real_refit`, finalizado el 13/10/2026. Las capturas muestran tags `owner`, `project`, `dataset`, `dataset_kind`, `environment`, `git_commit`; siete parámetros, cinco métricas y artefactos de evaluación y modelo. El hash de los archivos de captura y la exportación de este nuevo run aún no se han incorporado.
- **Process Mining:** `src/process/` registra solicitudes/eventos/feedback en almacenamiento operativo separado de MLflow. Véase `OPERATIONAL_TRACKING.md`.
- **Validación experta:** materiales preparados en `docs/expert_review/`; valoraciones humanas pendientes.
- **AWS:** `docs/evidence/aws/aws_estimate.json` y `README.md` documentan estimación oficial del 13/10/2026, 44,82 USD/mes (41,17 EC2 con EBS + 3,65 IPv4). Faltan las capturas originales en Git. La hoja `docs/evidence/cloud/` es complementaria, no la cotización oficial.

## Pendientes antes de entregar
1. Subir las nuevas capturas MLflow y sus metadatos/hashes; mantener las históricas claramente identificadas o archivadas.
2. Subir las tres capturas AWS y comprobar que la documentación cloud utiliza **44,82 USD/mes** y no el presupuesto histórico de ~35 EUR/mes.
3. Obtener valoraciones reales de expertos; no inventar resultados.
4. Obtener sesiones reales para analizar variantes de proceso; no tratar los tests como comportamiento humano.
5. Si se necesita coste en EUR, documentar tipo de cambio fechado. Desglosar con evidencia compute, EBS, egress y backup, o marcar costes no desglosados.
6. Verificar el checkout en Windows y las funciones de la aplicación antes de la defensa.

Consultar [TEACHER_FEEDBACK.md](TEACHER_FEEDBACK.md) para el estado detallado de las 19 observaciones.
