# TFM — Análisis y scouting de futbolistas

Sistema de recomendación por **afinidad con seis estilos de juego**, con datos reales FBref, modelos scikit-learn, MLflow y app Streamlit. Understat aporta análisis de tiros separado; las valoraciones reportadas se aplican después del ranking.

**Autores:** Iván Galán López, Basma Marso, Carlos Valencia Sánchez.



## Por dónde empezar

Para ejecutar la app, ve a **Quick start**. Para comprender el proyecto, lee los notebooks **01 → 06**. Para seguir el código, utiliza [PROJECT_MAP.md](docs/PROJECT_MAP.md): fuentes → limpieza → atributos/modelos → validación → Streamlit.

El notebook **04_feature_comparison_and_model_validation.ipynb** muestra los atributos comparados y la selección por validación. No realiza búsqueda exhaustiva de todas las combinaciones posibles.

## Qué incluye

- Raw CSV separados por FBref, Understat y Transfermarkt, con origen/hashes y exportación documentada.
- Limpieza, tasas por 90 y tablas CSV/Parquet reproducibles; ninguna sustitución sintética.
- Seis estilos expertos; recomendador de cinco ligas, KNN/distancia, K-means y PCA.
- Un único recomendador con seis estilos. Las comparaciones de atributos quedan solo en el notebook de análisis; no hay modelos Core/Offensive separados.
- MLflow real con dataset/Git/tags, métricas y artefactos originales portables.
- Streamlit: ranking, similares, comparación multijugador e historial, grupos ajustables/PCA, evolución y tiros.
- Valores reportados con fecha, identidades provisionales y moneda EUR asumida; no estimador de precios.
- Tests bajo `src/tests/`; log operativo separado de MLflow.

## Quick start

Python **3.12**. Desde la raíz:

```powershell
git clone https://github.com/TfmFootballScouting/tfm.git
cd tfm
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m pip check
```

Linux/macOS: activar con `source .venv/bin/activate`.

### Opción A — Usar datos/modelo ya generados

```powershell
python -m streamlit run src/app/streamlit_app.py
```

Modelo, galerías, históricos, tiros de cinco ligas y valoraciones preparadas están incluidos. No hay que entrenar ni copiar un ZIP de valoraciones para usar el filtro. No se ofrecen datos completos actuales: la última galería de seis estilos es 2023/24.

### Opción B — Reproducir limpieza desde los CSV incluidos

```powershell
python -m pip install -r requirements-research.lock.txt
python -m src.pipeline
```

La entrada reconstruye `data/processed/`; la app y los notebooks utilizan las mismas tablas. Se verifican hashes de fuentes, enlaces de identidad y entradas del recomendador. **No reentrena ni sobrescribe modelos congelados.** Código: `src/preprocessing/prepare_datasets.py`, `football_stats.py` y helpers en `src/preprocessing/fbref_categories.py`. CSV grandes se guardan como `.csv.gz`, además de Parquet.

El entrenamiento/evaluación reproducible desde los CSV incluidos está en `scripts/train_models.py` (orquestación/MLflow), `src/models/experiments.py` (cohortes/baselines/selección) y `src/models/recommender.py` (imputación/escalado/KNN/PCA/K-means). La orquestación se adaptó a la entrega limpia; los resultados y hashes del entrenamiento original permanecen documentados. Para entrenar sin sobrescribir los modelos incluidos:

```powershell
python -m scripts.train_models
```

Guarda nuevos resultados en `reports/retraining/<fecha>/`. Para una comprobación breve del flujo completo: `python -m scripts.train_models --bootstrap-trials 2`. Dos repeticiones son una comprobación de ejecución, no sustituyen la validación original con 30 repeticiones. No es necesario reentrenar para abrir la app.

### MLflow UI

```powershell
python -m pip install -r requirements-research.lock.txt
python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 127.0.0.1 --port 5000
```

La DB local no se incluye en Git. La evidencia original del run principal está en `reports/five_league_pipeline/mlflow_export/scouting/`, con `run.json` y un `artifact_manifest.json` que enlaza las copias únicas de evaluación/modelo con sus SHA256. Una DB vacía de un clon no muestra automáticamente los runs históricos. Las capturas reales del run original están en `docs/evidence/mlflow/`.

## Estructura

```text
tfm/
├── data/
│   ├── raw/{fbref,understat,transfermarkt}/  # CSV fuente y manifiesto de procedencia
│   └── processed/             # CSV/Parquet limpios y artefactos servidos
├── docs/                  # documentos originales y diccionario
├── models/                # scouting_recommender.joblib/metrics.json: un único modelo con seis estilos
├── notebooks/             # tres EDA, validación de modelos, grupos y revisión experta
├── src/
│   ├── scraping/          # código original/archivos publicados; no crawling nuevo implícito
│   ├── preprocessing/     # limpieza y reconstrucción de CSV
│   ├── features/          # seis estilos y contrato de features
│   ├── models/            # recomendación, ajuste y evaluación
│   ├── app/               # Streamlit
│   ├── data/              # identidad, procedencia, restricciones
│   ├── process/           # event log operativo
│   ├── tests/             # pruebas de componentes implementados
│   └── pipeline.py
├── scripts/               # solo reproducción/EDA/diccionario/MLflow necesarios
└── reports/               # solo evaluación actual y reporte final de revisión
```

Se usa la grafía original `scraping` y `preprocessing` para conservar imports. `requirements.txt` contiene solo 8 dependencias directas de app; `requirements-research*` separa notebooks/MLflow/tests.

## Estilos de juego

| Clave | Nombre |
|---|---|
| posesion | Posesión / construcción |
| presion_alta | Presión alta |
| vertical | Juego vertical / directo |
| contraataque | Contraataque |
| solidez_defensiva | Solidez defensiva |
| desborde_banda | Desborde / banda |

Son pesos expertos sobre estadísticas estandarizadas, no seis modelos supervisados. El recomendador usa nueve tasas por 90; Euclidean profile es el método elegido con validación. La PCA guardada tiene cuatro componentes y K-means dos grupos; la exploración permite otros números de grupos sin reentrenar el recomendador.

## Datos

- **FBref:** seis categorías, cinco ligas, 15.948 registros jugador/liga/temporada y 7.398 filas de galería; 1.810 candidatos en 2023/24. Joins por ID de fuente + club + liga + temporada y compatibilidad de exposición.
- **Understat:** 228.785 tiros de cinco ligas; no se inventan minutos/posiciones ni se unen identidades sin revisión.
- **Transfermarkt:** cuatro CSV del usuario con origen `salimt/football-datasets` declarado, no commit verificado. 901.429 valores fechados; moneda asumida EUR, no fees, no features de entrenamiento. En 2023/24, 1.601 perfiles tienen valor positivo utilizable al último cutoff disponible; no son necesariamente precios de 2023/24.

FBref/Understat fueron descargados como **RDS desde GitHub**, después exportados a CSV con el subconjunto objetivo sin limpiar campos. No se llaman falsamente CSV descargados directamente. Los uploads de Transfermarkt se copian byte a byte. `data/raw/source_manifest.json` documenta esa diferencia. Originales RDS/receipts se preservan localmente; el scraping original no es la ruta de datos de los experimentos actuales.

Se han retirado de esta rama los datasets demo/mixtos, modelos antiguos, escenarios, transfer likelihood, scripts abandonados y reportes históricos. La versión anterior queda accesible en el historial Git; no forma parte de esta entrega limpia. El periodo 2025/26 es parcial; Segunda no es una galería táctica actual. No se añade transfer likelihood ni predicción futura.

## Notebooks y validación


1. [FBref EDA](notebooks/01_fbref_data_exploration.ipynb): calidad, nulos, distribuciones/outliers, correlación y posiciones/ligas/temporadas.
2. [Understat EDA](notebooks/02_understat_data_exploration.ipynb): tiros, xG, cobertura, nulos, perfiles ofensivos y límites.
3. [Transfermarkt EDA](notebooks/03_transfermarkt_data_exploration.ipynb): perfiles, valores fechados, ceros/nulos/outliers y uso restringido.
4. [Modelos y validación](notebooks/04_feature_comparison_and_model_validation.ipynb): splits temporales, baselines, PCA/K-means, bootstrap y MLflow.

Solo se incluyen seis notebooks: los tres EDA, validación de los modelos actuales, exploración de grupos y revisión experta. No se incluyen notebooks de etapas abandonadas.

Holdout del recomendador: MRR 0,095498; Recall@5 12,95%; Recall@10 19,51%. La tarea recupera la identidad estadística futura del mismo jugador; **no demuestra éxito de fichajes**. Validación experta y transferencia real permanecen pendientes.

## Tests

```powershell
python -m pip install -r requirements-research.lock.txt
python -m pytest -q
```

El conjunto de tests de esta rama utiliza únicamente los archivos incluidos. Fixtures artificiales se usan solo en pruebas unitarias, nunca en los experimentos finales.

## Documentación

| Documento | Contenido |
|---|---|
| [modulo2_caso_uso.md](docs/modulo2_caso_uso.md) | Problema, alcance actual y validación experta propuesta |
| [modulo9_process_mining.md](docs/modulo9_process_mining.md) | AS-IS/TO-BE, UUID, eventos existentes y límites |
| [modulo9_cloud_estimacion.md](docs/modulo9_cloud_estimacion.md) | Estimación histórica, evidencia pendiente y producción futura |
| [modulo9_evidencias.md](docs/modulo9_evidencias.md) | Evidencia real y pendientes |
| [memoria_resumen.md](docs/memoria_resumen.md) | Resumen técnico actualizado |
| [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | Variables, cálculos, unidades y gaps explícitos |

## Stack

Python 3.12, pandas, NumPy/SciPy, scikit-learn, Parquet/CSV, Plotly, Streamlit. MLflow, Matplotlib/Seaborn, Jupyter y pytest en entorno research. SQLite operativo para solicitudes/decisiones es independiente de MLflow; los registros de participantes permanecen locales.


### Limpieza de la entrega

Se conserva la estructura original `data/`, `docs/`, `models/`, `notebooks/` y `src/{app,models,preprocessing,scraping,tests}`. Las carpetas `features`, `data` y `process` dentro de `src` son dependencias reales de la aplicación; `scripts` contiene los ejecutables de reproducción y `reports` los resultados actuales revisables. No hay una carpeta de tests duplicada en la raíz. [DATA_SOURCES.md](docs/DATA_SOURCES.md) explica el recorrido exacto de las fuentes y el código correspondiente.

Los datos preparados están directamente en `data/processed/`, sin carpetas `review`/`real` ni copias separadas para la app. Consulta [el inventario de datasets](data/processed/README.md).
