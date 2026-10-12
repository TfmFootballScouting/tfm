import pytest

from src.data.source_rights import SourceUseRestricted, RESTRICTED
from src.models.recommend import PlayerRecommender
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


def test_archive_acquisition_respects_rights_before_network(tmp_path, monkeypatch):
    from scripts import worldfootballr_archive as archive
    monkeypatch.setattr(archive, 'ROOT', tmp_path)
    with pytest.raises(SourceUseRestricted, match='archive acquisition'):
        archive.ensure_snapshot(dict(path='missing.rds', category='valuations', original_source='transfermarkt'), download=True)


def test_scorer_evidence_rejects_current_or_wrong_season():
    from scripts.uploaded_scraper_trial import scorer_evidence
    with pytest.raises(ValueError, match='not confirmed'):
        scorer_evidence('<html><title>LaLiga2 25/26</title></html>', 2024)


def test_new_source_probe_reports_proxy_failure_without_aborting(monkeypatch):
    import requests
    from scripts.uploaded_scraper_trial import NEW_HOSTS, probe_new_source
    def denied(*args, **kwargs):
        raise requests.exceptions.ProxyError('Tunnel connection failed: 403 Forbidden')
    monkeypatch.setattr(requests.Session, 'get', denied)
    outcomes = [probe_new_source(source) for source in NEW_HOSTS]
    assert len(outcomes) == 3
    assert all(row['status'] == 'environment_network_blocked' for row in outcomes)
