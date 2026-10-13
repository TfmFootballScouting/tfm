# Índice de documentación — ScoutIQ

Este directorio contiene documentación técnica, entregables de módulos y evidencias. La versión de trabajo para el profesor es la rama `review/teacher-submission`.

## Empezar
1. [Guía de revisión](REVIEW_GUIDE.md): orden de lectura y límites de la entrega.
2. [Mapa del proyecto](PROJECT_MAP.md): dónde está el código y cómo usarlo.
3. [Resumen de memoria](memoria_resumen.md): descripción técnica del TFM.
4. [Comentarios del profesor](TEACHER_FEEDBACK.md): estado de las 19 observaciones.

## Datos y metodología
- [Fuentes y reproducibilidad](DATA_SOURCES.md)
- [Diccionario de datos](DATA_DICTIONARY.md)
- [Validación experta](expert_review/README.md): materiales preparados; las evaluaciones humanas siguen pendientes.

## Módulos
- [Módulo 2 — caso de uso](modulo2_caso_uso.md)
- [Módulo 9 — Process Mining](modulo9_process_mining.md)
- [Módulo 9 — estimación cloud](modulo9_cloud_estimacion.md)
- [Módulo 9 — estado de evidencias](modulo9_evidencias.md)
- [Seguimiento operativo](OPERATIONAL_TRACKING.md)

## Evidencias
- [AWS — calculadora oficial](evidence/aws/README.md): estimación del 13/10/2026, **44,82 USD/mes** (EC2 con EBS 41,17 + IPv4 3,65). Las capturas PNG todavía deben incorporarse al repositorio.
- [MLflow — ejecución actual](evidence/mlflow/README.md): documentación de la ejecución del 13/10/2026; sus capturas nuevas están pendientes de subir. Un archivo PNG histórico sigue pendiente de eliminación.
- [Cloud — hoja de trabajo](evidence/cloud/README.md): descomposición y supuestos; no reemplaza la cotización oficial.

## Capturas nuevas de MLflow pendientes de subir
Se ejecutó localmente `five_league_scouting_real_refit` el 13/10/2026 en `tfm-scouting-six-styles-real`. Antes de sustituir la evidencia histórica, subir capturas del run (overview/tags, parámetros/métricas, artefactos y gráfica), actualizar el identificador de run y sus hashes. No inferir nuevas métricas a partir de las capturas antiguas.

**Criterio de conservación:** los documentos académicos originales y la evidencia histórica no se eliminan automáticamente; se etiquetan o archivan cuando la evidencia actual esté verificada.
