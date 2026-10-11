"""Frozen collected-model serving with a separate observed-season gallery."""
from copy import deepcopy
from dataclasses import dataclass
import json

import numpy as np
import pandas as pd

from src.config import ROOT
from src.data.provenance import sha256
from src.app.fingerprints import source_sha256
from src.data.source_rights import require_model_data_use
from src.models.collected import EXPERIMENTS
from src.models.recommend import PlayerRecommender
from src.features.styles import measured_weight_fraction

ORIGINAL_STYLES = ('posesion', 'presion_alta', 'vertical', 'contraataque', 'solidez_defensiva', 'desborde_banda')


@dataclass
class CollectedService:
    model: PlayerRecommender
    gallery: pd.DataFrame
    history: pd.DataFrame
    info: dict
    name: str

    @property
    def supported_styles(self):
        return [key for key in ORIGINAL_STYLES if measured_weight_fraction(key, self.model.artifacts.feature_cols) >= .6]

    @property
    def available_seasons(self):
        # Sparse/partial seasons are not meaningful galleries for comparisons.
        counts = self.gallery.groupby('season').size()
        partial = self.gallery.groupby('season').partial_season.any()
        return sorted(counts[(counts >= 10) & ~partial].index, reverse=True)

    def for_season(self, season):
        if season not in self.available_seasons:
            raise ValueError('Insufficient complete-season gallery coverage')
        players = self.gallery[self.gallery.season.eq(season)].copy().reset_index(drop=True)
        if players.entity_id.duplicated().any() or players.player_id.duplicated().any():
            raise ValueError('Season gallery identities must be unique')
        require_model_data_use(players)
        rec = deepcopy(self.model)
        scaler_before = rec.artifacts.scaler.mean_.copy()
        imputer_before = rec.artifacts.imputer.statistics_.copy()
        rec.X = rec.transform(players)
        players['cluster'] = rec.artifacts.kmeans.predict(rec.X)
        pcs = rec.artifacts.pca.transform(rec.X)
        for index in range(pcs.shape[1]): players[f'pc{index+1}'] = pcs[:, index]
        rec.players = players
        rec.artifacts.player_ids = players.player_id.to_numpy()
        # Build an index over candidates; no medians, scaling, PCA or clusters refit.
        rec.configure_neighbors(rec.neighbor_method)
        np.testing.assert_equal(rec.artifacts.scaler.mean_, scaler_before)
        np.testing.assert_equal(rec.artifacts.imputer.statistics_, imputer_before)
        return rec


def load_collected_service(name):
    if name not in ['core', 'offensive']: raise ValueError('Unsupported serving model')
    manifest = json.loads((ROOT / 'reports/enrichment/pipeline.json').read_text())
    info = manifest['new_model_experiments'][name]
    original = json.loads((ROOT / 'reports/collected_model_results.json').read_text())
    for code in ['src/features/styles.py', 'src/config.py']:
        if source_sha256(ROOT / code) != original['code_hashes'][code]:
            raise ValueError('Style definition fingerprint changed')
    for code in ['src/models/collected.py', 'src/models/recommend.py', 'src/data/source_rights.py']:
        if source_sha256(ROOT / code) != manifest['code_sha256'][code]:
            raise ValueError('Collected model source fingerprint changed')
    model_path = ROOT / info['model_path']
    if sha256(model_path) != info['model_sha256']: raise ValueError('Model artifact fingerprint changed')
    preprocessing = json.loads((ROOT / 'reports/collected_preprocessing.json').read_text())
    frames = {}
    for table in [EXPERIMENTS[name]['table'], 'collected_player_seasons']:
        item = preprocessing['outputs'][table]
        if sha256(ROOT / item['path']) != item['sha256']: raise ValueError('Gallery fingerprint changed')
        frames[table] = pd.read_parquet(ROOT / item['path'])
    model = PlayerRecommender.load(model_path)
    if model.neighbor_method != info['selected_method']: raise ValueError('Model distance method mismatch')
    return CollectedService(model, frames[EXPERIMENTS[name]['table']], frames['collected_player_seasons'], info, name)
