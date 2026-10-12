"""Integrity regressions; byte fixtures below are not football experiment data."""
import hashlib
import json

import pytest

from src.app import valuation_data


def test_included_real_valuation_inputs():
    values, candidates, history = valuation_data.load_valuation_inputs()
    assert len(values) == 901429
    assert len(candidates) == 5405
    assert len(history) == 15948


def make_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(valuation_data, 'ROOT', tmp_path)
    path = tmp_path / valuation_data.MANIFEST_PATH
    path.parent.mkdir(parents=True)
    item = {'path': 'values.parquet', 'sha256': hashlib.sha256(b'original fixture').hexdigest()}
    path.write_text(json.dumps({'inputs': {key: item for key in ['values', 'identity_candidates', 'player_seasons']}}), encoding='utf-8')
    return tmp_path / item['path']


def test_mismatch_names_file_and_preserves_it(tmp_path, monkeypatch):
    path = make_fixture(tmp_path, monkeypatch)
    path.write_bytes(b'corrupt fixture')
    with pytest.raises(ValueError, match='SHA-256 mismatch: values.parquet'):
        valuation_data.load_valuation_inputs()
    assert path.read_bytes() == b'corrupt fixture'


def test_missing_input_names_file(tmp_path, monkeypatch):
    make_fixture(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError, match='values.parquet'):
        valuation_data.load_valuation_inputs()


def test_signature_detects_input_update(tmp_path, monkeypatch):
    path = make_fixture(tmp_path, monkeypatch)
    first = valuation_data.input_signature()
    path.write_bytes(b'fixture')
    second = valuation_data.input_signature()
    path.write_bytes(b'longer fixture')
    assert first != second != valuation_data.input_signature()
