# TFM — Análisis y scouting de futbolistas

Sistema de recomendación por **afinidad con seis estilos de juego**, con datos reales FBref, modelos scikit-learn, MLflow y app Streamlit. Understat aporta análisis de tiros separado; las valoraciones reportadas se aplican después del ranking.

**Autores:** Iván Galán López, Basma Marso, Carlos Valencia Sánchez.

Rama para revisión: **`review/teacher-submission`**. Conserva la arquitectura y documentos originales, con las modificaciones actuales. La memoria original DOCX no se modifica. Estado de los 19 comentarios del profesor y propuestas pendientes: [TEACHER_FEEDBACK.md](docs/TEACHER_FEEDBACK.md).

## Qué incluye

- Raw CSV separados por FBref, Understat y Transfermarkt, con origen/hashes y exportación documentada.
- Limpieza, tasas por 90 y tablas CSV/Parquet reproducibles; ninguna sustitución sintética.
- Seis estilos expertos; recomendador Core de cinco ligas, KNN/distancia, K-means y PCA.
- Tres experimentos FBref reales conservados (Core, Offensive y Attack-on-Core); Core sirve la app.
- MLflow real con dataset/Git/tags, métricas y artefactos originales portables.
- Streamlit: ranking, similares, comparación multijugador e historial, grupos ajustables/PCA, evolución y tiros.
- Valores reportados con fecha, identidades provisionales y moneda EUR asumida; no estimador de precios.
- Tests bajo `src/tests/`; log operativo separado de MLflow.

## Quick start

Python **3.12**. Desde la raíz:

```powershell
git clone --branch review/teacher-submission --single-branch https://github.com/TfmFootballScouting/tfm.git
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

La entrada reconstruye `data/processed/review/` y verifica paridad numérica/identidades con la galería servida. **No reentrena ni sobrescribe modelos congelados.** Código: `src/preprocessing/review_dataset.py`, `collected.py` y helpers en `scripts/top_five_leagues.py`. CSV grandes se guardan como `.csv.gz`, además de Parquet.

Los entrenamientos completos originales están en `scripts/five_league_pipeline.py` (orquestación/MLflow), `src/models/collected.py` (cohortes/baselines/selección) y `src/models/recommend.py` (imputación/escalado/KNN/PCA/K-means). Para repetir esa ruta de archivos RDS instalar también `requirements-archives.txt` y restaurar los archives mediante `python -m src.scraping.raw_inputs --download`; véase [FIVE_LEAGUE_FULL_PIPELINE.md](docs/FIVE_LEAGUE_FULL_PIPELINE.md). No se afirma haber generado un nuevo entrenamiento por reorganizar esta entrega.

### MLflow UI

```powershell
python -m pip install -r requirements-research.lock.txt
python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 127.0.0.1 --port 5000
```

La DB local no se incluye en Git. La evidencia original del run principal está en `reports/five_league_pipeline/mlflow_export/core/`, con `run.json`, evaluación y modelo. Una DB vacía de un clon no muestra automáticamente los runs históricos. Capturas reales/reproducción se detallan en la matriz del profesor; no se presentan screenshots inexistentes.

## Estructura

```text
tfm/
├── data/
│   ├── raw/{fbref,understat,transfermarkt}/  # CSV fuente y manifiesto de procedencia
│   └── processed/{review,real}/             # CSV/Parquet limpios y artefactos servidos
├── docs/                  # documentos originales, diccionario y revisión del profesor
├── models/                # recommender.joblib/metrics.json actuales; comparativas en real/
├── notebooks/             # EDA por fuente, análisis de modelos y etapas históricas
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
├── scripts/               # reproducción, ingesta y MLflow
└── reports/               # evidencia/diccionarios/plots/runs originales y revisión
```

Se usa la grafía original `scraping` y `preprocessing` para conservar imports. `requirements.txt` contiene solo 8 dependencias directas de app; `requirements-research*` separa notebooks/MLflow/tests; `requirements-archives.txt` es opcional para RDS.

## Estilos de juego

| Clave | Nombre |
|---|---|
| posesion | Posesión / construcción |
| presion_alta | Presión alta |
| vertical | Juego vertical / directo |
| contraataque | Contraataque |
| solidez_defensiva | Solidez defensiva |
| desborde_banda | Desborde / banda |

Son pesos expertos sobre estadísticas estandarizadas, no seis modelos supervisados. Core usa nueve tasas por 90; Euclidean profile es el método elegido con validación. La PCA guardada tiene cuatro componentes y K-means dos grupos; la exploración permite otros números de grupos sin reentrenar el recomendador.

## Datos

- **FBref:** seis categorías, cinco ligas, 15.948 registros jugador/liga/temporada y 7.398 filas de galería; 1.810 candidatos en 2023/24. Joins por ID de fuente + club + liga + temporada y compatibilidad de exposición.
- **Understat:** 228.785 tiros de cinco ligas; no se inventan minutos/posiciones ni se unen identidades sin revisión.
- **Transfermarkt:** cuatro CSV del usuario con origen `salimt/football-datasets` declarado, no commit verificado. 901.429 valores fechados; moneda asumida EUR, no fees, no features de entrenamiento. En 2023/24, 1.601 perfiles tienen valor positivo utilizable al último cutoff disponible; no son necesariamente precios de 2023/24.

FBref/Understat fueron descargados como **RDS desde GitHub**, después exportados a CSV con el subconjunto objetivo sin limpiar campos. No se llaman falsamente CSV descargados directamente. Los uploads de Transfermarkt se copian byte a byte. `data/raw/review_manifest.json` documenta esa diferencia. Originales RDS/receipts se preservan localmente; el scraping original no es la ruta de datos de los experimentos actuales.

Los datasets originales mixtos/demo y los reportes antiguos se conservan como evidencia de etapas anteriores; **no entran en `src.pipeline` ni en los experimentos finales**. El periodo 2025/26 es parcial; Segunda no es una galería táctica actual. No se añade transfer likelihood ni predicción futura.

## Notebooks y validación

Orden recomendado para el profesor:

1. [FBref EDA](notebooks/fbref_eda.ipynb): calidad, nulos, distribuciones/outliers, correlación y posiciones/ligas/temporadas.
2. [Understat EDA](notebooks/understat_eda.ipynb): tiros, xG, cobertura, nulos, perfiles ofensivos y límites.
3. [Transfermarkt EDA](notebooks/transfermarkt_eda.ipynb): perfiles, valores fechados, ceros/nulos/outliers y uso restringido.
4. [Modelos y validación](notebooks/11_five_league_full_pipeline.ipynb): splits temporales, baselines, PCA/K-means, bootstrap y MLflow.

Los notebooks numerados anteriores conservan resultados de sus etapas, no métricas del dataset actual. El análisis de escenarios permanece académico, sin pestaña adicional en la app.

Core holdout: MRR 0,095498; Recall@5 12,95%; Recall@10 19,51%. La tarea recupera la identidad estadística futura del mismo jugador; **no demuestra éxito de fichajes**. Validación experta y transferencia real permanecen pendientes.

## Tests

```powershell
python -m pip install -r requirements-research.lock.txt
python -m pytest -q
```

El workflow CI ejecuta un conjunto portable de contratos/modelo/UI/datos actuales; las pruebas completas incluyen integraciones históricas que requieren archivos originales locales y lectores opcionales. El informe de revisión distingue tests completos en el workspace de smoke tests de un clon limpio; no afirma que un hosted CI con entradas ausentes haya pasado. Fixtures artificiales son solo pruebas unitarias.

## Documentación

| Documento | Contenido |
|---|---|
| [modulo2_caso_uso.md](docs/modulo2_caso_uso.md) | Problema, alcance actual y validación experta propuesta |
| [modulo9_process_mining.md](docs/modulo9_process_mining.md) | AS-IS/TO-BE, UUID, eventos existentes y límites |
| [modulo9_cloud_estimacion.md](docs/modulo9_cloud_estimacion.md) | Estimación histórica, evidencia pendiente y producción futura |
| [modulo9_evidencias.md](docs/modulo9_evidencias.md) | Evidencia real y pendientes |
| [memoria_resumen.md](docs/memoria_resumen.md) | Resumen técnico actualizado |
| [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | Variables, cálculos, unidades y gaps explícitos |
| [TEACHER_FEEDBACK.md](docs/TEACHER_FEEDBACK.md) | Los 19 comentarios: arreglado/parcial/propuesto/manual |

## Stack

Python 3.12, pandas, NumPy/SciPy, scikit-learn, Parquet/CSV, Plotly, Streamlit. MLflow, Matplotlib/Seaborn, Jupyter y pytest en entorno research. SQLite de MLflow no sustituye una base operativa de decisiones; esa mejora espera aprobación.
