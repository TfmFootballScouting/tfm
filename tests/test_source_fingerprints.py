import hashlib
import pytest
from src.app.fingerprints import source_sha256
from src.config import ROOT


def test_crlf_normalization_and_real_edit_detection(tmp_path):
    original = b'def f():\n    return 1\n'
    path = tmp_path / 'source.py'
    path.write_bytes(original.replace(b'\n', b'\r\n'))
    assert source_sha256(path) == hashlib.sha256(original).hexdigest()
    path.write_bytes(original.replace(b'return 1', b'return 2'))
    assert source_sha256(path) != hashlib.sha256(original).hexdigest()
    with pytest.raises(ValueError): source_sha256(tmp_path/'model.joblib')


def test_both_models_load_with_crlf_sources_and_reject_real_changes(monkeypatch, tmp_path):
    import src.app.collected as serving
    originals = {}
    for name in ['src/features/styles.py', 'src/config.py', 'src/models/collected.py',
                 'src/models/recommend.py', 'src/data/source_rights.py']:
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (ROOT/name).read_bytes()
        path.write_bytes(content.replace(b'\n', b'\r\n'))
        originals[ROOT/name] = path
    monkeypatch.setattr(serving, 'source_sha256', lambda path: source_sha256(originals[path]))
    for name in ['core', 'offensive']:
        service = serving.load_collected_service(name)
        assert len(service.for_season(service.available_seasons[0]).players) > 300
    changed = originals[ROOT/'src/features/styles.py']
    changed.write_bytes(changed.read_bytes()+b'\r\n# actual source edit\r\n')
    with pytest.raises(ValueError, match='Style definition fingerprint changed'):
        serving.load_collected_service('core')
