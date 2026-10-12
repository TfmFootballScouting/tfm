"""Serve separately trained five-league models with verified real galleries."""
import json
import pandas as pd
from src.config import ROOT
from src.app.collected import CollectedService
from src.app.fingerprints import source_sha256
from src.data.provenance import sha256
from src.models.recommend import PlayerRecommender


def load_trained_service(name):
    if name not in ['core']: raise ValueError('Unsupported serving model')
    report=json.loads((ROOT/'models/real/runtime_manifest.json').read_text())
    for path,digest in report['code_sha256'].items():
        if path.startswith('src/') and source_sha256(ROOT/path)!=digest:
            raise ValueError('Five-league training source fingerprint changed')
    info=report['experiments'][name]
    if sha256(ROOT/info['model_path'])!=info['model_sha256']: raise ValueError('Five-league model fingerprint changed')
    frames={}
    for key in [f'{name}_gallery','player_seasons']:
        item=report['outputs'][key]
        if sha256(ROOT/item['path'])!=item['sha256']: raise ValueError('Five-league trained gallery fingerprint changed')
        frames[key]=pd.read_parquet(ROOT/item['path'])
    model=PlayerRecommender.load(ROOT/info['model_path'])
    if model.neighbor_method!=info['selected_method']: raise ValueError('Distance method differs from evaluation')
    return CollectedService(model,frames[f'{name}_gallery'],frames['player_seasons'],
        {**info,'gallery_scope':'five_leagues_trained','gallery_dataset_version':report['dataset_version']},name)
