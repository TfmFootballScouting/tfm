# Documentación del TFM — ScoutIQ

**Rama para revisión:** `review/teacher-submission`. Esta carpeta reúne la documentación que aporta información distinta y comprobable; los resúmenes y guías duplicadas se han eliminado. El historial Git permite recuperar los archivos antiguos.

## Qué debe leer el profesor
1. [Caso de uso — Módulo 2](modulo2_caso_uso.md): problema de scouting y alcance.
2. [Fuentes y reproducibilidad](DATA_SOURCES.md): origen FBref/Understat/Transfermarkt, joins y límites.
3. [Diccionario de datos](DATA_DICTIONARY.md): definiciones, unidades, claves y tasas por 90. Los CSV `data_dictionary_raw.csv` y `data_dictionary_review.csv` son catálogos completos de campos; no duplican la explicación metodológica.
4. [Process Mining — Módulo 9](modulo9_process_mining.md) y [registro operativo](OPERATIONAL_TRACKING.md).
5. [Cloud — Módulo 9](modulo9_cloud_estimacion.md): estimación oficial AWS de **44,82 USD/mes**, no los costes históricos.
6. [Comentarios del profesor](TEACHER_FEEDBACK.md): matriz de observaciones y pendientes, actualizada.

## Evidencias
- [AWS](evidence/aws/README.md): JSON oficial y enlace de AWS Pricing Calculator (13/10/2026). Faltan las tres capturas originales PNG en Git.
- [MLflow](evidence/mlflow/README.md): ejecución local `five_league_scouting_real_refit` del 13/10/2026. Capturas nuevas pendientes de subir; no utilizar capturas del run histórico.
- [Hoja de trabajo cloud](evidence/cloud/README.md): cálculos auxiliares, no otra cotización oficial.
- [Revisión experta](expert_review/README.md): paquetes y metodología; no se han recibido valoraciones humanas.

## Cómo ejecutar y revisar
Desde la raíz del repositorio, Python 3.12:
```powershell
python -m pip install -r requirements.lock.txt
python -m streamlit run src/app/streamlit_app.py
```

Para reconstruir datos desde los CSV incluidos: instalar `requirements-research.lock.txt` y ejecutar `python -m src.pipeline`. Esto **no reentrena** el modelo. Para una nueva evaluación real y un run MLflow: `python -m scripts.train_models`, que escribe en `reports/retraining/<timestamp>/`.

La aplicación usa **un recomendador con seis estilos definidos por expertos**, no seis modelos. Compara métodos y atributos en `notebooks/04_feature_comparison_and_model_validation.ipynb`; los notebooks 01–03 contienen EDA por fuente, el 05 analiza grupos/PCA y el 06 prepara validación experta (ratings pendientes).

## Mapa mínimo del código
| Etapa | Código |
|---|---|
| Datos raw y origen | `data/raw/source_manifest.json`, `src/scraping/` (parsers originales, no ingesta actual) |
| Limpieza y uniones | `src/pipeline.py`, `src/preprocessing/prepare_datasets.py`, `football_stats.py`, `fbref_categories.py` |
| Entrenamiento y validación | `scripts/train_models.py`, `src/models/experiments.py`, `robustness_validation.py` |
| Modelo | `src/models/recommender.py`, `src/features/styles.py` |
| App | `src/app/streamlit_app.py`, `scouting_service.py`, `model_loader.py` |
| Proceso operativo | `src/process/`, independiente de MLflow |
| Tests | `src/tests/`; ejecutar `python -m pytest -q` |

**Interpretación:** MRR/Recall evalúan recuperación temporal de perfiles del mismo jugador, **no éxito real de fichajes**. La valoración de mercado es un filtro posterior al ranking, no un objetivo de entrenamiento. K-Means tiene `k=2` y no representa los seis estilos.

**Pendiente de evidencia:** capturas nuevas MLflow, capturas AWS, ratings de expertos, sesiones humanas para Process Mining y verificación nativa Windows. No se afirma despliegue productivo.
