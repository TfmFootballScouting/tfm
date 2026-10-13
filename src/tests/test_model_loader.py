"""Renamed serving code must keep original models portable and verified."""
import json
import shutil
import pytest
from src.config import ROOT
from src.data_preparation.provenance import sha256
from src.app.model_loader import load_scouting_service


def test_original_frozen_model_binary_and_compatibility_path():
    report=json.loads((ROOT/'reports/five_league_pipeline/experiment_manifest.json').read_text())
    for info in [report['serving_model']]:
        assert sha256(ROOT/info['model_path'])==info['model_sha256']
    service=load_scouting_service()
    assert service.model.__class__.__module__=='src.models.recommender'
    assert len(service.for_season('2023-2024').players)==1810


def test_modified_packaged_source_rejected(tmp_path,monkeypatch):
    import src.app.model_loader as loader
    relative='reports/five_league_pipeline/experiment_manifest.json'
    report=json.loads((ROOT/relative).read_text())
    for source in report['serving_code_sha256']:
        destination=tmp_path/source
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/source,destination)
    manifest=tmp_path/relative;manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(report))
    changed=tmp_path/'src/models/recommender.py'
    changed.write_text(changed.read_text()+'\n# Unit test tampering\n')
    monkeypatch.setattr(loader,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='fingerprint changed'):
        loader.load_scouting_service()


def test_only_one_saved_recommender_and_six_styles():
    assert {p.name for p in (ROOT/'models').glob('*.joblib')} == {'scouting_recommender.joblib'}
    service=load_scouting_service()
    assert set(service.supported_styles)=={'posesion','presion_alta','vertical','contraataque','solidez_defensiva','desborde_banda'}
