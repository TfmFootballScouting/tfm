"""Independent, explicit scenario execution for the collected application."""
from dataclasses import asdict
import json
import uuid
import streamlit as st
from src.app.scenarios import Requirements, TEMPLATES, analyze_scenario
from src.process.events import record_event
from src.app.scouting_views import display_frame, POSITIONS
from src.features.styles import list_styles


def render_scenarios(rec, service, links, values, selected_league="Todas"):
    st.subheader('Escenarios de scouting')
    st.caption('Supuestos ilustrativos y ajustables, no requisitos oficiales del club. Una vacante: cada jugador es una alternativa. '
               'Valores reportados a 30 de junio de la temporada observada; no son costes de fichaje. '
               'Identidades provisionales, moneda EUR supuesta y fecha de publicación desconocida: análisis retrospectivo, no validación histórica.')
    if service is None or values is None:
        st.info('Se necesitan un modelo evaluado y datos de valoración reportada.')
        return
    options = [label for label, template in TEMPLATES.items() if template['style'] in service.supported_styles]
    label = st.selectbox('Plantilla de requisitos', options)
    template = TEMPLATES[label]
    clubs = sorted({club for item in rec.players.clubs for club in json.loads(item)})
    league_options = ['Todas'] + sorted(rec.players.groupby('league').size().loc[lambda counts: counts >= 10].index)
    scenario_league = st.selectbox('Liga del escenario', league_options, index=league_options.index(selected_league))
    club = st.selectbox('Club del escenario', clubs, index=clubs.index('Valencia') if 'Valencia' in clubs else 0)
    # Template-specific keys prevent old widget values from overriding a new template.
    position = st.selectbox('Posición del escenario', ['DF', 'MF', 'FW'],
                            index=['DF', 'MF', 'FW'].index(template['position']), format_func=lambda p: POSITIONS[p], key=f'scenario_position_{label}')
    style = st.selectbox('Estilo del escenario', service.supported_styles,
                         index=service.supported_styles.index(template['style']), format_func=lambda s: list_styles()[s]['label'], key=f'scenario_style_{label}')
    age = st.number_input('Edad máxima del escenario', min_value=18, max_value=45, value=template['max_age'], key=f'scenario_age_{label}')
    minutes = st.number_input('Minutos mínimos del escenario', min_value=450, max_value=10000, value=template['min_minutes'], key=f'scenario_minutes_{label}')
    budget = st.number_input('Techo de valor reportado del escenario (M€)', min_value=.01, value=template['budget_million'], key=f'scenario_budget_{label}')
    size = st.number_input('Alternativas del escenario', min_value=1, max_value=50, value=5)
    req = Requirements(club, str(rec.players.season.iloc[0]), position, style, int(age), int(minutes), float(budget), int(size), None if scenario_league == "Todas" else scenario_league)
    signature = (service.name, service.info.get('gallery_scope', 'La Liga'), service.info.get('gallery_dataset_version'), tuple(sorted(rec.players.league.unique())), tuple(asdict(req).items()))
    if st.session_state.get('scenario_signature') != signature:
        st.session_state.pop('scenario_result', None)
        st.session_state.pop('scenario_case', None)
    if st.button('Ejecutar escenario'):
        result = analyze_scenario(rec, req, links, values)
        case = str(uuid.uuid4())
        attrs = {**asdict(req), 'model': service.name, 'scenario_kind': 'illustrative_retrospective',
                 'valuation_cutoff': str(req.valuation_cutoff.date()), 'historical_budget_eligible': False}
        record_event(case, 'need_defined', 'application_user', attrs)
        record_event(case, 'search_executed', 'application_user', attrs)
        record_event(case, 'ranking_generated', 'application', {**attrs, 'returned': len(result['shortlist'])})
        st.session_state['scenario_result'] = result
        st.session_state['scenario_case'] = case
        st.session_state['scenario_signature'] = signature
    result = st.session_state.get('scenario_result')
    if result is None: return
    st.markdown('**Cobertura de requisitos**')
    funnel = result['funnel'].copy()
    names = {'gallery': 'Jugadores del mercado', 'target_league': 'Liga elegida',
             'broad_position': 'Posición requerida', 'known_age_within_ceiling': 'Edad máxima',
             'minimum_minutes': 'Minutos mínimos', 'exclude_all_own_club_stints': 'Excluir jugadores del club',
             'known_positive_reported_value': 'Valor de mercado disponible', 'reported_value_ceiling': 'Dentro del presupuesto'}
    funnel['stage'] = funnel.stage.map(lambda v: names.get(v, v))
    st.dataframe(funnel.rename(columns={'stage': 'Requisito', 'count': 'Jugadores restantes'}), hide_index=True)
    shortlist = result['shortlist']
    if shortlist.empty: st.warning('Ningún candidato satisface todos los requisitos. No se relajan automáticamente.')
    else:
        fields = ['player', 'team', 'pos_main', 'age', 'minutes', 'affinity', 'reported_market_value_eur',
                  'reported_valuation_date', 'price_identity_status']
        st.dataframe(display_frame(shortlist[fields]), hide_index=True)
    st.download_button('Descargar escenario CSV', display_frame(shortlist[[c for c in ['player', 'team', 'league', 'pos_main', 'age', 'minutes', 'affinity', 'reported_market_value_eur', 'reported_valuation_date'] if c in shortlist]]).to_csv(index=False).encode(),
                       file_name='scouting_scenario.csv', mime='text/csv')
    if st.button('Registrar revisión del escenario'):
        record_event(st.session_state['scenario_case'], 'shortlist_reviewed', 'application_user',
                     {'returned': len(shortlist), 'scenario_kind': 'illustrative_retrospective'})
        st.success('Revisión registrada.')
