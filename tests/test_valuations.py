"""Artificial unit fixtures only; audit outputs exclusively use retained real data."""
import numpy as np
import pandas as pd
import pytest

from src.data.source_rights import SourceUseRestricted
from src.data.valuations import (audit_retained_values, consolidate_header_evidence,
                                header_valuation_evidence, select_recorded_values)

HEADER = '''<div class="data-header"><h1>#7 Example Player</h1><span class="data-header__club">Example Club</span>
<a class="data-header__market-value-wrapper" href="/example/marktwertverlauf/spieler/123">
<span>€</span>2.00<span>m</span><p class="data-header__last-update">Last update: 22/07/2026</p></a></div>'''
PROVENANCE = dict(source_player_id='123', retrieved_at='2026-10-10T15:00:00+00:00',
    category='profiles', url='https://example.invalid/player/123', sha256='unit-fixture', path='unit-fixture.html')


def test_explicit_header_date_does_not_use_request_season_or_other_dates():
    data = header_valuation_evidence(HEADER, dict(PROVENANCE, season='2020-2021'))
    assert data['market_value_eur'] == 2_000_000
    assert data['valuation_date'] == pd.Timestamp('2026-07-22', tz='UTC')
    assert data['valuation_known_at'] == pd.Timestamp(PROVENANCE['retrieved_at'])
    assert data['date_of_birth'] is None and not data['use_authorized']
    with pytest.raises(ValueError, match='date missing'):
        header_valuation_evidence(HEADER.replace('data-header__last-update', 'contract-expiry'), PROVENANCE)
    with pytest.raises(ValueError, match='player ID differs'):
        header_valuation_evidence(HEADER, dict(PROVENANCE, source_player_id='999'))
    with pytest.raises(ValueError, match='follows'):
        header_valuation_evidence(HEADER, dict(PROVENANCE, retrieved_at='2025-01-01'))


def test_repeated_headers_are_corroboration_not_independent_valuations():
    data = header_valuation_evidence(HEADER, PROVENANCE)
    later = dict(data, snapshot_sha256='unit-fixture-2', valuation_known_at=pd.Timestamp('2026-10-11', tz='UTC'))
    both = pd.DataFrame([later, data])
    values = consolidate_header_evidence(both)
    assert len(values) == 1 and values.corroborating_snapshots.iloc[0] == 2
    assert values.valuation_known_at.iloc[0] == data['valuation_known_at']
    both.loc[0, 'market_value_eur'] = 3_000_000
    with pytest.raises(ValueError, match='disagree'):
        consolidate_header_evidence(both)


def test_current_header_never_backfills_archived_player_season():
    archive = pd.DataFrame([dict(source='transfermarkt',source_player_id='123',player='Example',team='Club',
        season='2020-2021', record_id='old', snapshot_sha256='unit', market_value_eur=2_000_000,
        currency='EUR', valuation_date=pd.NaT, valuation_known_at=pd.NaT, ml_use_status='restricted_pending_explicit_license')])
    current = archive.assign(season=None, league='La Liga', record_id='current')
    dated = consolidate_header_evidence(pd.DataFrame([header_valuation_evidence(HEADER, PROVENANCE)]))
    crosswalk = pd.DataFrame([dict(right_source='transfermarkt',right_id='123',season_cutoff='2020-2021',
        canonical_player_id='fbref:a',exact_name=True,birth_year_agreement=True,upstream_id_mapping=True,
        proposal_status='high_support_proposal',unstable_across_cutoffs=False)])
    audit = audit_retained_values(archive, current, dated, crosswalk)
    assert audit.loc[audit.dataset.eq('season_labelled_archive'), 'valuation_date'].isna().all()
    assert audit.loc[audit.dataset.eq('current_market_sample'), 'valuation_date'].notna().all()
    assert not audit.eligible_for_historical_budget.any() and not audit.identity_verified.any()


def recorded_values():
    return pd.DataFrame([dict(source='open_export',source_player_id='a',canonical_player_id='fbref:a',
        market_value_eur=1_000_000,currency='EUR',valuation_date='2022-06-01',
        valuation_known_at='2022-06-02',identity_match_status='reviewed',identity_reviewed_at='2022-06-03',
        use_authorized=True,use_authorization_evidence='Artificial unit authorization fixture',record_id='a')])


def test_selector_excludes_unknown_future_and_unreviewed_records():
    data = recorded_values()
    assert len(select_recorded_values(data, '2022-07-01')) == 1
    for field, value in [('market_value_eur',np.nan),('market_value_eur',np.inf),('market_value_eur',-1),
        ('valuation_date',None),('valuation_known_at','2023-01-01'),('identity_reviewed_at','2023-01-01'),
        ('identity_match_status','provisional_not_reviewed'),('use_authorized','True'),
        ('use_authorization_evidence',''),('currency','USD')]:
        changed = data.copy(); changed[field] = value
        assert select_recorded_values(changed, '2022-07-01').empty, field
    assert select_recorded_values(data.assign(market_value_eur=0), '2022-07-01').market_value_eur.iloc[0] == 0
    with pytest.raises(ValueError, match='missing fields'):
        select_recorded_values(data.drop(columns='valuation_known_at'), '2022-07-01')


def test_selector_keeps_latest_eligible_value_without_future_backfill():
    original = recorded_values()
    later = original.assign(record_id='b',market_value_eur=2_000_000,
        valuation_date='2023-06-01',valuation_known_at='2023-06-02')
    rows = pd.concat([later,original],ignore_index=True)
    assert select_recorded_values(rows,'2022-07-01').market_value_eur.tolist() == [1_000_000]
    assert select_recorded_values(rows,'2023-07-01').market_value_eur.tolist() == [2_000_000]
    pd.testing.assert_frame_equal(select_recorded_values(rows,'2023-07-01'),select_recorded_values(rows.iloc[::-1],'2023-07-01'))


def test_selector_refuses_conflicting_values_identity_collisions_and_restricted_sources():
    original = recorded_values()
    with pytest.raises(ValueError, match='Conflicting recorded'):
        select_recorded_values(pd.concat([original,original.assign(record_id='b',market_value_eur=2_000_000)]),'2023-01-01')
    with pytest.raises(ValueError, match='one-to-one'):
        select_recorded_values(pd.concat([original,original.assign(record_id='b',source_player_id='b')]),'2023-01-01')
    with pytest.raises(SourceUseRestricted):
        select_recorded_values(original.assign(source='transfermarkt'), '2023-01-01')
