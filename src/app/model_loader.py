"""Verify and load the single six-style football scouting recommender."""
import json
import pandas as pd
from src.config import ROOT
from src.app.scouting_service import ScoutingService
from src.app.integrity import source_sha256
from src.data.provenance import sha256
from src.models.recommender import PlayerRecommender


def load_scouting_service():
    report=json.loads((ROOT/'reports/five_league_pipeline/experiment_manifest.json').read_text())
    for path,digest in report['serving_code_sha256'].items():
        if source_sha256(ROOT/path)!=digest:
            raise ValueError('Packaged model code fingerprint changed')
    info=report['serving_model']
    if sha256(ROOT/info['model_path'])!=info['model_sha256']:
        raise ValueError('Scouting model fingerprint changed')
    frames={}
    for key in ['scouting_gallery','player_seasons']:
        item=report['outputs'][key]
        if sha256(ROOT/item['path'])!=item['sha256']:
            raise ValueError('Scouting data fingerprint changed')
        frames[key]=pd.read_parquet(ROOT/item['path'])
    model=PlayerRecommender.load(ROOT/info['model_path'])
    if model.neighbor_method!=info['selected_method']:
        raise ValueError('Distance method differs from recorded evaluation')
    return ScoutingService(model,frames['scouting_gallery'],frames['player_seasons'],
        {**info,'gallery_scope':'five_leagues','gallery_dataset_version':report['dataset_version']},'scouting')
