"""Branch-independent, checksum-verified inputs for reported-value screening."""
import json

import pandas as pd

from src.config import ROOT
from src.data.provenance import sha256

MANIFEST_PATH = 'models/valuation_manifest.json'


def manifest():
    return json.loads((ROOT / MANIFEST_PATH).read_text(encoding='utf-8'))


def input_signature():
    """Refresh Streamlit data/results when the manifest or included files change."""
    paths = [MANIFEST_PATH] + [item['path'] for item in manifest()['inputs'].values()]
    signature = []
    for relative in paths:
        path = ROOT / relative
        if path.exists():
            info = path.stat()
            signature.append((relative, info.st_mtime_ns, info.st_size))
        else:
            signature.append((relative, None, None))
    return tuple(signature)


def load_valuation_inputs():
    entries = manifest()['inputs']
    frames = []
    for key in ['values', 'identity_candidates', 'player_seasons']:
        item = entries[key]
        path = ROOT / item['path']
        if not path.exists():
            raise FileNotFoundError(f"Missing included valuation input: {item['path']}")
        actual = sha256(path)
        if actual != item['sha256']:
            raise ValueError(f"SHA-256 mismatch: {item['path']}. Expected {item['sha256']}; found {actual}.")
        frames.append(pd.read_parquet(path))
    return tuple(frames)
