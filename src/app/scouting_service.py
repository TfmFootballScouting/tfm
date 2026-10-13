"""Frozen collected-model serving with a separate observed-season gallery."""
from copy import deepcopy
from dataclasses import dataclass
import json

import numpy as np
import pandas as pd

from src.config import ROOT
from src.data_preparation.source_rights import require_model_data_use
from src.models.recommender import PlayerRecommender
from src.features.styles import measured_weight_fraction

ORIGINAL_STYLES = ('posesion', 'presion_alta', 'vertical', 'contraataque', 'solidez_defensiva', 'desborde_banda')


@dataclass
class ScoutingService:
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
