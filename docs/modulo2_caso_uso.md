# Caso de uso de ciencia de datos — TFM Scouting de futbolistas

## 1. Contexto y problema de negocio
Los departamentos de scouting necesitan comparar candidatos con criterios explícitos y reproducibles, combinando datos con observación deportiva. El sistema apoya la elaboración de una shortlist; no sustituye la decisión del scout.

## 2. Objetivo del caso de uso
Recomendar perfiles por afinidad con seis estilos expertos, posición, edad, minutos y una o varias ligas. El valor de mercado reportado se aplica después del ranking cuando hay cruce provisional y fecha válida; no se estima un coste de fichaje.

## 3. Usuario final
Director deportivo, scout o analista del club. La interfaz evita selectores de entrenamiento y terminología técnica innecesaria.

## 4. Pregunta de negocio
¿Qué jugadores observados se ajustan al perfil solicitado y merecen investigación adicional, dadas las restricciones y cobertura disponibles?

## 5. Datos realmente utilizados
FBref de cinco ligas: 15.948 registros jugador/liga/temporada y 7.398 candidatos de galería; temporadas completas de los seis estilos hasta 2023/24. Understat aporta 228.785 tiros para exploración separada. Las valoraciones proceden de CSV proporcionados por el usuario con origen GitHub declarado; moneda EUR supuesta e identidades provisionales. Segunda no forma parte de la galería táctica actual. CSV y procedencia: `data/raw/source_manifest.json`; tablas limpias: `data/processed/review/`.

## 6. Pipeline de ciencia de datos
1. Archivos publicados de GitHub y uploads preservados; los CSV de FBref/Understat son exportaciones documentadas de RDS, no scraping nuevo.
2. Limpieza con nulos conservados, controles de claves/exposición y agregación de clubes por temporada.
3. Tasas por 90, estilos expertos y transformación ajustada solo al entrenamiento.
4. KNN/distancia de perfiles, PCA y K-means; comparación cronológica con baselines.
5. Streamlit: ranking, similares, comparación multijugador, grupos ajustables, evolución y tiros.
6. Registro operativo de búsquedas/revisiones separado de MLflow.

## 7. Validación y criterios de éxito
Entrenamiento 2020/21–2021/22; selección en 2022/23; holdout 2023/24. MRR/Recall@K evalúan recuperación de la identidad futura del mismo jugador, no éxito de fichaje. Se analizan incertidumbre, estabilidad y resultados por liga/posición.

Validación experta propuesta: definir briefs, comparar listas del sistema con baselines bajo restricciones equivalentes, ocultar el método y aleatorizar presentación. Los expertos revisan vídeo/contexto y califican relevancia/encaje y necesidad de investigar. Medir relevancia en top-K, preferencia, acuerdo y tiempo, con incertidumbre. **No hay ratings expertos recogidos ni mejora real de fichajes demostrada.** Formularios ciegos y notebook de análisis preparados en `docs/expert_review/` y `notebooks/06_expert_recommendation_validation.ipynb`; recogida humana pendiente de participantes.

## 8. Límites
Datos históricos, posiciones amplias, cobertura reciente incompleta, métricas proxy de estilo, valores distintos de fees y ausencia de fechas originales de publicación. No se ofrece probabilidad de transferencia ni predicción de rendimiento futuro. Véase `TEACHER_FEEDBACK.md`.
