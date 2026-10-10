"""Immutable raw snapshots and auditable dataset identifiers."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.config import ROOT


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(content: bytes, source: str, url: str, suffix: str = '.html', **metadata) -> dict:
    digest = hashlib.sha256(content).hexdigest()
    path = ROOT / 'data/raw/sources' / source / f'{digest}{suffix}'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)
    record = dict(source=source, url=url, retrieved_at=datetime.now(timezone.utc).isoformat(),
                  sha256=digest, path=path.relative_to(ROOT).as_posix(), **metadata)
    manifest = ROOT / 'data/raw/provenance.jsonl'
    with manifest.open('a', encoding='utf8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    return record
