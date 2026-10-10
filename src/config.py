"""Configuración central del TFM de scouting."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed" / "real"
MODELS_DIR = ROOT / "models" / "real"
DB_PATH = DATA_PROCESSED / "scouting.db"
PLAYERS_PARQUET = DATA_PROCESSED / "players.parquet"
FEATURES_PARQUET = DATA_PROCESSED / "features.parquet"

SOCCERDATA_FBREF = Path.home() / "soccerdata" / "data" / "FBref"

LEAGUES = {
    "ESP-La Liga": "La Liga",
    "ESP-Segunda División": "Segunda",
}

SEASONS = [f"{y}-{y + 1}" for y in range(2020, 2026)]
STAT_TYPES = ["standard", "shooting", "misc"]

MIN_MINUTES = 450
RANDOM_SEED = 42

# Expert-defined style directions on standardized features; affinity is not a probability.
PLAY_STYLES = {
    "posesion": {
        "label": "Posesión / construcción",
        "description": "Prioriza creación, pases y participación ofensiva sostenida.",
        "weights": {
            "gls_p90": 0.10,
            "ast_p90": 0.20,
            "sh_p90": 0.10,
            "sot_p90": 0.10,
            "crs_p90": 0.15,
            "int_p90": 0.05,
            "tklw_p90": 0.05,
            "fld_p90": 0.10,
            "ga_p90": 0.15,
        },
    },
    "presion_alta": {
        "label": "Presión alta",
        "description": "Intensidad defensiva adelantada, recuperaciones y duelos.",
        "weights": {
            "int_p90": 0.25,
            "tklw_p90": 0.25,
            "fls_p90": -0.10,
            "fld_p90": 0.05,
            "crs_p90": 0.05,
            "gls_p90": 0.05,
            "ast_p90": 0.05,
            "sh_p90": 0.05,
            "ga_p90": 0.15,
        },
    },
    "vertical": {
        "label": "Juego vertical / directo",
        "description": "Progresión ofensiva, tiros y llegada a áreas.",
        "weights": {
            "gls_p90": 0.25,
            "sh_p90": 0.20,
            "sot_p90": 0.15,
            "ast_p90": 0.10,
            "ga_p90": 0.15,
            "crs_p90": 0.10,
            "int_p90": 0.025,
            "tklw_p90": 0.025,
        },
    },
    "contraataque": {
        "label": "Contraataque",
        "description": "Transiciones rápidas: goles, asistencias y espacios.",
        "weights": {
            "gls_p90": 0.20,
            "ast_p90": 0.20,
            "ga_p90": 0.20,
            "sh_p90": 0.10,
            "sot_p90": 0.10,
            "crs_p90": 0.10,
            "int_p90": 0.05,
            "tklw_p90": 0.05,
        },
    },
    "solidez_defensiva": {
        "label": "Solidez defensiva",
        "description": "Intercepciones, entradas y disciplina táctica.",
        "weights": {
            "int_p90": 0.30,
            "tklw_p90": 0.30,
            "fls_p90": -0.10,
            "crs_p90": 0.05,
            "gls_p90": 0.05,
            "ast_p90": 0.05,
            "sh_p90": 0.05,
            "ga_p90": 0.05,
            "fld_p90": 0.05,
        },
    },
    "desborde_banda": {
        "label": "Desborde / banda",
        "description": "Centros, llegada y generación de peligro desde costados.",
        "weights": {
            "crs_p90": 0.30,
            "ast_p90": 0.20,
            "sh_p90": 0.10,
            "sot_p90": 0.10,
            "ga_p90": 0.15,
            "gls_p90": 0.10,
            "fld_p90": 0.05,
        },
    },
}

FEATURE_COLS = [
    "gls_p90",
    "ast_p90",
    "ga_p90",
    "sh_p90",
    "sot_p90",
    "crs_p90",
    "int_p90",
    "tklw_p90",
    "fls_p90",
    "fld_p90",
]

MLFLOW_TRACKING_URI = "sqlite:///mlflow.db"
MLFLOW_EXPERIMENT = "tfm-scouting-recomendacion"

# Honest limited-feature profiles when broad tactical categories lack coverage.
PLAY_STYLES['finisher'] = {'label': 'Finalizador (goles)', 'description': 'Perfil descriptivo de goles por 90; no mide pressing ni progresión.', 'weights': {'gls_p90': 1.0}}
PLAY_STYLES['creator'] = {'label': 'Asistente (asistencias)', 'description': 'Perfil descriptivo de asistencias por 90; no mide construcción con pases.', 'weights': {'ast_p90': 1.0}}
