"""FBref category joins at player/club/league/season grain."""
import pandas as pd

LEAGUES = ['La Liga', 'Premier League', 'Bundesliga', 'Serie A', 'Ligue 1']

KEYS = ['source_player_id', 'league', 'season', 'team']

MAPPINGS = {
    'shooting': {'Sh_Standard': 'sh', 'SoT_Standard': 'sot'},
    'defense': {'Int': 'int', 'TklW_Tackles': 'tklw'},
    'misc': {'Crs': 'crs', 'Fls': 'fls', 'Fld': 'fld'},
    'passing': {'Cmp_Total': 'passes_completed', 'Att_Total': 'passes_attempted', 'KP': 'key_passes'},
    'possession': {'Touches_Touches': 'touches', 'Succ_Take': 'successful_take_ons'},
}

def select_rows(frame):
    selected = frame[frame.Comp.isin(LEAGUES) & pd.to_numeric(frame.Season_End_Year).between(2021, 2026)].copy()
    selected['source_player_id'] = selected.Url.str.extract(r'/players/([^/]+)', expand=False)
    selected['team'] = selected.Squad
    selected['league'] = selected.Comp
    selected['season'] = selected.Season_End_Year.map(lambda year: f'{int(year)-1}-{int(year)}')
    if selected[KEYS].isna().any().any() or selected.duplicated(KEYS).any():
        raise ValueError('Missing or conflicting source/league/club/season identity')
    return selected

def align_category(standard, auxiliary, columns):
    joined = standard[KEYS+['Min_Playing']].merge(auxiliary[KEYS+['Mins_Per_90']+list(columns)],
                                                on=KEYS, how='left', validate='one_to_one', indicator=True)
    diff = (pd.to_numeric(joined.Min_Playing, errors='coerce')/90 - pd.to_numeric(joined.Mins_Per_90, errors='coerce')).abs()
    compatible = joined._merge.eq('both') & diff.le(.061)
    joined['category_key_matched'] = joined._merge.eq('both')
    joined['category_exposure_compatible'] = compatible
    for column in columns: joined[column] = pd.to_numeric(joined[column], errors='coerce').where(compatible)
    return joined, joined[KEYS+list(columns)].rename(columns=columns)

def dominant_league_gallery(frame):
    """One source identity per season; keep the highest-minutes league, never blend competitions."""
    return frame.sort_values(['season', 'entity_id', 'minutes', 'league'], ascending=[True, True, False, True])\
        .drop_duplicates(['entity_id', 'season']).sort_values(['season', 'league', 'player_id']).reset_index(drop=True)
