"""User-facing presentation shared across scouting views."""
import streamlit as st
import pandas as pd

CSS = '''<style>
:root { --scout-accent: #51deb2; }
[data-testid="stAppViewContainer"] { background: #101b28; color: #eaf2f8; }
[data-testid="stSidebar"] { background: #172536; border-right: 1px solid #304357; }
[data-testid="stHeader"] { background: rgba(16,27,40,.94); }
.block-container { max-width: 1500px; padding-top: 2rem; padding-bottom: 3rem; }
h1 { font-size: 2.3rem !important; letter-spacing: -.04em; font-weight: 750 !important; }
h2,h3 { letter-spacing: -.02em; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #b8c7d8; }
[data-testid="stMetric"] { background: #1a2b3e; border: 1px solid #304357; border-radius: 14px; padding: 1rem; }
[data-testid="stMetricValue"] { color: #51deb2; font-size: 1.8rem; }
[data-testid="stMetricLabel"] { color: #d2deea; }
[data-baseweb="tab-list"] { gap: .4rem; overflow-x: auto; padding-bottom: .35rem; }
[data-baseweb="tab"] { white-space: nowrap; border-radius: 8px 8px 0 0; padding: .65rem 1rem; }
[aria-selected="true"][data-baseweb="tab"] { color: #51deb2; background: #1b3443; }
[data-testid="stBaseButton-primary"] { border-radius: 10px; font-weight: 650; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px; }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
button:focus-visible, a:focus-visible { outline: 3px solid #51deb2 !important; outline-offset: 3px; }
@media (max-width: 768px) {
 .block-container { padding: 1rem .75rem 2rem; }
 h1 { font-size: 1.7rem !important; }
 [data-testid="stMetricValue"] { font-size: 1.4rem; }
 .st-key-market_metrics [data-testid="stHorizontalBlock"] { display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; }
 .st-key-market_metrics [data-testid="stColumn"] { width: 100% !important; min-width: 0 !important; }
 .st-key-market_metrics [data-testid="stMetric"] { padding: .7rem; }
 .st-key-market_metrics [data-testid="stMetricLabel"] { font-size: .8rem; }
 [data-baseweb="tab"] { padding: .5rem .65rem; }
}
</style>'''


def shortlist_cards(result):
    st.caption('Alternativas destacadas · revisa el perfil y la procedencia antes de decidir.')
    for column, (_, row) in zip(st.columns(min(3,len(result))), result.head(3).iterrows()):
        with column.container(border=True):
            st.write(str(row.player))
            st.caption(f'{row.team} · {row.league} · {row.pos}')
            st.metric('Afinidad de estilo', f'{row.affinity:.3f}')
            age=str(int(row.age)) if pd.notna(row.age) else 'desconocida'
            st.caption(f'Edad: {age} · {int(row.minutes):,} minutos')
            if 'reported_value_screenable' in row and row.reported_value_screenable:
                st.caption(f'Valor reportado: €{row.reported_market_value_eur:,.0f} · identidad provisional')
            else:
                st.caption('Valor de mercado: desconocido')


def reset_search_filters():
    for key in list(st.session_state):
        if key.startswith('scout_filter_') or key in ['last_result','last_filters','scouting_case','similar_result']:
            st.session_state.pop(key, None)
