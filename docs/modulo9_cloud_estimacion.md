> Revisión actual: los precios y el tipo de cambio de este documento se conservan como hipótesis históricas, no como cotización AWS verificada a la fecha de entrega. Falta captura/export de AWS Calculator, fecha y referencia de cambio. Compute, disco y transferencia están desglosados; backup/snapshots y request charges necesitan evidencia. Instrucciones en `TEACHER_FEEDBACK.md`.

# Módulo 9 — Estimación de recursos cloud

## 1. Premisas de carga
- Dataset pequeño: ~1.500–2.500 jugadores, >40 métricas
- Modelos ligeros: scikit-learn (similitud coseno, KNN, PCA, K-Means)
- App: Streamlit (pocos usuarios concurrentes en fase TFM/demo)
- Experiment tracking: MLflow (`sqlite:///mlflow.db` + artefactos en `mlruns/`)
- No se requiere Big Data (Spark) ni GPU

## 2. Arquitectura propuesta (fase TFM)
1 máquina virtual cloud (o local) que concentre:
- Pipeline de datos / entrenamiento
- MLflow Tracking UI/Server
- App Streamlit

Opcional futuro: almacenamiento de objetos (S3/Blob) para datos raw y artefactos.

## 3. Recursos estimados

| Recurso | Especificación | Justificación |
|---------|----------------|---------------|
| Compute (VM) | 2 vCPU, 4–8 GB RAM | Suficiente para pandas + sklearn + Streamlit + MLflow |
| Disco | 50 GB SSD (gp3 / equivalente) | SO + venv + datos + mlruns + modelos |
| Red / egress | < 10 GB/mes | Demo académica, poco tráfico |
| GPU | No | No hay deep learning |
| BD gestionada | No | SQLite basta en esta fase |
| Orquestación | No | Un solo servicio; sin Kubernetes |

## 4. Coste estimado (referencia calculadora AWS)

Valores orientativos tomados de precios públicos On-Demand (Linux), región **EU (Ireland) `eu-west-1`**, convertidos aprox. a EUR (1 USD ≈ 0,92 EUR).  
Equivalentes: **AWS t3.medium**, Azure B2s, GCP e2-medium.

| Concepto | Configuración | Coste mensual (USD) | Coste mensual (EUR ≈) |
|----------|---------------|---------------------|------------------------|
| VM compute | t3.medium, 2 vCPU, 4 GB, 730 h | ~33,29 $ | ~**30,60 €** |
| Disco EBS | 50 GB gp3 | ~4,00 $ | ~**3,70 €** |
| Transferencia | ~5 GB egress (estimado bajo) | ~0,45 $ | ~**0,40 €** |
| **Total escenario B (24/7)** | | ~37,7 $ | ~**34,70 €/mes** |

### Resumen para la entrega

- **Proveedor elegido:** AWS (referencia; Azure/GCP serían del mismo orden de magnitud)
- **Región:** eu-west-1 (Irlanda)
- **Instancia:** t3.medium (2 vCPU / 4 GB)
- **Coste mensual estimado VM:** ~30,60 €
- **Coste almacenamiento:** ~3,70 €
- **Coste total mensual estimado (24/7):** ~**35 €**
- **Coste anual estimado (24/7):** ~**420 €**

### Escenario B optimizado (solo demos)

Si la VM se enciende ~40 h/mes (demos y pruebas):

- Compute: 40 × 0,0456 $ ≈ 1,82 $ ≈ **1,70 €**
- Disco (sigue provisionado): ~**3,70 €**
- **Total ≈ 5–6 €/mes**

> Si el máster exige pegar capturas de *su* calculadora oficial, usar estos mismos parámetros (t3.medium / B2s / e2-medium, 50 GB, sin GPU) y sustituir los € por los de esa herramienta.

## 5. Escenarios

### A) Desarrollo TFM (recomendado ahora) — **elegido**
- Local + GitHub
- Coste cloud ≈ **0 €**
- MLflow en `sqlite:///mlflow.db`

### B) Demo en cloud
- 1 VM pequeña 24/7 ≈ **35 €/mes**, o solo horas de demo ≈ **5–6 €/mes**
- Misma máquina para Streamlit + MLflow

### C) Producto escalable (futuro)
- Contenedor Streamlit (Cloud Run / App Service)
- Object storage para datos
- MLflow en servidor dedicado o managed
- Posible BD (PostgreSQL) si crece el volumen

## 6. Conclusión
Para el volumen y algoritmos del TFM **no hace falta un cluster**. El desarrollo se hace en local (escenario A). Si se publica una demo, una VM tipo **t3.medium** (~35 €/mes 24/7, o ~6 €/mes a demanda) cubre entrenamiento, MLflow y Streamlit sin GPU ni servicios gestionados de BD.

## Mejoras futuras de producción (no desplegadas)

Autenticación y roles, HTTPS mediante proxy/TLS, gestión de secretos, monitorización de errores/latencias, backups probados con restauración, base operativa distinta de MLflow, retención de eventos, artefactos versionados en almacenamiento de objetos y escalado según concurrencia. No se presentan como capacidades ya desplegadas. El prototipo sirve 1.810 perfiles completos en su temporada más reciente, con histórico y tiros adicionales; la memoria requerida debe medirse para el escenario elegido, no asumirse a partir de filas antiguas.
