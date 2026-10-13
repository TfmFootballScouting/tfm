import pytest

from src.data_preparation.source_rights import SourceUseRestricted, RESTRICTED
from src.models.recommender import PlayerRecommender
from src.scraping.collect import AccessBlocked, Client


def test_restricted_collection_never_requests_network_or_cached_pages(monkeypatch):
    client = Client()
    def unexpected(*args, **kwargs):
        pytest.fail('Restricted collection must stop before a request')
    monkeypatch.setattr(client.session, 'get', unexpected)
    for source in ('transfermarkt', 'fbref'):
        with pytest.raises(AccessBlocked, match='section 11.1'):
            client.get('https://www.transfermarkt.com/laliga2/torschuetzenliste/wettbewerb/ES2', source)


@pytest.mark.parametrize('column,value', [('source', 'transfermarkt_worldfootballr'),
                                         ('valuation_source', 'Transfermarkt'),
                                         ('ml_use_status', RESTRICTED)])
def test_restricted_data_cannot_fit_or_transform_model(players, column, value):
    model = PlayerRecommender().fit(players)
    restricted = players.copy()
    restricted[column] = value
    with pytest.raises(SourceUseRestricted):
        PlayerRecommender().fit(restricted)
    with pytest.raises(SourceUseRestricted):
        model.transform(restricted)


def test_archive_path_must_remain_in_raw_sources(tmp_path, monkeypatch):
    from src.scraping import raw_inputs
    monkeypatch.setattr(raw_inputs, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='inside data/raw/sources'):
        raw_inputs.ensure_archive(dict(path='../outside.rds', sha256='0'*64), download=True)


def test_archive_restore_rejects_unapproved_host_before_network(tmp_path, monkeypatch):
    from src.scraping import raw_inputs
    monkeypatch.setattr(raw_inputs, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='recorded secondary GitHub'):
        raw_inputs.ensure_archive(dict(path='data/raw/sources/a.rds', sha256='0'*64, url='https://example.com/unapproved.rds'), download=True)


def test_existing_archive_mismatch_preserved(tmp_path, monkeypatch):
    from src.scraping import raw_inputs
    monkeypatch.setattr(raw_inputs, 'ROOT', tmp_path)
    path=tmp_path/'data/raw/sources/a.rds';path.parent.mkdir(parents=True);path.write_bytes(b'Unit-test bytes only')
    with pytest.raises(ValueError, match='not overwritten'):
        raw_inputs.ensure_archive(dict(path='data/raw/sources/a.rds', sha256='0'*64), download=True)
    assert path.read_bytes()==b'Unit-test bytes only'
