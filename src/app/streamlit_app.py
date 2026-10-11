"""Aplicación Streamlit de scouting — versión mejorada visualmente."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import FEATURE_COLS, MODELS_DIR, PLAY_STYLES
from src.features.styles import list_styles
from src.models.recommend import PlayerRecommender
from src.preprocessing.clean import load_players
from src.app.budget import load_budget_inputs, candidate_links, attach_reported_values, screen_budget
from src.app.collected import load_collected_service

# ── Paleta verde fútbol ──────────────────────────────────────────────────────
GREEN_PRIMARY   = "#1a7a3c"   # verde campo
GREEN_LIGHT     = "#2ecc71"   # acento claro
GREEN_DARK      = "#0f4d25"   # verde oscuro
BG_DARK         = "#0d1f14"   # fondo muy oscuro
BG_CARD         = "#142b1c"   # fondo tarjetas
GOLD            = "#f0c040"   # acento dorado para destacados
TEXT_LIGHT      = "#e8f5ec"   # texto principal
TEXT_MUTED      = "#7dab8a"   # texto secundario
PLOTLY_TEMPLATE = "plotly_dark"

CSS = f"""
<style>
/* Fondo general */
[data-testid="stAppViewContainer"] {{
    background-color: {BG_DARK};
}}
[data-testid="stSidebar"] {{
    background-color: {BG_CARD};
    border-right: 1px solid {GREEN_PRIMARY};
}}

/* Texto base */
html, body, [data-testid="stMarkdownContainer"] p,
[data-testid="stText"] {{
    color: {TEXT_LIGHT};
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}

/* Título principal */
h1 {{
    color: {GREEN_LIGHT} !important;
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
    border-bottom: 2px solid {GREEN_PRIMARY};
    padding-bottom: 0.4rem;
    margin-bottom: 0.2rem;
}}

/* Subtítulos */
h2, h3 {{
    color: {TEXT_LIGHT} !important;
    font-weight: 700 !important;
}}

/* Caption */
[data-testid="stCaptionContainer"] {{
    color: {TEXT_MUTED} !important;
    font-size: 0.85rem;
}}

/* Sidebar header */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {GREEN_LIGHT} !important;
    font-size: 1rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.8rem;
}}

/* Botón primario */
[data-testid="stButton"] button[kind="primary"] {{
    background-color: {GREEN_PRIMARY} !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    width: 100%;
    padding: 0.6rem !important;
    transition: background 0.2s;
}}
[data-testid="stButton"] button[kind="primary"]:hover {{
    background-color: {GREEN_LIGHT} !important;
    color: {BG_DARK} !important;
}}

/* Botón secundario */
[data-testid="stButton"] button {{
    background-color: {BG_CARD} !important;
    border: 1px solid {GREEN_PRIMARY} !important;
    color: {TEXT_LIGHT} !important;
    border-radius: 6px !important;
    width: 100%;
}}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background-color: {BG_CARD};
    border-radius: 8px;
    padding: 4px;
    gap: 4px;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    color: {TEXT_MUTED} !important;
    font-weight: 600;
    border-radius: 6px;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background-color: {GREEN_PRIMARY} !important;
    color: white !important;
}}

/* Dataframe */
[data-testid="stDataFrame"] {{
    border: 1px solid {GREEN_PRIMARY};
    border-radius: 8px;
    overflow: hidden;
}}

/* Info box */
[data-testid="stInfo"] {{
    background-color: {BG_CARD} !important;
    border-left: 3px solid {GREEN_LIGHT} !important;
    color: {TEXT_LIGHT} !important;
    border-radius: 0 6px 6px 0;
}}

/* Sliders */
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stThumbValue"] {{
    color: {GREEN_LIGHT};
}}

/* Métricas KPI */
[data-testid="stMetric"] {{
    background-color: {BG_CARD};
    border: 1px solid {GREEN_PRIMARY};
    border-radius: 10px;
    padding: 1rem 1.2rem;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED} !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}
[data-testid="stMetricValue"] {{
    color: {GREEN_LIGHT} !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
}}
[data-testid="stMetricDelta"] {{
    color: {GOLD} !important;
}}

/* Warning */
[data-testid="stAlert"] {{
    border-radius: 8px;
}}
</style>
"""

# Emojis por estilo de juego
STYLE_ICONS = {
    "posesion":          "🎯",
    "presion_alta":      "⚡",
    "vertical":          "🚀",
    "contraataque":      "🏃",
    "solidez_defensiva": "🛡️",
    "desborde_banda":    "🌀",
}


@st.cache_resource
def load_model() -> PlayerRecommender:
    import json
    from src.data.provenance import sha256
    from src.config import PLAYERS_PARQUET
    path = MODELS_DIR / "recommender.joblib"
    meta_path = MODELS_DIR / "metrics.json"
    if not path.exists() or not meta_path.exists():
        raise FileNotFoundError("No audited real-data model; old mixed-data artifacts are excluded")
    meta = json.loads(meta_path.read_text())
    if sha256(PLAYERS_PARQUET) != meta["dataset"]["dataset_sha256"]:
        raise ValueError("Model and dataset fingerprints differ; retrain before use")
    return PlayerRecommender.load(path)


@st.cache_data
def load_reported_budget_data():
    return load_budget_inputs()


@st.cache_resource
def collected_service(name):
    return load_collected_service(name)


def radar_figure(
    player_row: pd.Series,
    feature_cols: list[str],
    title: str,
    all_players: pd.DataFrame | None = None,
) -> go.Figure:
    raw = pd.to_numeric(pd.Series([player_row.get(c, np.nan) for c in feature_cols]), errors='coerce').to_numpy(float)

    # Normalizar 0-1 respecto al máximo de la liga para comparación justa
    if all_players is not None:
        maxvals = np.array([
            all_players[c].quantile(0.95) if c in all_players.columns else 1.0
            for c in feature_cols
        ])
        maxvals[~np.isfinite(maxvals) | (maxvals <= 0)] = np.nan
        normalized = np.clip(raw / maxvals, 0, 1)
    else:
        maxv = max(np.nanmax(raw), 1e-6) if np.isfinite(raw).any() else np.nan
        normalized = raw / maxv
    values = [float(value) if np.isfinite(value) else None for value in normalized]

    labels = [c.replace("_p90", "").upper() for c in feature_cols]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + values[:1],
        theta=labels + labels[:1],
        fill="toself",
        fillcolor=f"rgba(46,204,113,0.2)",
        line=dict(color=GREEN_LIGHT, width=2),
        connectgaps=False,
        name=str(player_row.get("player", "Jugador")),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor=BG_CARD,
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickfont=dict(color=TEXT_MUTED, size=9),
                gridcolor="#1f3d2a",
                linecolor="#1f3d2a",
            ),
            angularaxis=dict(
                tickfont=dict(color=TEXT_LIGHT, size=11, family="Inter"),
                gridcolor="#1f3d2a",
                linecolor="#1f3d2a",
            ),
        ),
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_CARD,
        font=dict(color=TEXT_LIGHT),
        showlegend=False,
        title=dict(text=title, font=dict(color=TEXT_LIGHT, size=13), x=0.5),
        margin=dict(l=50, r=50, t=55, b=40),
        height=400,
    )
    return fig


def bar_figure(df: pd.DataFrame) -> go.Figure:
    df = df.head(10).copy()
    df["affinity_pct"] = (df["affinity"] * 100).round(1)
    colors = [GOLD if i == 0 else GREEN_PRIMARY for i in range(len(df))]
    fig = go.Figure(go.Bar(
        x=df["affinity_pct"],
        y=df["player"],
        orientation="h",
        marker_color=colors,
        text=df["affinity_pct"].astype(str),
        textposition="outside",
        textfont=dict(color=TEXT_LIGHT, size=11),
    ))
    fig.update_layout(
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_CARD,
        font=dict(color=TEXT_LIGHT),
        xaxis=dict(
            title="Coseno ×100",
            gridcolor="#1f3d2a",
            tickfont=dict(color=TEXT_MUTED),
            range=[-100, 115],
        ),
        yaxis=dict(
            categoryorder="total ascending",
            tickfont=dict(color=TEXT_LIGHT, size=11),
        ),
        title=dict(text="Ranking de afinidad", font=dict(color=TEXT_LIGHT, size=13), x=0.5),
        margin=dict(l=10, r=60, t=50, b=40),
        height=400,
    )
    return fig


def scatter_figure(df: pd.DataFrame) -> go.Figure:
    cluster_colors = [
        GREEN_LIGHT, GOLD, "#e74c3c", "#3498db", "#9b59b6", "#e67e22"
    ]
    fig = px.scatter(
        df,
        x="pc1", y="pc2",
        color=df["cluster"].astype(str),
        hover_data=["player", "team", "pos_main", "league"],
        color_discrete_sequence=cluster_colors,
        title="Proyección PCA · Clusters de perfiles",
    )
    fig.update_traces(marker=dict(size=6, opacity=0.75))
    fig.update_layout(
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_DARK,
        font=dict(color=TEXT_LIGHT),
        xaxis=dict(gridcolor="#1f3d2a", tickfont=dict(color=TEXT_MUTED), title="PC1"),
        yaxis=dict(gridcolor="#1f3d2a", tickfont=dict(color=TEXT_MUTED), title="PC2"),
        legend=dict(
            title="Cluster",
            font=dict(color=TEXT_LIGHT),
            bgcolor=BG_CARD,
            bordercolor=GREEN_PRIMARY,
            borderwidth=1,
        ),
        title=dict(font=dict(color=TEXT_LIGHT, size=14), x=0.5),
        height=480,
    )
    return fig


def main() -> None:
    st.set_page_config(
        page_title="ScoutIQ · Scouting de Futbolistas",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.title("⚽ ScoutIQ — Scouting de Futbolistas")
    st.caption("Sistema de recomendación por afinidad táctica · TFM Data Science")
    model_labels = {'Core · seis estilos': 'core', 'Ofensivo': 'offensive', 'Exploración heredada': 'legacy'}
    selected_model = st.sidebar.selectbox('Modelo de scouting', list(model_labels))
    model_kind = model_labels[selected_model]

    # ── Carga del modelo ──────────────────────────────────────────────────────
    try:
        service = None if model_kind == 'legacy' else collected_service(model_kind)
        base_model = load_model() if service is None else service.model
        seasons = sorted(base_model.players.season.unique(), reverse=True) if service is None else service.available_seasons
        season = st.sidebar.selectbox('Temporada observada', seasons)
        rec = base_model if service is None else service.for_season(season)
    except Exception as exc:
        st.error(
            "No hay modelo/datos disponibles. Ejecuta primero:\n\n"
            "`python -m src.pipeline`"
        )
        st.exception(exc)
        return

    import json
    if service is None:
        st.warning("Exploración de datos FBref heredados 2023/24: procedencia original sin verificar. Solo goles y asistencias; no validación final ni costes de fichaje.")
    else:
        st.caption(f"Perfiles FBref observados en {season}, mínimo 450 minutos. Exploración retrospectiva; "
                   "los estilos son aproximaciones estadísticas y no una simulación de decisiones históricas. "
                   "Temporadas parciales o con menos de 10 candidatos no se ofrecen.")
    st.caption("Afinidad coseno: puntuación descriptiva de −1 a 1, no probabilidad de éxito. Features: " + ", ".join(rec.artifacts.feature_cols))
    from src.features.styles import measured_weight_fraction
    styles = {k:v for k,v in list_styles().items() if measured_weight_fraction(k, rec.artifacts.feature_cols) >= .6}
    if service is not None:
        styles = {key: value for key, value in styles.items() if key in service.supported_styles}
    style_labels = {k: v["label"] for k, v in styles.items()}
    try:
        reported_values, price_candidates, canonical_profiles = load_reported_budget_data()
        price_links = candidate_links(rec.players, price_candidates, canonical_profiles)
        budget_data_available = True
    except (FileNotFoundError, ValueError, KeyError):
        reported_values = price_links = None
        budget_data_available = False

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🎛️ Filtros de búsqueda")
        st.divider()

        style_key = st.selectbox(
            "Estilo de juego",
            options=list(style_labels),
            format_func=lambda k: f"{STYLE_ICONS.get(k, '⚽')} {style_labels[k]}",
        )
        st.info(f"_{PLAY_STYLES[style_key]['description']}_")

        st.divider()

        positions = ['Todas'] + sorted(rec.players.pos_main.dropna().unique())
        position = st.selectbox("Posición", positions)

        leagues = ["Todas"] + sorted(rec.players["league"].dropna().unique().tolist())
        league = st.selectbox("Liga", leagues)

        max_age = st.slider("Edad máxima", 18, 40, 32) if rec.players.age.notna().any() else None
        min_minutes = st.slider('Minutos mínimos', 450, 4500, 450, step=90)
        clubs = sorted({club for item in rec.players.get('clubs', rec.players.team.map(lambda team: json.dumps([team]))) for club in json.loads(item)})
        excluded_club = st.selectbox('Excluir club', ['Ninguno'] + clubs)
        budget_enabled = st.checkbox("Filtrar por valor de mercado", disabled=not budget_data_available)
        valuation_cutoff = None
        max_budget = None
        if budget_data_available:
            valuation_cutoff = st.date_input("Fecha límite del valor reportado",
                value=reported_values.valuation_date.max().date())
            st.caption(f"Valoraciones registradas hasta {reported_values.valuation_date.max().date()}. "
                       "Cruces de identidad provisionales. Precio de mercado reportado, no coste de fichaje. "
                       "La fecha original de publicación es desconocida; este filtro no valida presupuestos históricos.")
            if budget_enabled:
                max_budget = st.number_input("Presupuesto máximo (M€)", min_value=0.01, value=10.0, step=1.0)
                st.caption("Se excluyen valores desconocidos y ceros ambiguos. No se estiman precios faltantes.")
        else:
            st.caption("Valoraciones no disponibles: conserva los archivos de datos subidos y sus manifiestos.")
        top_n = st.slider("Nº de resultados", 5, 30, 10)

        st.divider()
        run = st.button("🔍 Buscar jugadores", type="primary")
        if run:
            import uuid
            from src.process.events import record_event
            st.session_state['scouting_case'] = str(uuid.uuid4())
            attrs = dict(style=style_key, position=position, season=season, league=league, max_age=max_age,
                         model=model_kind, min_minutes=min_minutes, exclude_club=excluded_club,
                         reported_value_budget_million=max_budget, reported_value_cutoff=str(valuation_cutoff),
                         price_match_status='provisional', historical_budget_validation=False)
            record_event(st.session_state.scouting_case, 'need_defined', 'app_user', attrs)
            record_event(st.session_state.scouting_case, 'search_executed', 'system', attrs)

    # ── KPIs globales ─────────────────────────────────────────────────────────
    total = rec.players.entity_id.nunique()
    n_teams = len(clubs)
    n_leagues = rec.players["league"].nunique()
    n_styles = len(styles)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Jugadores en la temporada", f"{total:,}")
    k2.metric("Equipos", f"{n_teams:,}")
    k3.metric("Ligas", f"{n_leagues:,}")
    k4.metric("Estilos de juego", f"{n_styles}")

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Recomendaciones",
        "🔗 Jugadores similares",
        "🗺️ Explorar clusters",
        '👤 Perfiles y comparación',
        '📊 Modelo y cobertura',
        '🎯 Escenarios de scouting',
    ])

    # ── Tab 1: Recomendaciones ────────────────────────────────────────────────
    with tab1:
        filters = (style_key, position, league, season, max_age, max_budget, str(valuation_cutoff), top_n,
                   model_kind, min_minutes, excluded_club)
        if run or "last_result" not in st.session_state or st.session_state.get('last_filters') != filters:
            if not run and st.session_state.get('last_filters') != filters:
                st.session_state.pop('scouting_case', None)
            result = rec.recommend(
                style_key=style_key,
                position=None if position == "Todas" else position,
                max_age=max_age,
                max_budget=None,
                league=None if league == "Todas" else league,
                top_n=len(rec.players),
                season=season,
            )
            result = result[result.minutes.ge(min_minutes)]
            if excluded_club != 'Ninguno':
                if 'clubs' in result:
                    result = result[~result.clubs.map(lambda item: excluded_club in json.loads(item))]
                else:
                    result = result[result.team.ne(excluded_club)]
            if budget_data_available:
                result = attach_reported_values(result, price_links, reported_values, valuation_cutoff)
                if max_budget is not None:
                    result = screen_budget(result, max_budget)
            result = result.head(top_n)
            if run:
                from src.process.events import record_event
                record_event(st.session_state.scouting_case, 'ranking_generated', 'system', {'candidates': len(result)})
            st.session_state["last_result"] = result
            st.session_state["last_style"] = style_key
            st.session_state['last_filters'] = filters
        else:
            result = st.session_state["last_result"]
            style_key = st.session_state.get("last_style", style_key)

        if st.session_state.get('scouting_case') and st.button("Registrar revisión de shortlist"):
            from src.process.events import record_event
            record_event(st.session_state.scouting_case, 'shortlist_reviewed', 'app_user', {'count': len(result)})
        icon = STYLE_ICONS.get(style_key, "⚽")
        st.subheader(f"{icon} Ranking · {style_labels[style_key]}")

        if result.empty:
            st.warning("Sin resultados con esos filtros. Prueba a ampliar los rangos.")
        else:
            # Tabla
            show = result.copy()
            show["affinity"] = (show["affinity"] * 100).round(1)
            if 'reported_value_status' in show:
                show['reported_value_status'] = show.reported_value_status.map({
                    'reported_positive': 'Valor reportado disponible',
                    'reported_zero_ambiguous': 'Cero reportado; significado desconocido',
                    'unmatched': 'Jugador sin cruce de identidad',
                    'no_record_on_or_before_cutoff': 'Sin valor anterior a la fecha límite',
                    'invalid_or_unknown': 'Valor desconocido o no válido',
                })
                show['price_identity_status'] = show.price_identity_status.map({
                    'provisional_not_reviewed': 'Provisional, sin revisión individual', 'unmatched': 'Sin cruce'})
            visible = ['player', 'team', 'league', 'season', 'pos', 'age', 'minutes', 'affinity']
            visible += rec.artifacts.feature_cols
            visible += ['reported_market_value_eur', 'reported_valuation_date',
                        'reported_value_source', 'price_identity_status', 'reported_value_status']
            visible = list(dict.fromkeys(column for column in visible if column in show))
            st.dataframe(
                show[visible].rename(columns={
                    "player": "Jugador", "team": "Equipo", "league": "Liga",
                    "season": "Temp.", "pos": "Pos", "age": "Edad",
                    "affinity": "Afinidad coseno ×100",
                    "minutes": "Minutos",
                    "reported_market_value_eur": "Valor de mercado reportado (€)",
                    "reported_valuation_date": "Fecha del valor reportado",
                    "price_identity_status": "Estado del cruce de jugador",
                    "reported_value_source": "Fuente del valor",
                    "reported_value_status": "Disponibilidad del valor",
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.download_button("Descargar shortlist CSV", data=result.to_csv(index=False).encode('utf-8'),
                               file_name='scouting_shortlist.csv', mime='text/csv')

            st.divider()

            # Gráficos
            top = result.iloc[0]
            feats = rec.artifacts.feature_cols
            st.caption('Radar relativo al percentil 95 de la temporada; valores desconocidos quedan sin trazar.')
            c1, c2 = st.columns(2)

            with c1:
                st.plotly_chart(
                    radar_figure(
                        top, feats,
                        f"Perfil · {top['player']}",
                        all_players=rec.players,
                    ),
                    use_container_width=True,
                )
            with c2:
                st.plotly_chart(
                    bar_figure(result),
                    use_container_width=True,
                )

            # Detalle del jugador top
            with st.expander(f"📄 Detalle · {top['player']}", expanded=False):
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Equipo", str(top.get("team", "—")))
                d2.metric("Edad", str(int(top.age)) if pd.notna(top.age) else "Desconocida")
                d3.metric("Minutos", f"{int(top.get('minutes', 0)):,}")
                d4.metric("Afinidad coseno", f"{top.get('affinity', 0):.3f}")

    # ── Tab 2: Similares ──────────────────────────────────────────────────────
    with tab2:
        st.subheader("🔗 Jugadores similares")
        st.caption('Distancia de perfil estandarizado; menor distancia indica mayor cercanía. '
                   'La puntuación de similitud no es una probabilidad de éxito.')

        references = rec.players
        if position != 'Todas':
            references = references[references.pos.astype(str).str.split(',').map(lambda parts: position in [part.strip() for part in parts])]
        options = references.sort_values("player")[["player_id", "player", "team"]]
        label_map = {
            int(r.player_id): f"{r.player}  ·  {r.team}"
            for r in options.itertuples()
        }
        selected = st.selectbox(
            "Jugador de referencia",
            options=list(label_map),
            format_func=lambda i: label_map[i],
        )
        same_position = st.checkbox('Misma posición que la referencia', value=True)

        if st.button("🔍 Buscar similares"):
            sim = rec.similar_players(selected, top_n=len(rec.players))
            reference = rec.players[rec.players.player_id.eq(selected)].iloc[0]
            if same_position: sim = sim[sim.pos_main.eq(reference.pos_main)]
            if position != 'Todas':
                sim = sim[sim.pos.astype(str).str.split(',').map(lambda parts: position in [part.strip() for part in parts])]
            sim = sim[sim.minutes.ge(min_minutes)]
            if max_age is not None: sim = sim[sim.age.notna() & sim.age.le(max_age)]
            if excluded_club != 'Ninguno':
                sim = sim[~sim.get('clubs', sim.team.map(lambda team: json.dumps([team]))).map(lambda item: excluded_club in json.loads(item))]
            if budget_data_available:
                sim = attach_reported_values(sim, price_links, reported_values, valuation_cutoff)
                if max_budget is not None: sim = screen_budget(sim, max_budget)
            sim = sim.head(top_n)
            st.session_state['similar_result'] = sim
            st.dataframe(
                sim[[column for column in ['player', 'team', 'pos', 'age', 'league', 'season', 'distance', 'similarity',
                     'reported_market_value_eur', 'reported_valuation_date', 'price_identity_status'] if column in sim]].rename(columns={
                    "player": "Jugador", "team": "Equipo", "pos": "Pos",
                    "age": "Edad", "league": "Liga", "similarity": "Puntuación de similitud",
                    'distance': 'Distancia de perfil', 'season': 'Temporada',
                    'reported_market_value_eur': 'Valor de mercado reportado (€)',
                    'reported_valuation_date': 'Fecha del valor reportado',
                    'price_identity_status': 'Cruce de identidad provisional',
                }),
                use_container_width=True,
                hide_index=True,
            )

            # Radar comparativo del jugador seleccionado
            ref_row = rec.players[rec.players["player_id"] == selected]
            if not ref_row.empty:
                feats = rec.artifacts.feature_cols
                st.plotly_chart(
                    radar_figure(
                        ref_row.iloc[0], feats,
                        f"Perfil de referencia · {ref_row.iloc[0]['player']}",
                        all_players=rec.players,
                    ),
                    use_container_width=True,
                )

    # ── Tab 3: Clusters ───────────────────────────────────────────────────────
    with tab3:
        st.subheader("🗺️ Mapa PCA + K-Means")
        st.caption('Cada punto es un perfil observado. Los clusters son grupos estadísticos; no representan los seis estilos de juego.')

        df = rec.players
        if "pc1" in df.columns and "pc2" in df.columns:
            sample = df.sample(min(800, len(df)), random_state=42)
            st.plotly_chart(scatter_figure(sample), use_container_width=True)

            # Distribución por cluster
            cluster_dist = df["cluster"].value_counts().reset_index()
            cluster_dist.columns = ["Cluster", "Jugadores"]
            st.dataframe(cluster_dist, use_container_width=True, hide_index=True)
        else:
            st.info("PCA no disponible en el modelo cargado. Ejecuta `python -m src.pipeline`.")

    with tab4:
        st.subheader('Perfiles, historial y comparación')
        profiles = rec.players.sort_values(['player', 'player_id'])
        labels = {int(row.player_id): f'{row.player} · {row.team} · {row.season}' for row in profiles.itertuples()}
        first_id = st.selectbox('Primer jugador', list(labels), format_func=lambda value: labels[value])
        second_id = st.selectbox('Segundo jugador', list(labels), index=min(1, len(labels)-1), format_func=lambda value: labels[value])
        compared = profiles[profiles.player_id.isin([first_id, second_id])]
        fields = ['player', 'team', 'season', 'pos_main', 'age', 'minutes'] + rec.artifacts.feature_cols
        st.dataframe(compared[fields], hide_index=True, use_container_width=True)
        columns = st.columns(2)
        for index, (column, identifier) in enumerate(zip(columns, [first_id, second_id])):
            row = profiles[profiles.player_id.eq(identifier)].iloc[0]
            column.plotly_chart(radar_figure(row, rec.artifacts.feature_cols, str(row.player), rec.players),
                                use_container_width=True, key=f'comparison_radar_{index}')
        st.caption('Comparación de mediciones observadas en la misma temporada; desconocidos no equivalen a cero.')
        if service is not None:
            entity = profiles[profiles.player_id.eq(first_id)].entity_id.iloc[0]
            history = service.history[service.history.entity_id.eq(entity)].sort_values('season')
            st.markdown('**Historial FBref del primer jugador**')
            st.dataframe(history[['season', 'team', 'minutes', 'gls', 'ast', 'partial_season']], hide_index=True, use_container_width=True)
        else:
            st.caption('El archivo heredado no permite unir un historial de identidad verificado.')

    with tab5:
        st.subheader('Modelo y cobertura')
        if service is None:
            st.caption('Modelo exploratorio heredado; su procedencia y evaluación final no están verificadas.')
        else:
            info = service.info
            st.caption('Evaluación: recuperación del mismo jugador en la siguiente temporada según su perfil. '
                       'No mide éxito de fichajes ni pertinencia táctica validada.')
            st.dataframe(pd.DataFrame([{'Modelo': selected_model, 'Método de distancia': info['selected_method'],
                'MRR holdout': info['holdout_mrr'], 'Recall@5': info['holdout_recall_at_5'],
                'K clusters': info['selected_k'], 'Varianza PCA 2 componentes': sum(info['pca_explained_variance'][:2]),
                'Jaccard top-5 bootstrap': info['robustness_top5_jaccard_mean']}]), hide_index=True)
            st.caption('Core y ofensivo tienen periodos de evaluación diferentes; sus métricas no son una comparación controlada. '
                       'La componente PC4 de Core mostró sensibilidad en la validación extendida.')
            st.dataframe(service.gallery.groupby('season').agg(observaciones=('entity_id', 'size'),
                jugadores=('entity_id', 'nunique'), temporada_parcial=('partial_season', 'any')).reset_index(), hide_index=True)
            st.caption('Transformaciones ajustadas únicamente en las temporadas de entrenamiento: ' +
                       ', '.join(sorted(service.model.players.season.unique())) + '. No se reajustan al cambiar de temporada.')
            st.caption('Variables medidas: ' + ', '.join(rec.artifacts.feature_cols) + '. '
                       'No hay galería avanzada de Segunda disponible; no se presentan sus estadísticas básicas como perfiles completos.')

    with tab6:
        from src.app.scenario_ui import render_scenarios
        render_scenarios(rec, service, price_links, reported_values)


if __name__ == "__main__":
    main()
