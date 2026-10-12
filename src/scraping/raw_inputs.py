"""Restore or verify checksum-pinned raw archives; no provider crawling or ML use."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

from src.config import ROOT


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def ensure_archive(record, download=False):
    path = ROOT / record['path']
    if not path.resolve().is_relative_to((ROOT / 'data/raw/sources').resolve()):
        raise ValueError('Raw archive path must remain inside data/raw/sources')
    if path.exists():
        if digest(path) != record['sha256']:
            raise ValueError(f'Checksum mismatch; retained archive was not overwritten: {record["path"]}')
        return 'verified_existing'
    if not download:
        return 'missing'
    url = record['url']
    if not url.startswith('https://github.com/JaseZiv/worldfootballR_data/releases/download/'):
        raise ValueError('Only recorded secondary GitHub release assets can be downloaded')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        request = Request(url, headers={'User-Agent': 'ScoutIQ-raw-archive-restoration/1.0'})
        with urlopen(request, timeout=90) as response, tempfile.NamedTemporaryFile(
                dir=path.parent, prefix='.raw-download-', delete=False) as output:
            temporary = Path(output.name)
            size = 0
            for block in iter(lambda: response.read(1024 * 1024), b''):
                size += len(block)
                if size > record['bytes']:
                    raise ValueError('Downloaded archive exceeds its recorded size')
                output.write(block)
        if size != record['bytes'] or digest(temporary) != record['sha256']:
            raise ValueError('Downloaded archive differs from the pinned snapshot; no replacement saved')
        temporary.replace(path)
        return 'downloaded_and_verified'
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--verify', action='store_true')
    actions.add_argument('--download', action='store_true')
    parser.add_argument('--include-optional', action='store_true', help='Also restore four-league shot archives')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'data/raw/sources_manifest.json').read_text())
    missing = False
    for record in manifest['archives']:
        if record['role'] != 'primary' and not args.include_optional:
            continue
        status = ensure_archive(record, download=args.download)
        print(json.dumps({'path': record['path'], 'status': status}))
        missing |= status == 'missing'
    raise SystemExit(1 if missing else 0)


if __name__ == '__main__':
    main()
