"""Portable source verification; dataset/model checksums remain byte-exact."""
import hashlib
from pathlib import Path


def source_sha256(path):
    """Normalize CRLF only in Python source, preserving all other content."""
    path = Path(path)
    if path.suffix != '.py':
        raise ValueError('Source normalization is limited to Python files')
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
