"""Conservative cleaning: preserve unavailable statistics, no invented prices."""
from __future__ import annotations
import hashlib
import sqlite3

import numpy as np
import pandas as pd
from src.config import DATA_PROCESSED, DB_PATH, FEATURE_COLS, MIN_MINUTES, PLAYERS_PARQUET

COUNTS = ['gls', 'ast', 'ga', 'sh', 'sot', 'crs', 'int', 'tklw', 'fls', 'fld', 'xg', 'xa']


def clean_players(df, min_minutes=MIN_MINUTES):
    out = df.rename(columns={'Player': 'player', 'Squad': 'team', 'Pos': 'pos', 'Age': 'age', 'Nation': 'nation'}).copy()
    required = {'player', 'team', 'pos', 'minutes', 'season', 'league', 'source'}
    if not required <= set(out):
        raise ValueError(f'Missing columns: {sorted(required - set(out))}')
    if not out.columns.is_unique:
        raise ValueError('Duplicate column names; resolve the source schema first')
    if out.source.isna().any() or out.source.astype(str).str.contains('demo|synthetic', case=False).any():
        raise ValueError('Real pipeline rejects synthetic or unknown-source rows')
    out['season'] = out.season.astype(str).map(lambda s: f'20{s[:2]}-20{s[2:]}' if len(s) == 4 and s.isdigit() else s)
    if not out.season.str.fullmatch(r'20\d{2}-20\d{2}').all():
        raise ValueError('Season must use YYYY-YYYY format')
    if not out.season.map(lambda s: int(s[5:]) == int(s[:4])+1).all():
        raise ValueError('Non-consecutive season years')
    for col in ['minutes', 'mp', 'age'] + COUNTS:
        vals = out[col] if col in out else pd.Series(np.nan, index=out.index)
        text = vals.astype(str).str.replace(',', '', regex=False)
        if col == 'age':
            text = text.str.extract(r'^(\d+)(?:-\d+)?$', expand=False)
        out[col] = pd.to_numeric(text, errors='coerce')
        if col != 'age':
            out.loc[out[col] < 0, col] = np.nan
    out.loc[~out.age.between(14, 50), 'age'] = np.nan
    out['nineties'] = out.minutes / 90
    out['ga'] = out.gls + out.ast  # Missing remains missing.
    for col in COUNTS:
        out[col + '_p90'] = out[col] / out.nineties.where(out.nineties > 0)
    out['pos_main'] = out.pos.astype(str).str.split(',').str[0].str.strip().str.upper()
    out['quality_outlier'] = (out.minutes > 4500) | (out.gls_p90 > 3) | (out.sh_p90 > 15)
    if 'source_player_id' not in out:
        # Local legacy identity only, not a cross-source claim.
        out['source_player_id'] = out.apply(lambda r: 'legacy:' + hashlib.sha256(f'{r.player}|{r.get("nation", "")}'.encode()).hexdigest()[:16], axis=1)
    out['entity_id'] = out.source.astype(str) + ':' + out.source_player_id.astype(str)
    keys = ['entity_id', 'team', 'season', 'league']
    out = out.drop_duplicates()
    if out.duplicated(keys).any():
        raise ValueError('Conflicting duplicate observation keys; review raw data')
    # Prefer the source's all-club total; retain raw club stints in raw snapshots.
    total = out.team.astype(str).str.match(r'^\d+\s+(squads|clubs)$', case=False)
    group = ['entity_id', 'season', 'league']
    total_keys = set(map(tuple, out.loc[total, group].to_numpy()))
    out = out[total | ~out[group].apply(tuple, axis=1).isin(total_keys)].copy()
    out['observation_id'] = out[keys].astype(str).agg('|'.join, axis=1)
    out['player_id'] = out.observation_id.map(lambda s: int(hashlib.sha256(s.encode()).hexdigest()[:13], 16))
    if out.player_id.duplicated().any():
        raise ValueError('Observation ID hash collision')
    out = out[out.minutes >= min_minutes].reset_index(drop=True)
    return out


def save_processed(df):
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PLAYERS_PARQUET, index=False)
    df.to_csv(DATA_PROCESSED / 'players.csv', index=False)
    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql('players', conn, if_exists='replace', index=False)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_players_pos ON players(pos_main)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_players_entity ON players(entity_id)')


def load_players():
    if not PLAYERS_PARQUET.exists():
        raise FileNotFoundError('No real-data output. Run python -m src.pipeline (or explicit legacy exploratory mode).')
    return pd.read_parquet(PLAYERS_PARQUET)


def feature_matrix(df):
    return df[[c for c in FEATURE_COLS if c in df]].copy()
