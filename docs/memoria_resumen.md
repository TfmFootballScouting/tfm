# Memoria técnica — entrega para revisión

Autores: Iván Galán López, Basma Marso, Carlos Valencia Sánchez.

El TFM mantiene su problema y arquitectura original: scouting por seis estilos expertos, Python/scikit-learn, KNN, PCA, K-means, MLflow y Streamlit. La entrega actual usa datos reales separados por fuente y evita valores inventados, mezclas sintéticas y uniones por orden de filas.

## Datos y preparación
Los CSV revisables están en `data/raw/fbref/`, `understat/` y `transfermarkt/`; su manifiesto distingue GitHub/RDS, uploads y transformaciones. `python -m src.pipeline` reproduce tablas limpias de CSV y verifica paridad numérica con la galería congelada, sin reentrenar ni sustituir artefactos. Los outputs CSV/Parquet están en `data/processed/review/` y la app conserva los Parquet con checksums de `data/processed/real/`.

FBref: 15.948 registros jugador/liga/temporada; galería 7.398, con 1.810 candidatos en 2023/24. Understat: 228.785 tiros explorables, independientes del modelo. Transfermarkt: 901.429 observaciones de valor reportado; no fees, no estimaciones ML, moneda asumida EUR y enlaces provisionales. No se presenta Segunda ni 2025/26 como galería táctica completa.

## Modelos y resultados existentes
Core cinco ligas sirve la aplicación; Offensive y Attack-on-Core son experimentos comparativos. Se ajustan imputación/escalado/PCA/clusters únicamente en entrenamiento. La selección usa validación temporal y el holdout evalúa recuperación de perfiles: Core MRR 0,095498; Recall@5 0,129542; Recall@10 0,195103. Estos números no son precisión de fichajes. PCA/K-means y rankings tienen análisis de estabilidad, loadings, cohortes y baselines en el notebook 11 y exports reales de MLflow.

## Aplicación y pruebas
Filtros de liga múltiple, posición, edad, minutos y valor reportado; seis estilos; similares; comparación multijugador/historiales; grupos ajustables con mapa PCA; evolución y tiros. No existe página separada de escenarios ni predictor de transferencias. Tests bajo `src/tests/`; fixtures artificiales se limitan a pruebas, nunca a experimentos finales.

## Trazabilidad y revisión del profesor
MLflow registra owner, dataset, environment, project, hash/versiones, Git original y artefactos. SQLite operativo guarda solicitudes, eventos, decisiones y feedback con UUID; JSONL es el log/export. No existen aún sesiones humanas validadas. Las capturas reales de MLflow están incluidas; revisión experta y evidencia oficial AWS/tipo de cambio permanecen pendientes. La matriz de los 19 comentarios y siguientes acciones está en `TEACHER_FEEDBACK.md`.
