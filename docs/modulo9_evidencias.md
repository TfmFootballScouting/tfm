# Evidencias ejecutadas y pendientes

- Python 3.12 y dependencias: `scripts/setup.sh`, `requirements.lock.txt`, pip check.
- Pruebas: `reports/verification.json`; tests funcionales de ranking/filtros/similares/Streamlit y protección contra leakage.
- Notebooks: cuatro `.ipynb` ejecutados; `reports/notebook_execution.json`.
- MLflow: experimento separado `tfm-scouting-legacy-exploratory`; `reports/mlflow_export/run.json` y artefactos reales del run.
- Cobertura y bloqueos: `reports/source_coverage.csv`, `reports/transfermarkt_sample_access.csv`, `docs/SOURCE_ACCESS.md`.
- Datos originales preservados; los resultados antiguos mezclados con sintéticos no validan el TFM.

No se presentan capturas, validación de fichajes, métricas de precisión o descubrimiento de un proceso humano que no se hayan obtenido. El demo sintético mantiene su propio experimento y no se ha ejecutado para esta entrega. Véase `COMPLETION_REPORT.md` para estados completos.
