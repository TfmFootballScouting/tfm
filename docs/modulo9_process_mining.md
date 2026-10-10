> Estado de entrega: el proceso siguiente es un diseño TO-BE, no un proceso observado de un club. La aplicación registra necesidad/búsqueda/ranking y revisión explícita; no infiere fichajes. `src/process/events.py` implementa log formal y descubrimiento directly-follows. No hay sesiones humanas genuinas en la entrega, por lo que descubrimiento organizativo y KPIs quedan bloqueados. Véase `notebooks/04_process_mining.ipynb` y `COMPLETION_REPORT.md`.

# Módulo 9 — Problema de negocio con visión Process Mining

## 1. Proceso analizado
Proceso de scouting y recomendación de futbolistas para la toma de decisión de fichaje.

## 2. AS-IS (situación actual)
1. Definir necesidad del club (posición / perfil táctico)
2. Buscar candidatos de forma manual (vídeos, informes, intuición)
3. Comparar perfiles de forma subjetiva entre analistas
4. Elaborar shortlist
5. Decisión de fichaje
6. Seguimiento posterior (poco sistematizado)

### Problemas del AS-IS
- Alta subjetividad y poca reproducibilidad
- Tiempo elevado hasta disponer de una shortlist comparable
- Difícil cuantificar el "encaje" con el estilo de juego
- Escasa trazabilidad de por qué se eligió a un jugador

## 3. TO-BE (con el sistema del TFM)
1. Definir necesidad del club
2. Traducir la necesidad a un estilo de juego (vector de métricas ponderadas)
3. Aplicar filtros (posición, edad, presupuesto)
4. Ejecutar motor de similitud / recomendación
5. Revisar ranking + visualizaciones (radar)
6. Shortlist basada en evidencia cuantitativa
7. Decisión de fichaje
8. Registrar resultado para mejora continua (feedback)

## 4. Eventos del proceso (visión process mining)
| Evento | Actor | Sistema |
|--------|-------|---------|
| necesidad_definida | Dirección deportiva | Manual / app |
| estilo_configurado | Scouting / analista | Streamlit |
| busqueda_ejecutada | Sistema | Pipeline ML |
| ranking_generado | Sistema | Modelo similitud |
| shortlist_validada | Scouting | App + humano |
| decision_fichaje | Dirección | Manual |
| feedback_registrado | Analista | Futuro (MLflow/logs) |

## 5. Cuellos de botella que ataca el TFM
- Búsqueda y comparación de candidatos (pasos 2–3 del AS-IS)
- Falta de criterio cuantitativo de afinidad táctica

## 6. KPIs de proceso
- Tiempo medio hasta shortlist
- Nº de candidatos evaluados por búsqueda
- % de shortlist alineada con el estilo definido
- Tasa de aceptación de recomendaciones por scouting
- Reproducibilidad: misma configuración → mismo ranking

## 7. Pregunta de negocio (process + datos)
¿Cómo reducir el tiempo y la subjetividad del scouting cuantificando el encaje jugador–estilo de juego y dejando trazabilidad del proceso de decisión?
