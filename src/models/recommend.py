"""Existing cosine/KNN/PCA/K-means engine with training-only preprocessing."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from src.config import FEATURE_COLS, MODELS_DIR, RANDOM_SEED
from src.features.styles import affinity_scores, measured_weight_fraction
from src.data.source_rights import require_model_data_use


@dataclass
class RecommenderArtifacts:
    imputer: SimpleImputer
    scaler: StandardScaler
    knn: NearestNeighbors
    kmeans: KMeans
    pca: PCA
    feature_cols: list[str]
    player_ids: np.ndarray


class PlayerRecommender:
    def __init__(self, n_neighbors=15, n_clusters=6, n_pca=4):
        if min(n_neighbors, n_clusters, n_pca) < 1:
            raise ValueError('Model dimensions must be positive')
        self.n_neighbors, self.n_clusters, self.n_pca = n_neighbors, n_clusters, n_pca
        self.artifacts = self.players = self.X = None

    def fit(self, players, feature_cols=None):
        require_model_data_use(players)
        if len(players) < 2:
            raise ValueError('At least two observations required')
        if players.player_id.duplicated().any():
            raise ValueError('player_id must identify unique observations')
        requested = feature_cols or [c for c in FEATURE_COLS if c in players]
        # All-empty and constant features cannot support meaningful similarity.
        cols = [c for c in requested if players[c].notna().any() and players[c].nunique() > 1]
        if not cols:
            raise ValueError('No usable features; unavailable data are not zero')
        if not np.isfinite(players[cols].dropna().to_numpy()).all():
            raise ValueError('Infinite feature values')
        self.players = players.reset_index(drop=True).copy()
        imputer = SimpleImputer(strategy='median')
        scaler = StandardScaler()
        X = scaler.fit_transform(imputer.fit_transform(self.players[cols]))
        knn = NearestNeighbors(n_neighbors=min(self.n_neighbors, len(X)), metric='cosine').fit(X)
        kmeans = KMeans(n_clusters=min(self.n_clusters, len(np.unique(X, axis=0))),
                        random_state=RANDOM_SEED, n_init=10).fit(X)
        self.players['cluster'] = kmeans.labels_
        pca = PCA(n_components=min(self.n_pca, X.shape[1], X.shape[0]), random_state=RANDOM_SEED)
        pcs = pca.fit_transform(X)
        for i in range(pcs.shape[1]):
            self.players[f'pc{i+1}'] = pcs[:, i]
        self.X = X
        self.artifacts = RecommenderArtifacts(imputer, scaler, knn, kmeans, pca, cols,
                                               self.players.player_id.to_numpy())
        return self

    def transform(self, players):
        require_model_data_use(players)
        if self.artifacts is None:
            raise RuntimeError('Model not fitted')
        return self.artifacts.scaler.transform(self.artifacts.imputer.transform(players[self.artifacts.feature_cols]))

    def recommend(self, style_key, position=None, max_age=None, max_budget=None,
                  league=None, top_n=10, cutoff=None, season=None, exclude_club=None):
        if self.players is None or self.artifacts is None:
            raise RuntimeError('Model not fitted')
        if top_n < 1:
            raise ValueError('top_n must be positive')
        if measured_weight_fraction(style_key, self.artifacts.feature_cols) < .6:
            raise ValueError('Insufficient measured features for this tactical style; use a supported profile')
        result = self.players.copy()
        result['affinity'] = affinity_scores(self.X, style_key, self.artifacts.feature_cols)
        if season:
            result = result[result.season == season]
        if cutoff:
            # Never retrospectively rank a model fitted on seasons after the decision date.
            t = pd.Timestamp(cutoff)
            model_ends = pd.to_datetime(self.players.season.str[5:] + '-06-30')
            if (model_ends > t.tz_localize(None)).any():
                raise ValueError('Model contains future/full-season information; fit on past data first')
        if position and position != 'Todas':
            result = result[result.pos.astype(str).str.split(',').map(lambda x: position.upper() in [s.strip().upper() for s in x])]
        if max_age is not None:
            result = result[result.age.notna() & (result.age <= max_age)]
        if max_budget is not None:
            required = {'market_value_eur', 'valuation_date', 'valuation_known_at'}
            if not cutoff or not required <= set(result):
                raise ValueError('Budget requires dated EUR valuations and a decision cutoff; unknown values are excluded')
            cutoff_utc = pd.Timestamp(cutoff)
            cutoff_utc = cutoff_utc.tz_localize('UTC') if cutoff_utc.tzinfo is None else cutoff_utc.tz_convert('UTC')
            result = result[(pd.to_datetime(result.valuation_date, utc=True) <= cutoff_utc) &
                            (pd.to_datetime(result.valuation_known_at, utc=True) <= cutoff_utc) &
                            result.market_value_eur.notna() & (result.market_value_eur >= 0) &
                            (result.market_value_eur <= max_budget * 1_000_000)]
        if league and league != 'Todas':
            result = result[result.league == league]
        if exclude_club:
            result = result[result.team != exclude_club]
        result = result.sort_values(['affinity', 'player_id'], ascending=[False, True])
        # Multiple season observations cannot occupy multiple shortlist slots.
        if 'entity_id' in result:
            result = result.drop_duplicates('entity_id')
        return result.head(top_n)

    def similar_players(self, player_id, top_n=10):
        if self.artifacts is None or self.players is None:
            raise RuntimeError('Model not fitted')
        idx = self.players.index[self.players.player_id == player_id]
        if len(idx) == 0:
            raise ValueError(f'Unknown player_id {player_id}')
        i = int(idx[0])
        distances, indices = self.artifacts.knn.kneighbors(self.X[i:i+1], n_neighbors=len(self.X))
        out = self.players.iloc[indices[0]].copy()
        out['similarity'] = 1 - distances[0]
        out = out[out.player_id != player_id]
        if 'entity_id' in out:
            out = out[out.entity_id != self.players.iloc[i].entity_id].drop_duplicates('entity_id')
        return out.head(top_n)

    def save(self, path=None):
        path = Path(path or MODELS_DIR / 'recommender.joblib')
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({'recommender': self, 'players': self.players}, path)
        return path

    @classmethod
    def load(cls, path=None):
        return joblib.load(path or MODELS_DIR / 'recommender.joblib')['recommender']
