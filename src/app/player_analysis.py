"""Source-specific player development and shot exploration without identity merges."""
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from src.config import ROOT
from src.data.provenance import sha256
from src.app.ui_helpers import display_frame,field_label

SITUATIONS={'OpenPlay':'Juego abierto','FromCorner':'Tras un córner','SetPiece':'Balón parado','DirectFreekick':'Tiro libre directo','Penalty':'Penalti'}
OUTCOMES={'Goal':'Gol','MissedShots':'Fuera','SavedShot':'Parada','BlockedShot':'Bloqueado','ShotOnPost':'Poste'}
SHOT_FIELDS={'player':'Jugador','team':'Equipo','season':'Temporada','shot_date':'Fecha','minute':'Minuto','result':'Resultado','situation':'Situación','shotType':'Tipo de tiro','xG':'Goles esperados del tiro'}


@st.cache_data
def load_analysis_shots():
    report=json.loads((ROOT/'data/processed/review/manifest.json').read_text(encoding='utf8'))
    info=report['outputs']['understat_shots']
    path=ROOT/info['parquet_path']
    if sha256(path)!=info['parquet_sha256']:
        raise ValueError('Shot dataset fingerprint changed')
    shots=pd.read_parquet(path)
    if shots.duplicated(['league','shot_id']).any():
        raise ValueError('Duplicate source shot identity')
    shots['source_player_id']=shots.source_player_id.astype(str)
    return shots


def shot_coverage(shots,league,season):
    g=shots[shots.league.eq(league)&shots.season.eq(season)]
    start=int(season[:4])
    expected=306 if league=='Bundesliga' or (league=='Ligue 1' and start>=2023) else 380
    return int(g.match_id.nunique()),expected


def shot_map(frame):
    f=frame.copy()
    f['Resultado']=f.result.map(OUTCOMES).fillna('Otro resultado')
    f['Situación']=f.situation.map(SITUATIONS).fillna('Otra situación')
    f['Posición longitudinal']=f.X*100;f['Posición lateral']=f.Y*100
    f['Minuto']=f.minute;f['Fecha']=f.shot_date.dt.strftime('%Y-%m-%d')
    f['Goles esperados del tiro']=f.xG
    # Preserve xG=0 as a real event with a visible marker.
    f['Tamaño del marcador']=.03+f.xG
    fig=px.scatter(f,x='Posición longitudinal',y='Posición lateral',color='Resultado',
        size='Tamaño del marcador',size_max=24,hover_data={'Situación':True,'Minuto':True,'Fecha':True,'Goles esperados del tiro':':.3f','Tamaño del marcador':False},
        color_discrete_map={'Gol':'#51deb2','Fuera':'#b8c7d8','Parada':'#3498db','Bloqueado':'#f0c040','Poste':'#e67e22'},
        title='Mapa de tiros observados')
    fig.add_shape(type='rect',x0=0,y0=0,x1=100,y1=100,line=dict(color='#b8c7d8',width=1))
    fig.update_layout(template='plotly_dark',height=500,paper_bgcolor='#172536',plot_bgcolor='#101b28',
        xaxis=dict(range=[0,100],title='Hacia la portería → · coordenada de la fuente (%)'),
        yaxis=dict(range=[0,100],title='Ancho · coordenada de la fuente (%)'),
        legend=dict(orientation='h',y=-.2),margin=dict(l=40,r=15,t=50,b=85))
    return fig


def development_plot_data(history, seasons):
    """Insert NaN display gaps, never fabricated statistics or appearances."""
    pieces=[]
    for (entity,league),g in history.groupby(['entity_id','league'],sort=False):
        if g.season.duplicated().any():raise ValueError('Development history requires one source entity/league/season')
        filled=g.set_index('season').reindex(seasons).rename_axis('season').reset_index()
        filled['entity_id']=entity
        filled['league']=league
        filled['Jugador del historial']=g['Jugador del historial'].iloc[0]
        pieces.append(filled)
    return pd.concat(pieces,ignore_index=True)


def render_development(service,selected_leagues):
    st.subheader('Evolución del jugador')
    st.caption('Historial FBref por identidad de esta fuente. Cambios de minutos, club y liga afectan las comparaciones; una tendencia no demuestra mejora de talento.')
    candidates=service.history[service.history.league.isin(selected_leagues)].sort_values(['season','player'])
    latest=candidates.drop_duplicates('entity_id',keep='last').sort_values('player')
    labels={r.entity_id:f'{r.player} · {r.team} · último registro {r.season}' for r in latest.itertuples()}
    if not labels:
        st.info('No hay historial para las ligas seleccionadas.');return
    previous=st.session_state.get('development_players')
    if previous is not None:st.session_state['development_players']=[i for i in previous if i in labels]
    recommended=st.session_state.get('last_result',pd.DataFrame()).get('entity_id',pd.Series(dtype=str)).tolist()
    default=next((i for i in recommended if i in labels),next(iter(labels)))
    ids=st.multiselect('Jugadores para ver su evolución',list(labels),default=[default],format_func=lambda i:labels[i],key='development_players')
    if not ids:
        st.info('Selecciona uno o varios jugadores para comparar su evolución.');return
    complete=st.checkbox('Mostrar solo temporadas completas',value=True,key='development_complete')
    other_leagues=st.checkbox('Incluir historial en otras ligas disponibles',value=True,key='development_other_leagues')
    minutes=st.slider('Minutos mínimos por temporada de evolución',0,3000,450,step=90,key='development_minutes')
    history=service.history[service.history.entity_id.isin(ids)].copy()
    if not other_leagues:history=history[history.league.isin(selected_leagues)]
    if complete:history=history[~history.partial_season]
    history=history[history.minutes.ge(minutes)].sort_values(['season','entity_id'])
    metrics=['gls_p90','ast_p90','xg_p90','sh_p90','sot_p90','minutes']
    metric=st.selectbox('Estadística para seguir',metrics,format_func=field_label,key='development_metric')
    if history.empty:
        st.info('No hay temporadas con esos requisitos.');return
    if history.partial_season.any():st.warning('El historial incluye temporadas parciales: revisa minutos y cobertura antes de comparar.')
    # Each source entity/league is a separate series; never blend competitions.
    series_labels={identifier:f'{index+1} · {labels[identifier].rsplit(" · último registro ",1)[0]}' for index,identifier in enumerate(ids)}
    history['Jugador del historial']=history.entity_id.map(series_labels)+' · '+history.league
    axis=sorted(service.history.loc[~service.history.partial_season if complete else service.history.season.notna(),'season'].unique())
    chart=development_plot_data(history,axis)
    fig=px.line(chart,x='season',y=metric,color='Jugador del historial',markers=True,
        labels={'season':'Temporada',metric:field_label(metric),'team':'Equipo','league':'Liga','minutes':'Minutos'},hover_data=['team','league','minutes'],template='plotly_dark')
    fig.update_traces(connectgaps=False)
    st.plotly_chart(fig,use_container_width=True,key='development_chart')
    st.caption('Valores desconocidos quedan sin trazar. Los minutos son observados; los indicadores por 90 usan el denominador FBref. Cada jugador tiene una serie por liga; sus estadísticas no se suman entre competiciones.')
    fields=['player','season','league','team','minutes','gls','ast',metric,'partial_season']
    fields=list(dict.fromkeys(fields))
    visible=display_frame(history[fields])
    st.dataframe(visible,hide_index=True,use_container_width=True)
    st.download_button('Descargar evolución CSV',visible.to_csv(index=False).encode(),file_name='scouting_development.csv',mime='text/csv')


def render_shots(selected_leagues):
    st.subheader('Análisis de tiros')
    st.caption('Identidades Understat: selecciona un jugador de esta fuente. Los cruces con FBref siguen pendientes de revisión. La vista describe oportunidades y resultados observados.')
    try:shots=load_analysis_shots()
    except (FileNotFoundError,ValueError,KeyError) as exc:
        st.error('No se pueden verificar los datos de tiros.');st.caption(str(exc));return
    available=[] if shots.empty else sorted(set(shots.league)&set(selected_leagues))
    if not available:
        st.info('No hay archivos de tiros preparados para las ligas seleccionadas.')
        st.code('python -m scripts.four_league_acquisition --download --public-only\npython -m scripts.four_league_preprocessing')
        st.caption('Instala requirements-archives.txt para reproducir la preparación, luego reinicia Streamlit.');return
    missing=set(selected_leagues)-set(available)
    if missing:st.caption('Sin archivos locales preparados: '+', '.join(sorted(missing)))
    league=st.selectbox('Liga para analizar tiros',available,index=available.index('Premier League') if 'Premier League' in available else 0,key='shots_league')
    allow_partial=st.checkbox('Incluir temporadas parciales de tiros',value=False,key='shots_partial')
    pool=shots[shots.league.eq(league)]
    if not allow_partial:pool=pool[~pool.partial_season]
    seasons=sorted(pool.season.unique(),reverse=True)
    if not seasons:st.info('No hay temporadas disponibles con esos requisitos.');return
    season=st.selectbox('Temporada de tiros',seasons,key='shots_season')
    cohort=pool[pool.season.eq(season)]
    observed,expected=shot_coverage(shots,league,season)
    if cohort.partial_season.any():st.warning(f'Temporada parcial: {observed}/{expected} partidos registrados. No compares totales con una temporada completa.')
    elif observed<expected:st.warning(f'Cobertura incompleta: {observed}/{expected} partidos registrados; faltan {expected-observed}.')
    else:st.caption(f'{observed}/{expected} partidos registrados. El recuento no confirma independientemente que estén todos los tiros.')
    attempts=cohort[cohort.result.ne('OwnGoal')]
    players=attempts.groupby('source_player_id').agg(player=('player',lambda s:s.mode().iloc[0]),attempts=('shot_id','size'),clubs=('team',lambda s:', '.join(sorted(s.dropna().unique())))).sort_values(['attempts','player'],ascending=[False,True])
    if players.empty:st.info('No hay intentos de tiro registrados.');return
    names={str(i):f'{r.player} · {r.clubs}' for i,r in players.iterrows()}
    identifier=st.selectbox('Jugador para analizar tiros',list(names),format_func=lambda i:names[i],key='shots_player')
    situations=st.multiselect('Situaciones de tiro',list(SITUATIONS),default=list(SITUATIONS),format_func=lambda s:SITUATIONS[s],key='shots_situations')
    player=attempts[attempts.source_player_id.eq(identifier)&attempts.situation.isin(situations)].copy()
    if player.empty:st.info('No hay tiros con esas situaciones.');return
    a,b,c,d=st.columns(4)
    a.metric('Tiros observados',len(player));b.metric('Goles',int(player.result.eq('Goal').sum()))
    c.metric('Goles esperados',f'{player.xG.sum():.2f}');d.metric('Goles esperados por tiro',f'{player.xG.mean():.3f}')
    st.plotly_chart(shot_map(player),use_container_width=True,key='source_shot_map')
    st.caption('Tamaño del punto: calidad de la oportunidad según xG. Las coordenadas están normalizadas, no son metros reales. Los autogoles se excluyen de los intentos y goles de esta vista. No hay tasas por 90 sin minutos verificados.')
    trend=attempts[attempts.source_player_id.eq(identifier)&attempts.situation.isin(situations)].groupby('shot_date').agg(Tiros=('shot_id','size'),Goles_esperados=('xG','sum')).reset_index().sort_values('shot_date')
    # This is a match-date series, not a filled appearance log.
    fig=px.bar(trend,x='shot_date',y='Goles_esperados',labels={'shot_date':'Fecha con tiros registrados','Goles_esperados':'Goles esperados'},hover_data=['Tiros'],template='plotly_dark')
    st.plotly_chart(fig,use_container_width=True,key='source_shot_trend')
    st.caption('Solo fechas con tiros registrados; los partidos sin tiros del jugador no se inventan como apariciones.')
    table=player[['shot_date','team','minute','result','situation','shotType','xG']].copy()
    table['result']=table.result.map(OUTCOMES);table['situation']=table.situation.map(SITUATIONS)
    table['shotType']=table.shotType.map({'RightFoot':'Pie derecho','LeftFoot':'Pie izquierdo','Head':'Cabeza','OtherBodyPart':'Otra parte del cuerpo'})
    table=table.rename(columns=SHOT_FIELDS).sort_values('Fecha')
    st.dataframe(table,hide_index=True,use_container_width=True)
    st.download_button('Descargar tiros CSV',table.to_csv(index=False).encode(),file_name='scouting_shots.csv',mime='text/csv')
