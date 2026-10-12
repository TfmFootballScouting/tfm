"""Real uploaded-file admission checks, not valuation-model experiments."""
import hashlib
from zipfile import ZipFile

import pandas as pd
import pytest

from src.data.kaggle_values import read_archive, audit_tables
from src.data.source_rights import require_model_data_use, SourceUseRestricted
from scripts.kaggle_value_audit import ARCHIVE_SHA256, RAW


@pytest.fixture(scope='module')
def uploaded_tables():
    path = RAW / (ARCHIVE_SHA256 + '.zip')
    assert path.exists(), 'Preserve/inspect the uploaded archive with scripts.kaggle_value_audit first'
    profiles, history, dictionary, raw = read_archive(path, ARCHIVE_SHA256)
    return profiles, history


def test_real_uploaded_dates_are_preserved_and_quarantined(uploaded_tables):
    profiles, history = uploaded_tables
    p, h, consistency, diagnostics = audit_tables(profiles, history, '2026-10-11T13:37:21Z')
    assert len(p) == 508 and len(h) == 9764
    assert h.valuation_date_raw.equals(history.valuation_date)
    assert h.market_value_eur.equals(history.value_eur)
    assert h.valuation_date.isna().all(), 'Do not silently correct the systematic date discrepancy'
    assert h.source_publication_known_at.isna().all()
    assert not h.historical_budget_eligible.any()
    assert consistency.first_summary_to_history_days.eq(1).all()
    assert consistency.last_summary_to_history_days.eq(1).all()
    assert diagnostics['reported_year_month_disagreement_rows'] == 234
    assert diagnostics['reported_year_disagreement_rows'] == 24
    assert diagnostics['players_peak_amount_date_matches_one_day_earlier_hypothesis'] == 508


def test_corrupted_profiles_cannot_supply_club_or_position(uploaded_tables):
    p, h, consistency, diagnostics = audit_tables(*uploaded_tables, '2026-10-11T13:37:21Z')
    assert p.position_reported_invalid.all()
    assert p.position_clean.isna().all() and p.current_club_clean.isna().all()
    assert diagnostics['current_club_equals_nationality_rows'] == 501
    assert set(p.league_name) == {'La Liga', 'Premier League', 'Bundesliga', 'Serie A', 'Ligue 1'}
    assert p.source_player_id.nunique() == 508


@pytest.mark.parametrize('damage', ['duplicate', 'orphan'])
def test_history_cardinality_failures_are_not_silently_joined(uploaded_tables, damage):
    p, h = uploaded_tables
    broken = h.copy()
    if damage == 'duplicate':
        broken = pd.concat([h, h.iloc[[0]]], ignore_index=True)
        message = 'Duplicate history observation'
    else:
        broken.loc[0, 'player_id'] = 'unknown-id'
        message = 'orphan'
    with pytest.raises(ValueError, match=message):
        audit_tables(p, broken, '2026-10-11T13:37:21Z')


def test_uploaded_provider_flags_reject_model_use(uploaded_tables):
    p, h, consistency, diagnostics = audit_tables(*uploaded_tables, '2026-10-11T13:37:21Z')
    for frame in (p, h):
        with pytest.raises(ValueError, match='Unreviewed'):
            require_model_data_use(frame)
        # Removing an identity column cannot conceal the original provider.
        with pytest.raises(SourceUseRestricted, match='Transfermarkt'):
            require_model_data_use(frame.drop(columns='identity_match_status'))


def test_archive_integrity_and_unexpected_members_fail(tmp_path):
    actual = RAW / (ARCHIVE_SHA256 + '.zip')
    with pytest.raises(ValueError, match='checksum'):
        read_archive(actual, '0' * 64)
    hostile = tmp_path / 'hostile.zip'
    with ZipFile(hostile, 'w') as archive:
        archive.writestr('../instructions.py', 'raise RuntimeError("must never execute")')
    with pytest.raises(ValueError, match='ZIP members'):
        read_archive(hostile, hashlib.sha256(hostile.read_bytes()).hexdigest())
