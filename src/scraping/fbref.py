"""Extracción de datos FBref (caché local / soccerdata) y dataset demo."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    DATA_RAW,
    LEAGUES,
    MIN_MINUTES,
    RANDOM_SEED,
    SEASONS,
    SOCCERDATA_FBREF,
    STAT_TYPES,
)


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [
            "_".join(str(c) for c in col if not str(c).startswith("Unnamed")).strip("_")
            if isinstance(col, tuple)
            else str(col)
            for col in df.columns
        ]
    return df


def _read_fbref_html_table(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    tables = pd.read_html(path)
    candidates = [t for t in tables if t.shape[0] > 50 and t.shape[1] > 10]
    if not candidates:
        return None
    df = _flatten_columns(candidates[-1])
    # Quitar filas de cabecera repetidas
    if "Player" in df.columns:
        df = df[df["Player"].astype(str) != "Player"]
    return df.reset_index(drop=True)


def load_from_soccerdata_cache(league_key="ESP-La Liga", season="2324"):
    """Compatibility adapter; join cached HTML by stable source IDs, never row index."""
    from src.scraping.collect import parse_fbref
    from src.data_preparation.fbref import merge_tables
    frames = {}
    for stat in STAT_TYPES:
        path = SOCCERDATA_FBREF / f"players_{league_key}_{season}_{stat}.html"
        if path.exists():
            frame = parse_fbref(path.read_text(encoding="utf8"), stat)
            frame["league"] = LEAGUES.get(league_key, league_key)
            frame["season"] = season
            frames[stat] = frame
    if "standard" not in frames:
        return None
    result = merge_tables(frames["standard"], [f for key,f in frames.items() if key != "standard"])
    result["source"] = "fbref"
    return result


def try_soccerdata_download(league: str, season: str, stat_type: str = "standard") -> pd.DataFrame | None:
    """Intenta descargar vía soccerdata; puede fallar por CAPTCHA/red."""
    try:
        import soccerdata as sd

        fb = sd.FBref(leagues=league, seasons=season)
        df = fb.read_player_season_stats(stat_type=stat_type)
        return df.reset_index()
    except Exception as exc:  # noqa: BLE001
        print(f"[scraping] No se pudo descargar {league} {season} {stat_type}: {exc}")
        return None


def generate_demo_players(n: int = 1800, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Dataset sintético realista (La Liga + Segunda, varias temporadas)."""
    rng = np.random.default_rng(seed)
    teams_l1 = [
        "Real Madrid", "Barcelona", "Atlético", "Real Sociedad", "Athletic",
        "Betis", "Villarreal", "Sevilla", "Valencia", "Osasuna",
        "Girona", "Celta", "Mallorca", "Rayo", "Getafe", "Las Palmas",
        "Alavés", "Leganés", "Espanyol", "Valladolid",
    ]
    teams_l2 = [
        "Zaragoza", "Sporting", "Oviedo", "Eibar", "Tenerife", "Racing",
        "Elche", "Levante", "Granada", "Almería", "Burgos", "Albacete",
        "Huesca", "Mirandés", "Cartagena", "Eldense", "Racing Ferrol", "Castellón",
        "Dépor", "Málaga", "Córdoba", "Zaragoza B",
    ]
    positions = ["FW", "MF", "DF", "GK", "FW,MF", "MF,DF", "DF,MF"]
    pos_p = [0.22, 0.32, 0.30, 0.08, 0.04, 0.02, 0.02]
    first = [
        "Álex", "Carlos", "Iván", "Hugo", "Pablo", "Marc", "Sergio", "Javier",
        "Unai", "Iker", "Nico", "Yeremy", "Lamine", "Pedri", "Gavi", "Rodri",
        "Fermín", "Bryan", "Samu", "Ayoze", "Mikel", "Oihan", "Takefusa", "Ante",
    ]
    last = [
        "García", "López", "Martínez", "Sánchez", "Pérez", "González", "Ruiz",
        "Díaz", "Torres", "Ramírez", "Navarro", "Moreno", "Jiménez", "Alonso",
        "Castro", "Romero", "Iglesias", "Vargas", "Núñez", "Ortega",
    ]

    rows = []
    for i in range(n):
        league = "La Liga" if i % 5 < 3 else "Segunda"
        season = SEASONS[i % len(SEASONS)]
        team = rng.choice(teams_l1 if league == "La Liga" else teams_l2)
        pos = rng.choice(positions, p=pos_p)
        age = int(rng.integers(17, 37))
        minutes = float(rng.integers(200, 3400))
        n90 = max(minutes / 90.0, 0.1)

        # Perfiles por posición
        if pos == "GK":
            gls = rng.poisson(0.05)
            ast = rng.poisson(0.02)
            sh = rng.poisson(0.1)
            sot = 0
            crs = rng.poisson(0.2)
            ints = rng.poisson(1.5 * n90 / 10)
            tkl = rng.poisson(0.5 * n90 / 10)
        elif "FW" in pos:
            gls = rng.poisson(0.35 * n90)
            ast = rng.poisson(0.18 * n90)
            sh = rng.poisson(2.2 * n90)
            sot = rng.binomial(max(int(sh), 1), 0.35)
            crs = rng.poisson(1.2 * n90)
            ints = rng.poisson(0.4 * n90)
            tkl = rng.poisson(0.5 * n90)
        elif "MF" in pos:
            gls = rng.poisson(0.12 * n90)
            ast = rng.poisson(0.22 * n90)
            sh = rng.poisson(1.1 * n90)
            sot = rng.binomial(max(int(sh), 1), 0.32)
            crs = rng.poisson(1.8 * n90)
            ints = rng.poisson(1.3 * n90)
            tkl = rng.poisson(1.4 * n90)
        else:
            gls = rng.poisson(0.05 * n90)
            ast = rng.poisson(0.06 * n90)
            sh = rng.poisson(0.4 * n90)
            sot = rng.binomial(max(int(sh), 1), 0.25)
            crs = rng.poisson(0.8 * n90)
            ints = rng.poisson(1.8 * n90)
            tkl = rng.poisson(1.6 * n90)

        fls = rng.poisson(1.1 * n90)
        fld = rng.poisson(1.0 * n90)
        name = f"{rng.choice(first)} {rng.choice(last)} {i%97}"

        rows.append(
            {
                "player": name,
                "team": team,
                "pos": pos,
                "age": age,
                "nation": rng.choice(["ESP", "ARG", "FRA", "BRA", "POR", "MAR", "URU", "NGA"]),
                "league": league,
                "season": season,
                "minutes": minutes,
                "mp": int(min(38, max(1, round(minutes / 70)))),
                "nineties": round(n90, 2),
                "gls": int(gls),
                "ast": int(ast),
                "ga": int(gls + ast),
                "sh": int(sh),
                "sot": int(sot),
                "crs": int(crs),
                "int": int(ints),
                "tklw": int(tkl),
                "fls": int(fls),
                "fld": int(fld),
                "source": "demo",
            }
        )

    return pd.DataFrame(rows)


def build_raw_dataset(use_demo_if_needed: bool = False) -> pd.DataFrame:
    """Deprecated legacy entry point: never mix synthetic and real data."""
    if use_demo_if_needed:
        raise ValueError("Synthetic fallback removed. Use source collection or explicit separate demonstrations.")
    raise RuntimeError("Use python -m src.scraping.collect then python -m src.pipeline")
