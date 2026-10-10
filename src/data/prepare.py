"""Source-specific normalization. Legacy input is opt-in and never final evidence."""
import json
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.preprocessing.clean import clean_players, save_processed


def prepare(legacy=False):
    if legacy:
        path = ROOT / 'data/raw/players_raw.csv'
        raw = pd.read_csv(path)
        audit = raw.groupby(['source', 'league', 'season'], dropna=False).size().rename('rows').reset_index()
        audit.to_csv(ROOT / 'reports/legacy_inventory.csv', index=False)
        raw = raw[raw.source == 'fbref_cache'].copy()
        # Original loader assigned these tables by row index, so discard all suspect fields.
        raw = raw.drop(columns=['sh','sot','crs','int','tklw','fls','fld'], errors='ignore')
        raw['provenance_status'] = 'legacy_unverified'
        raw['snapshot_sha256'] = sha256(path)
        raw['source_snapshot'] = path.relative_to(ROOT).as_posix()
        kind = 'real_legacy_unverified'
    else:
        parts = []
        # Understat is kept separate; never outer-join unidentified FBref or TM players.
        for path in sorted((ROOT / 'data/external/understat').glob('*_players_xg_xa.csv')):
            f = pd.read_csv(path, dtype={'id': str})
            f = f.rename(columns={'id':'source_player_id', 'player_name':'player', 'team_title':'team',
                                  'position':'pos', 'time':'minutes', 'goals':'gls', 'assists':'ast',
                                  'shots':'sh', 'xG':'xg', 'xA':'xa', 'games':'mp'})
            f['pos'] = f.pos.astype(str).map(lambda s: {'F':'FW', 'S':'FW', 'M':'MF', 'D':'DF', 'GK':'GK'}.get(s.split()[0], s))
            f['provenance_status'] = 'direct_snapshot'
            f['source_snapshot'] = path.relative_to(ROOT).as_posix()
            parts.append(f)
        # FBref is a separate observation source; never pool source estimates in one model.
        if not parts:
            from src.data.fbref import merge_tables
            folder = ROOT / 'data/external/fbref'
            for path in sorted(folder.glob('*_standard.csv')):
                standard = pd.read_csv(path, dtype={'source_player_id': str})
                prefix = path.name.removesuffix('_standard.csv')
                aux = [pd.read_csv(p, dtype={'source_player_id': str}) for p in folder.glob(prefix + '_*.csv') if p != path]
                frame = merge_tables(standard, aux)
                frame['provenance_status'] = 'direct_snapshot'
                frame['source_snapshot'] = path.relative_to(ROOT).as_posix()
                parts.append(frame)
        if not parts:
            raise RuntimeError('No collected real player statistics. See reports/source_coverage.csv. No synthetic fallback.')
        raw = pd.concat(parts, ignore_index=True)
        kind = 'real_direct_snapshot'
    clean = clean_players(raw)
    if clean.empty:
        raise ValueError('No players meet the minutes threshold')
    save_processed(clean)
    (ROOT / 'reports/dataset.json').write_text(json.dumps(dict(dataset_kind=kind,
        rows=len(clean), sources=sorted(clean.source.unique()),
        snapshots=sorted(clean.snapshot_sha256.unique()),
        dataset_sha256=sha256(ROOT / 'data/processed/real/players.parquet'),
        limitations=['Legacy retrieval date and original HTML absent; ancillary stats discarded'] if legacy else []), indent=2))
    return clean
