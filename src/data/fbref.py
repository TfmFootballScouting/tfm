"""Normalize FBref tables with validated source-ID/club/season joins."""
import pandas as pd

STANDARD = {'player':'player', 'team':'team', 'position':'pos', 'nationality':'nation',
            'age':'age', 'minutes':'minutes', 'games':'mp', 'goals':'gls', 'assists':'ast'}
AUXILIARY = {'shots':'sh', 'shots_on_target':'sot', 'interceptions':'int',
             'tackles_won':'tklw', 'crosses':'crs', 'fouls':'fls', 'fouled':'fld'}
KEYS = ['source_player_id','team','league','season']


def merge_tables(standard, additional):
    base = standard.rename(columns=STANDARD).copy()
    if not set(KEYS) <= set(base):
        raise ValueError('FBref source ID, club, league and season required')
    if base.duplicated(KEYS).any():
        raise ValueError('Duplicate standard keys')
    for table in additional:
        aux = table.rename(columns=AUXILIARY).copy()
        if not set(KEYS) <= set(aux):
            raise ValueError('Ancillary table lacks stable merge keys')
        cols = [c for c in AUXILIARY.values() if c in aux and c not in base]
        if cols:
            base = base.merge(aux[KEYS+cols],on=KEYS,how='left',validate='one_to_one')
    return base
