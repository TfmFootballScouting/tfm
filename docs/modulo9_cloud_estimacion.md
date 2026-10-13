# Módulo 9 — Infraestructura cloud y estimación de costes

## Objetivo y dimensionamiento
Se estudia una infraestructura pequeña para demostrar ScoutIQ, no un despliegue productivo acreditado. La app Streamlit, MLflow y los modelos ligeros de scikit-learn pueden ejecutarse en CPU. La capacidad no se ha medido bajo carga real.

| Recurso | Configuración estimada |
|---|---|
| Proveedor | AWS |
| Región | Europe (Ireland), eu-west-1 |
| Instancia | EC2 `t3.medium`, Linux, 2 vCPU, 4 GiB RAM |
| Facturación | On-Demand, 730 horas/mes (100 % uso) |
| Almacenamiento | EBS, 50 GB |
| Transferencia saliente | 10 GB/mes, supuesto del calculador |
| IPv4 pública | Una dirección en uso |
| GPU | No |
| Base de datos | SQLite local en fase académica |
| Monitorización avanzada | No incluida |

## Evidencia oficial de costes (13/10/2026)
La exportación de **AWS Pricing Calculator**, en USD, se encuentra en [evidence/aws/aws_estimate.json](evidence/aws/aws_estimate.json) y su [README](evidence/aws/README.md). [Enlace compartido de la estimación](https://calculator.aws/#/estimate?id=5de04cff4f4167e7baf5ebdc7346fa5734f87989).

| Concepto | USD/mes | USD/12 meses |
|---|---:|---:|
| EC2 con EBS y supuestos de tráfico de la estimación | 41,17 | 494,02 |
| IPv4 pública (730 h × 0,005 USD/h) | 3,65 | 43,80 |
| **Total exportado** | **44,82** | **537,84** |

Importe inicial: 0 USD. Se conservan las cifras anuales de la exportación, sin recalcular importes redondeados. **No se debe utilizar el presupuesto antiguo de ~35 EUR/mes** como coste oficial.

El desglose independiente de compute, EBS, transferencia y backups no figura en el resumen JSON. El fichero `evidence/cloud/` es una hoja complementaria de hipótesis y fórmulas, **no otra cotización oficial**. Los costes de copias de seguridad, almacenamiento externo, monitorización adicional y las posibles peticiones no se han verificado por separado. No se incluye conversión a EUR sin un tipo de cambio fechado. Impuestos y consumo real pueden variar.

## Escenarios
- **A — Desarrollo local:** sin gasto directo de AWS; sí costes indirectos de equipos y electricidad.
- **B — Demostración cloud 24/7:** 44,82 USD/mes bajo los supuestos de la calculadora.
- **C — Demostración temporal:** iniciar la VM solo para pruebas; requiere una nueva cotización basada en horas reales, conservando posibles costes de EBS e IP pública.

## Seguridad y evolución
En una puesta en producción serían necesarios autenticación, HTTPS, gestión de secretos, monitorización, backups verificables, almacenamiento de artefactos externo, separación de la base operativa de MLflow y evaluación de escalado. Ninguna de estas medidas se presenta como ya desplegada.

## Evidencia pendiente
Incorporar al repositorio las tres capturas originales del calculador. La configuración no equivale a una factura ni prueba de infraestructura realmente desplegada.
