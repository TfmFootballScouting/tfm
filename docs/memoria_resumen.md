> Collected-data preprocessing update: real retained archives are now cleaned and audited across seasons without changing the original folder structure or fitted model. See [mandatory features, cohorts and executed EDA](COLLECTED_PREPROCESSING.md).

# Memoria técnica — primera entrega reproducible

Autores: Iván Galán López, Basma Marso, Carlos Valencia Sánchez.

## Problema y alcance

El objetivo es comparar candidatos de scouting mediante métricas observadas y criterios explícitos, no sustituir la decisión deportiva. El proyecto conserva su arquitectura Python, SQLite/Parquet, similitud coseno, KNN, PCA, K-means, MLflow y Streamlit. La mejora corrige mezcla de datos sintéticos, uniones por orden de filas y presupuestos inventados.

Se propone cobertura La Liga/Segunda 2020/21–2025/26, pero no se presenta como conseguida. FBref devuelve 403 en su política de acceso; Understat prohíbe rastreo en robots. Transfermarkt aporta una muestra actual de 50 valores y dos perfiles: no es un histórico por temporada ni un universo completo de fichajes. Véase [acceso y cobertura](SOURCE_ACCESS.md).

## Datos y metodología ejecutada

Los datos originales permanecen intactos. Hay 609 filas etiquetadas FBref 2023/24 y 840 sintéticas en el CSV original. El modo exploratorio excluye las sintéticas y las columnas cuya unión anterior no es fiable, y conserva 420 observaciones tras minutos mínimos y tratamiento de totales multiclub. La procedencia original sin HTML ni fecha queda explícitamente sin verificar; no valida los experimentos finales del TFM.

Se calculan tasas con minutos/90, conservando desconocidos como NULL. Se detectan duplicados contradictorios, se separa identidad de persona/observación y se exige DOB o revisión explícita para enlazar fuentes. El valor de mercado requiere fecha efectiva y fecha de conocimiento; no se estima con goles/edad. La transformación se ajusta solo sobre entrenamiento, y la evaluación histórica rechaza temporadas futuras.

## Modelado y análisis

La exploración disponible usa goles/asistencias por 90, sin G+A redundante. Los seis estilos tácticos amplios están deshabilitados por falta de métricas; solo se exponen perfiles descriptivos de finalización/asistencia. PCA de dos componentes sobre dos variables conserva el 100% de varianza por construcción, no demuestra una mejora. K-means segmenta niveles de producción ofensiva, no roles tácticos descubiertos.

Se ejecutan silhouette, estabilidad de clusters entre semillas, comparación de rankings con baselines lineal/minutos/G+A, perturbación de pesos y bootstrap de entrenamiento. Estas medidas son diagnósticos internos, no precisión de fichajes. La recuperación de perfil entre temporadas está implementada con baselines y métricas, pero no ejecutada sobre datos reales multitemporada por falta de cobertura. La validación contra transferencias y presupuestos históricos está bloqueada.

## Evidencia y limitaciones

Cuatro notebooks ejecutables contienen salidas, análisis de calidad, interpretaciones y apartados bloqueados. MLflow conserva dataset/hash, commit, estado de cambios, entorno, propietario y artefactos exportables. La aplicación permite ranking, filtros, similares, visualización y registro de acciones realmente observadas. Las pruebas de aplicación usan logs temporales, separados de sesiones reales.

No hay eventos genuinos de decisiones de un club: process mining y conclusiones de cuellos de botella no se afirman. Falta adquirir datos autorizados con IDs, temporadas, fechas y etiquetas para una validación final. Estado por requisito y comandos verificados: [informe de entrega](COMPLETION_REPORT.md). Diccionario: [DATA_DICTIONARY.md](DATA_DICTIONARY.md).
