"""Legacy quick entry point. Full executed analysis: 01_data_quality_eda.ipynb."""
from src.preprocessing.clean import load_players
players=load_players()
print('Source provenance:',players.provenance_status.unique())
print(players.groupby(['source','league','season']).size())
print(players[['gls_p90','ast_p90']].describe())
