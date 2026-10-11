> Collected-data preprocessing update: real retained archives are now cleaned and audited across seasons without changing the original folder structure or fitted model. See [mandatory features, cohorts and executed EDA](COLLECTED_PREPROCESSING.md).

# Caso de uso de ciencia de datos — TFM Scouting de futbolistas

## 1. Contexto y problema de negocio
Los departamentos de scouting de clubes profesionales y semiprofesionales basan gran parte de la identificación de talento en observación subjetiva. Eso dificulta comparar jugadores de forma objetiva, reproducir criterios entre analistas y alinear fichajes con el estilo de juego del equipo.

## 2. Objetivo del caso de uso
Desarrollar un sistema de recomendación que, dado un estilo de juego (vector de métricas ponderadas), una posición y filtros (edad, presupuesto basado en valoraciones históricas verificadas), proponga un ranking de jugadores cuyo perfil estadístico sea afín a ese estilo.

## 3. Usuario final
- Director deportivo / responsable de scouting
- Analista de datos deportivos del club

## 4. Pregunta de negocio
¿Qué jugadores disponibles se ajustan mejor al estilo de juego X, en la posición Y, dentro de un rango de edad y presupuesto Z?

## 5. Datos
- Cobertura objetivo: FBref, Understat (La Liga) y Transfermarkt; La Liga/Segunda 2020/21–2025/26.
- Cobertura realmente ejecutada: 420 observaciones heredadas FBref sin procedencia original verificada; muestra actual Transfermarkt de 50 valores y dos perfiles.
- Solo goles/asistencias por 90 en la exploración; cobertura ampliada, métricas defensivas y validación de fichajes pendientes. Véase SOURCE_ACCESS.md y COMPLETION_REPORT.md.

## 6. Pipeline de ciencia de datos
1. Extracción (scraping / soccerdata)
2. Limpieza y estructuración (SQLite / tablas procesadas)
3. Feature engineering: normalización y vectores de estilo de juego
4. Modelado: similitud coseno, KNN, PCA y K-Means
5. Evaluación de fichajes históricos (diseño documentado; ejecución bloqueada sin datos/etiquetas verificadas)
6. Despliegue en app Streamlit (ranking + radars)

## 7. Output esperado
- Ranking de jugadores por afinidad táctica
- Visualizaciones (radar, comparativas)
- Trazabilidad del criterio (métricas y pesos del estilo)

## 8. Criterios de éxito
- Coherencia con fichajes/casos reales conocidos
- Ranking interpretable por scouting
- Prototipo usable en Streamlit
- Pipeline reproducible (código + dependencias en GitHub)

## 9. Riesgos y limitaciones
- Sesgo por liga/minutos jugados
- Fragilidad del scraping
- Falta de valor de mercado preciso en fuentes públicas
- Estilos de juego son simplificaciones cuantitativas del juego real

## 10. Relación con el TFM
Este caso de uso materializa el anteproyecto "Análisis y scouting de futbolistas para la toma de decisiones en scouting deportivo" (Iván Galán, Basma Marso, Carlos Valencia).
