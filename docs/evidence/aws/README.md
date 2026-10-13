# Evidencias AWS — ScoutIQ

Estimación oficial creada el **13/10/2026 a las 18:32**, región **Europe (Ireland)**.

## Configuración
- EC2: 1 × `t3.medium`, Linux, 2 vCPU, 4 GiB RAM, On-Demand, 100 % utilización.
- EBS: 50 GB; transferencia saliente configurada: 10 GB/mes.
- IPv4 pública: 1 en uso, 0 inactivas; monitorización adicional desactivada.

## Costes (USD)
| Servicio | Mensual | 12 meses |
|---|---:|---:|
| EC2 con EBS | 41,17 | 494,02 |
| IPv4 pública | 3,65 | 43,80 |
| **Total** | **44,82** | **537,84** |

Coste inicial: 0 USD. IPv4: 730 h × 0,005 USD/h = 3,65 USD/mes.

## Escenarios
- Local: sin contratación cloud (con costes indirectos).
- Cloud permanente: 44,82 USD/mes según la calculadora.
- Cloud para demostraciones: requiere cálculo separado según horas efectivas; EBS y otros recursos persistentes pueden seguir generando costes.

## Limitaciones
Estimación, no factura ni evidencia de despliegue. No incluye impuestos ni conversión EUR; el precio de EC2 agrupa cómputo y EBS y no separa el coste de transferencia. Backups, monitorización avanzada y almacenamiento externo no están presupuestados por separado. Un futuro despliegue productivo requeriría autenticación, HTTPS, copias de seguridad y monitorización.

[Estimación AWS Pricing Calculator](https://calculator.aws/#/estimate?id=5de04cff4f4167e7baf5ebdc7346fa5734f87989)

La exportación original se encuentra en `aws_estimate.json`. Las capturas pendientes de incorporar son `aws_estimate_summary.png`, `aws_ipv4_configuration.png` y `aws_ipv4_calculation.png`.
