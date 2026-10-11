"""Five-league galleries served with the unchanged, evaluated La Liga models."""
import json
from dataclasses import replace
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.app.collected import load_collected_service

LEAGUES = ['La Liga', 'Premier League', 'Bundesliga', 'Serie A', 'Ligue 1']


def load_top_five_service(name):
    original = load_collected_service(name)
    manifest = json.loads((ROOT/'reports/top_five_leagues/manifest.json').read_text())
    frames = {}
    for key in [f'{name}_gallery','player_seasons']:
        item=manifest['outputs'][key]
        if sha256(ROOT/item['path']) != item['sha256']: raise ValueError('Five-league gallery fingerprint changed')
        frames[key]=pd.read_parquet(ROOT/item['path'])
    gallery=frames[f'{name}_gallery']
    if set(gallery.league)!=set(LEAGUES): raise ValueError('Incomplete five-league coverage')
    if gallery.duplicated(['entity_id','season']).any(): raise ValueError('Ambiguous cross-league gallery identity')
    for report in ['availability.csv','evaluation.csv']:
        if sha256(ROOT/'reports/top_five_leagues'/report)!=manifest['report_sha256'][report]:
            raise ValueError('Five-league coverage/evaluation fingerprint changed')
    return replace(original,gallery=gallery,history=frames['player_seasons'],
                   info={**original.info,'gallery_scope':'five_leagues','gallery_dataset_version':manifest['dataset_version']})


def coverage_table():
    return pd.read_csv(ROOT/'reports/top_five_leagues/availability.csv')


def league_evaluation(name):
    table=pd.read_csv(ROOT/'reports/top_five_leagues/evaluation.csv')
    return table[table.model.eq(name)&table.selected_method].copy()
