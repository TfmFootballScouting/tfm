"""Vectores de estilo de juego y scoring de afinidad."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.config import FEATURE_COLS, PLAY_STYLES


def style_vector(style_key: str, feature_cols: list[str] | None = None) -> np.ndarray:
    feature_cols = feature_cols or FEATURE_COLS
    weights = PLAY_STYLES[style_key]["weights"]
    vec = np.array([float(weights.get(c, 0.0)) for c in feature_cols], dtype=float)
    if np.abs(vec).sum() == 0:
        raise ValueError("No measured features support this style")
    return vec / np.abs(vec).sum()


def list_styles() -> dict:
    return {
        k: {"label": v["label"], "description": v["description"]}
        for k, v in PLAY_STYLES.items()
    }


def affinity_scores(
    X: np.ndarray,
    style_key: str,
    feature_cols: list[str] | None = None,
) -> np.ndarray:
    """Similitud coseno entre perfil del jugador y vector de estilo."""
    feature_cols = feature_cols or FEATURE_COLS
    style = style_vector(style_key, feature_cols).reshape(1, -1)
    # Normalizar jugadores
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    Xn = X / norms
    sn = style / (np.linalg.norm(style) + 1e-12)
    return (Xn @ sn.T).ravel()


def build_scaler(df_features: pd.DataFrame) -> tuple[StandardScaler, np.ndarray]:
    scaler = StandardScaler()
    X = scaler.fit_transform(df_features.values)
    return scaler, X


def measured_weight_fraction(style_key, feature_cols):
    weights = PLAY_STYLES[style_key]['weights']
    return sum(abs(w) for c,w in weights.items() if c in feature_cols) / sum(abs(w) for w in weights.values())
