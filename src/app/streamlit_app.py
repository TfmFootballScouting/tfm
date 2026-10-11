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

from src.config import PLAY_STYLES
from src.features.styles import list_styles
from src.app.budget import candidate_links, attach_reported_values, screen_budget
from src.app.presentation import CSS as MODERN_CSS, shortlist_cards
from src.app.trained import load_trained_service
from src.app.europe_budget import load_europe_budget_inputs
from src.app.scouting_views import field_label, display_frame, group_profiles, POSITIONS

# ── Paleta verde fútbol ──────────────────────────────────────────────────────
GREEN_PRIMARY   = "#239b83"   # verde campo
GREEN_LIGHT     = "#51deb2"   # acento claro
GREEN_DARK      = "#0f4d25"   # verde oscuro
BG_DARK         = "#101b28"   # fondo muy oscuro
BG_CARD         = "#172536"   # fondo tarjetas
GOLD            = "#f0c040"   # acento dorado para destacados
TEXT_LIGHT      = "#e8f5ec"   # texto principal
TEXT_MUTED      = "#b8c7d8"   # texto secundario
PLOTLY_TEMPLATE = "plotly_dark"

# Emojis por estilo de juego
STYLE_ICONS = {
    "posesion":          "🎯",
    "presion_alta":      "⚡",
    "vertical":          "🚀",
    "contraataque":      "🏃",
    "solidez_defensiva": "🛡️",
    "desborde_banda":    "🌀",
}


@st.cache_data
def load_reported_budget_data():
    return load_europe_budget_inputs()


@st.cache_resource
def scouting_service():
    return load_trained_service('core')


@st.cache_data
def grouped_gallery(matrix, players, number):
    return group_profiles(matrix, players, number)


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

    labels = [field_label(c) for c in feature_cols]

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
    df["affinity_display"] = df["affinity"].round(3)
    colors = [GOLD if i == 0 else GREEN_PRIMARY for i in range(len(df))]
    fig = go.Figure(go.Bar(
        x=df["affinity_display"],
        y=df["player"],
        orientation="h",
        marker_color=colors,
        text=df["affinity_display"].astype(str),
        textposition="outside",
        textfont=dict(color=TEXT_LIGHT, size=11),
    ))
    fig.update_layout(
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_CARD,
        font=dict(color=TEXT_LIGHT),
        xaxis=dict(
            title="Afinidad de estilo (−1 a 1)",
            gridcolor="#1f3d2a",
            tickfont=dict(color=TEXT_MUTED),
            range=[-1, 1.15],
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


def main() -> None:
    st.set_page_config(
        page_title="ScoutIQ · Scouting de Futbolistas",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(MODERN_CSS, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.title("ScoutIQ · Tu próxima shortlist")
    st.caption("Encuentra perfiles, compara alternativas y define tus necesidades de scouting.")
    st.sidebar.markdown("## ScoutIQ")
    st.sidebar.caption("Define el mercado y el perfil que necesitas.")
    model_kind = 'core'
    scope = 'Cinco grandes ligas'
    training = 'Cinco ligas · reentrenado'

    # ── Carga del modelo ──────────────────────────────────────────────────────
    try:
        service = scouting_service()
        base_model = service.model
        seasons = service.available_seasons
        season = st.sidebar.selectbox('Temporada observada', seasons)
        rec = service.for_season(season)
    except Exception as exc:
        st.error(
            "No se pueden cargar los perfiles de scouting. Revisa el detalle del error. "
            "Actualiza el proyecto y verifica que los archivos de datos y perfiles están completos."
        )
        st.exception(exc)
        return

    import json
    st.caption(f"Temporada {season} · estadísticas disponibles de las cinco grandes ligas · 450+ minutos")
    with st.expander('Cómo interpretar las recomendaciones'):
        st.write('La afinidad compara las estadísticas del jugador con el estilo elegido. No es una probabilidad de éxito de fichaje. Los estilos son aproximaciones y necesitan revisión deportiva.')
        st.caption('Estadísticas utilizadas: ' + ', '.join(field_label(c) for c in rec.artifacts.feature_cols))
        st.caption('Los datos disponibles de perfiles completos terminan en 2023/24. En cambios de liga se conserva la liga con más minutos por temporada.')
    from src.features.styles import measured_weight_fraction
    styles = {k:v for k,v in list_styles().items() if measured_weight_fraction(k, rec.artifacts.feature_cols) >= .6}
    if service is not None:
        styles = {key: value for key, value in styles.items() if key in service.supported_styles}
    style_labels = {k: v["label"] for k, v in styles.items()}
    try:
        reported_values, price_candidates, canonical_profiles = load_reported_budget_data()
        price_links = candidate_links(rec.players, price_candidates, canonical_profiles)
        season_prices = attach_reported_values(rec.players, price_links, reported_values, reported_values.valuation_date.max().date())
        budget_data_available = bool(season_prices.reported_value_screenable.any())
    except (FileNotFoundError, ValueError, KeyError):
        reported_values = price_links = None
        budget_data_available = False

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### Perfil objetivo")
        from src.app.presentation import reset_search_filters
        st.button("Restablecer filtros", on_click=reset_search_filters, use_container_width=True)
        st.divider()

        style_key = st.selectbox(
            "Estilo de juego",
            options=list(style_labels),
            format_func=lambda k: f"{STYLE_ICONS.get(k, '⚽')} {style_labels[k]}",
            key='scout_filter_style',
        )
        st.info(f"_{PLAY_STYLES[style_key]['description']}_")

        st.divider()

        positions = ['Todas'] + sorted(rec.players.pos_main.dropna().unique())
        position = st.selectbox("Posición", positions, format_func=lambda p: POSITIONS.get(p, p), key="scout_filter_position")

        league_counts = rec.players.groupby('league').size()
        leagues = sorted(league_counts[league_counts.ge(10)].index.tolist())
        selected_leagues = st.multiselect('Ligas', leagues, default=leagues, key='scout_filter_leagues')
        league = ', '.join(selected_leagues)
        if not selected_leagues:
            st.info('Selecciona al menos una liga para explorar jugadores.')
            st.stop()

        max_age = st.slider("Edad máxima", 18, 40, 32, key="scout_filter_age") if rec.players.age.notna().any() else None
        min_minutes = st.slider('Minutos mínimos', 450, 4500, 450, step=90, key='scout_filter_minutes')
        clubs = sorted({club for item in rec.players.get('clubs', rec.players.team.map(lambda team: json.dumps([team]))) for club in json.loads(item)})
        excluded_club = st.selectbox('Excluir club', ['Ninguno'] + clubs, key='scout_filter_club')
        budget_enabled = False
        valuation_cutoff = None
        max_budget = None
        if budget_data_available:
            budget_enabled = st.checkbox("Filtrar por valor de mercado", key="scout_filter_budget_enabled")
            valuation_cutoff = st.date_input("Fecha límite del valor reportado",
                value=reported_values.valuation_date.max().date())
            st.caption(f"Valoraciones registradas hasta {reported_values.valuation_date.max().date()}. "
                       "Cruces de identidad provisionales. Precio de mercado reportado, no coste de fichaje. "
                       "La fecha original de publicación es desconocida; este filtro no valida presupuestos históricos.")
            if budget_enabled:
                max_budget = st.number_input("Presupuesto máximo (M€)", min_value=0.01, value=10.0, step=1.0)
                st.caption("Se excluyen valores desconocidos y ceros ambiguos. No se estiman precios faltantes.")
        top_n = st.slider("Nº de resultados", 5, 30, 10, key="scout_filter_top_n")

        st.divider()
        run = st.button("🔍 Buscar jugadores", type="primary", use_container_width=True)
        if run:
            import uuid
            from src.process.events import record_event
            st.session_state['scouting_case'] = str(uuid.uuid4())
            attrs = dict(training_scope=training, gallery_scope=scope, style=style_key, position=position, season=season, league=league, max_age=max_age,
                         model=model_kind, min_minutes=min_minutes, exclude_club=excluded_club,
                         reported_value_budget_million=max_budget, reported_value_cutoff=str(valuation_cutoff),
                         price_match_status='provisional', historical_budget_validation=False)
            record_event(st.session_state.scouting_case, 'need_defined', 'app_user', attrs)
            record_event(st.session_state.scouting_case, 'search_executed', 'system', attrs)

    # ── KPIs globales ─────────────────────────────────────────────────────────
    market_players = rec.players[rec.players.league.isin(selected_leagues)]
    total = market_players.entity_id.nunique()
    n_teams = len({club for item in market_players.get('clubs', market_players.team.map(lambda team: json.dumps([team]))) for club in json.loads(item)})
    n_leagues = market_players["league"].nunique()
    n_styles = len(styles)

    with st.container(key='market_metrics'):
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Jugadores en la temporada", f"{total:,}")
        k2.metric("Equipos", f"{n_teams:,}")
        k3.metric("Ligas", f"{n_leagues:,}")
        k4.metric("Estilos de juego", f"{n_styles}")

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📋 Recomendaciones",
        "🔗 Jugadores similares",
        "🗺️ Grupos de jugadores",
        '👤 Perfiles y comparación',
        '📊 Datos disponibles',
    ] + (['🎯 Escenarios de scouting'] if budget_data_available else []))
    tab1, tab2, tab3, tab4, tab5 = tabs[:5]
    tab6 = tabs[5] if budget_data_available else None

    # ── Tab 1: Recomendaciones ────────────────────────────────────────────────
    with tab1:
        filters = (style_key, position, tuple(selected_leagues), season, max_age, max_budget, str(valuation_cutoff), top_n,
                   model_kind, min_minutes, excluded_club, scope, training)
        if run or "last_result" not in st.session_state or st.session_state.get('last_filters') != filters:
            if not run and st.session_state.get('last_filters') != filters:
                st.session_state.pop('scouting_case', None)
            result = rec.recommend(
                style_key=style_key,
                position=None if position == "Todas" else position,
                max_age=max_age,
                max_budget=None,
                league=None,
                top_n=len(rec.players),
                season=season,
            )
            result = result[result.league.isin(selected_leagues) & result.minutes.ge(min_minutes)]
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
        st.caption(f"{league} · {season} · {POSITIONS.get(position, position)} · mínimo {min_minutes:,} minutos · {len(result)} alternativas")

        if result.empty:
            st.warning("Sin resultados con esos filtros. Prueba a ampliar los rangos.")
        else:
            # Tabla
            show = result.copy()
            shortlist_cards(result)
            show["affinity"] = show["affinity"].round(3)
            details = st.checkbox('Ver estadísticas y trazabilidad', value=False)
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
            if details: visible += rec.artifacts.feature_cols
            visible += ['reported_market_value_eur', 'reported_value_status']
            if details: visible += ['reported_valuation_date', 'reported_value_source', 'price_identity_status']
            visible = list(dict.fromkeys(column for column in visible if column in show))
            st.dataframe(
                display_frame(show[visible]).rename(columns={
                    "player": "Jugador", "team": "Equipo", "league": "Liga",
                    "season": "Temp.", "pos": "Pos", "age": "Edad",
                    "affinity": "Afinidad de estilo",
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
            st.download_button("Descargar shortlist CSV", data=display_frame(show[visible]).to_csv(index=False).encode('utf-8'),
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
                d4.metric("Afinidad con el estilo", f"{top.get('affinity', 0):.3f}")

    # ── Tab 2: Similares ──────────────────────────────────────────────────────
    with tab2:
        st.subheader("🔗 Jugadores similares")
        st.caption('Distancia de perfil estandarizado; menor distancia indica mayor cercanía. '
                   'La puntuación de similitud no es una probabilidad de éxito.')

        references = market_players
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
            sim = sim[sim.league.isin(selected_leagues)]
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
                display_frame(sim[[column for column in ['player', 'team', 'pos', 'age', 'league', 'season', 'distance', 'similarity',
                     'reported_market_value_eur', 'reported_valuation_date', 'price_identity_status'] if column in sim]]).rename(columns={
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

    with tab3:
        st.subheader('Grupos de jugadores con perfiles parecidos')
        st.caption('Elige cuántos grupos quieres explorar. Se agrupan las estadísticas de los jugadores de las ligas y temporada seleccionadas; esto no modifica las recomendaciones ni los seis estilos.')
        indices = rec.players.index.get_indexer(market_players.index)
        matrix = rec.X[indices]
        maximum = min(12, len(np.unique(matrix, axis=0)))
        if maximum < 2:
            st.info('No hay suficientes perfiles diferentes para formar grupos.')
        else:
            count = st.slider('Número de grupos', 2, maximum, min(6, maximum), key='explore_group_count')
            grouped = grouped_gallery(matrix, market_players, count)
            st.session_state['explore_group_members'] = grouped[['player_id', 'group', 'league']]
            summary = grouped.groupby('group').agg(Jugadores=('player_id', 'size'),
                Edad_media=('age', 'mean'), Minutos_medios=('minutes', 'mean')).round(1).reset_index()
            summary = summary.rename(columns={'group': 'Grupo', 'Edad_media': 'Edad media', 'Minutos_medios': 'Minutos medios'})
            st.dataframe(summary, hide_index=True, use_container_width=True)
            chosen = st.selectbox('Grupo a explorar', sorted(grouped.group.unique()), format_func=lambda g: f'Grupo {g}', key='explore_group')
            members = grouped[grouped.group.eq(chosen)].sort_values(['pos_main', 'player'])
            st.caption(f'Grupo {chosen} · {len(members)} jugadores. Los números de grupo pueden cambiar al modificar el mercado o el número de grupos.')
            st.markdown('**Estadísticas medias del grupo**')
            averages = members[rec.artifacts.feature_cols].mean().rename(index=field_label).round(2)
            st.dataframe(averages.rename('Media').rename_axis('Estadística').reset_index(), hide_index=True)
            member_fields = ['player', 'team', 'league', 'pos_main', 'age', 'minutes'] + rec.artifacts.feature_cols
            if budget_data_available:
                members = attach_reported_values(members, price_links, reported_values, valuation_cutoff)
                member_fields += ['reported_market_value_eur', 'reported_valuation_date']
            st.dataframe(display_frame(members[member_fields]), hide_index=True, use_container_width=True)
            st.download_button('Descargar jugadores del grupo', display_frame(members[member_fields]).to_csv(index=False).encode(),
                               file_name='scouting_group.csv', mime='text/csv')

    with tab4:
        st.subheader('Perfiles, historial y comparación')
        profiles = market_players.sort_values(['player', 'player_id'])
        labels = {int(row.player_id): f'{row.player} · {row.team} · {row.season}' for row in profiles.itertuples()}
        previous = st.session_state.get('comparison_players')
        if previous is not None:
            st.session_state['comparison_players'] = [i for i in previous if i in labels]
        selected_ids = st.multiselect('Jugadores a comparar', list(labels), default=list(labels)[:2],
                                      format_func=lambda value: labels[value], key='comparison_players')
        if not selected_ids:
            st.info('Selecciona uno o varios jugadores para ver sus perfiles e historiales.')
        else:
            compared = profiles.set_index('player_id').loc[selected_ids].reset_index()
            fields = ['player', 'team', 'league', 'season', 'pos_main', 'age', 'minutes'] + rec.artifacts.feature_cols
            if budget_data_available:
                compared = attach_reported_values(compared, price_links, reported_values, valuation_cutoff)
                fields += ['reported_market_value_eur', 'reported_valuation_date']
                st.caption('Valoraciones reportadas; las asociaciones de identidad están pendientes de revisión individual. No son costes de fichaje.')
            st.dataframe(display_frame(compared[fields]), hide_index=True, use_container_width=True)
            st.download_button('Descargar comparación', display_frame(compared[fields]).to_csv(index=False).encode(),
                               file_name='scouting_comparison.csv', mime='text/csv')
            combined = go.Figure()
            for row in compared.itertuples(index=False):
                player_row = compared[compared.player_id.eq(row.player_id)].iloc[0]
                trace = radar_figure(player_row, rec.artifacts.feature_cols, str(row.player), rec.players).data[0]
                trace.fill = 'none'
                trace.line.color = None
                combined.add_trace(trace)
            combined.update_layout(radar_figure(compared.iloc[0], rec.artifacts.feature_cols, 'Comparación de perfiles', rec.players).layout)
            combined.update_layout(showlegend=True, height=520)
            st.plotly_chart(combined, use_container_width=True, key='comparison_radar')
            st.caption('Escala relativa al percentil 95 de la temporada. Los valores desconocidos quedan sin trazar, no se sustituyen por cero.')
            for row in compared.itertuples(index=False):
                with st.expander(f'Perfil e historial · {row.player} · {row.team}', expanded=True):
                    st.plotly_chart(radar_figure(compared[compared.player_id.eq(row.player_id)].iloc[0],
                        rec.artifacts.feature_cols, str(row.player), rec.players), use_container_width=True, key=f'player_radar_{row.player_id}')
                    history = service.history[service.history.entity_id.eq(row.entity_id)].sort_values(['season', 'league', 'team'])
                    history_fields = ['season', 'league', 'team', 'minutes', 'gls', 'ast', 'partial_season']
                    st.dataframe(display_frame(history[history_fields]), hide_index=True, use_container_width=True)

    with tab5:
        st.subheader('Datos disponibles')
        st.caption('Estadísticas FBref de temporadas observadas. Los perfiles completos que permiten los seis estilos llegan hasta 2023/24; las temporadas incompletas no se ofrecen.')
        available = service.gallery.groupby(['season', 'league']).agg(Jugadores=('entity_id', 'nunique')).reset_index()
        st.dataframe(display_frame(available), hide_index=True, use_container_width=True)
        st.caption('Solo se ofrecen jugadores con al menos 450 minutos y suficientes estadísticas. Un valor desconocido no equivale a cero. La evaluación técnica está documentada en los notebooks del proyecto.')

    if budget_data_available:
        with tab6:
            from copy import deepcopy
            from src.app.scenario_ui import render_scenarios
            scenario_rec = deepcopy(rec)
            scenario_rec.players = market_players.copy().reset_index(drop=True)
            scenario_rec.X = matrix.copy()
            scenario_rec.artifacts.player_ids = scenario_rec.players.player_id.to_numpy()
            scenario_rec.configure_neighbors(scenario_rec.neighbor_method)
            render_scenarios(scenario_rec, service, price_links, reported_values,
                             selected_leagues[0] if len(selected_leagues) == 1 else 'Todas')


if __name__ == "__main__":
    main()
