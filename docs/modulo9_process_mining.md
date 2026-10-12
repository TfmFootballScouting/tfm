# Módulo 9 — Process Mining del scouting

## 1. Proceso y AS-IS
Proceso propuesto: definir una necesidad, buscar perfiles, compararlos, elaborar shortlist, revisar y decidir. El AS-IS depende de observación manual y criterios difíciles de reproducir. No se afirma haber observado el proceso interno de un club.

## 2. TO-BE y unidad de caso
La aplicación convierte la necesidad en filtros y estilo; genera candidatos y permite revisión humana. Un UUID `case_id` identifica actualmente una búsqueda explícita (`scouting_case` en sesión), equivalente al identificador de solicitud de scouting para esa ejecución. Una solicitud que agrupe varias búsquedas iterativas requiere ampliar el ciclo de vida; no se simula como ya implementada.

## 3. Event log implementado
`src/process/events.py` escribe JSONL append-only con `case_id`, `activity`, timestamp UTC, `actor`, `event_kind` y `attributes`.

| Acción real en Streamlit | Actividades registradas |
|---|---|
| Buscar jugadores | need_defined, search_executed, ranking_generated |
| Registrar revisión de shortlist | shortlist_reviewed |

Atributos iniciales: estilo, filtros, temporada, alcance de datos/modelo y presupuesto/fecha de valor cuando aplica. Ranking/revisión registran cantidad de candidatos. `actor` es un rol genérico, no usuario autenticado. Los IDs de jugadores recomendados y feedback individual no se almacenan aún. Previsualizaciones automáticas al cambiar filtros no equivalen a búsqueda explícita registrada.

Destino: `data/events/scouting.jsonl`, ignorado por Git; `TFM_EVENT_LOG` selecciona otro archivo. Los tests usan rutas aisladas y no cuentan como sesiones humanas. No se publican decisiones privadas.

## 4. Análisis implementado y límites
`discover()` valida esquema, eventos observados y orden temporal; obtiene grafo directly-follows, tiempos entre actividades y duración/completitud de casos. No hay una muestra genuina de usuarios/clubes para presentar variantes o cuellos de botella organizativos. El notebook original 04 conserva el diseño y distingue demostraciones/pruebas de evidencias reales.

## 5. KPIs propuestos
Tiempo hasta shortlist, revisiones, repeticiones de búsqueda, aceptación experta y duración de caso. No se muestran valores inventados. Medirlos requiere sesiones humanas con casos y atributos adecuados.

## 6. Separación de sistemas
MLflow guarda experimentos y artefactos ML. JSONL guarda actualmente acciones operativas. Una base SQLite distinta para solicitudes, decisiones y feedback es **propuesta pendiente de aprobación**, con exportación de event log; no está implementada. Autenticación y aliases también son mejoras futuras.

## 7. Próximos pasos
Aprobar enriquecimiento de eventos/base operativa, recoger sesiones reales con participantes y analizar secuencias/repeticiones/esperas. Las instrucciones y responsabilidades manuales figuran en `TEACHER_FEEDBACK.md`.

## Implementación operativa aprobada

Se añadió una base SQLite independiente para solicitudes/eventos/decisiones/feedback. Las búsquedas iterativas conservan el UUID hasta iniciar una nueva solicitud. El alias es declarado, no autenticado. Véase `OPERATIONAL_TRACKING.md` para schema, exportación y limitaciones. No existen todavía sesiones humanas verificadas para conclusiones organizativas.
