"""Audit uploaded valuation files; never infer historical budget eligibility."""
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile
import hashlib

import numpy as np
import pandas as pd

from src.data.source_rights import RESTRICTED

PREFIX = 'Football_Player_Market_Value_Trajectories/'
MEMBERS = {PREFIX + name for name in (
    'data_dictionary.csv', 'transfermarkt_player_values.csv',
    'transfermarkt_player_values.parquet', 'transfermarkt_value_history.csv')}


def read_archive(path, expected_sha256):
    """Read only expected data members, with bounded sizes and no execution."""
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError('Uploaded archive checksum mismatch')
    with ZipFile(BytesIO(payload)) as archive:
        infos = archive.infolist()
        if len(infos) != len(MEMBERS) or {i.filename for i in infos} != MEMBERS:
            raise ValueError('Unexpected or duplicate ZIP members')
        for info in infos:
            member = PurePosixPath(info.filename)
            if member.is_absolute() or '..' in member.parts or info.file_size > 20_000_000:
                raise ValueError('Unsafe or oversized ZIP member')
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('ZIP symlinks are not accepted')
        raw = {name: archive.read(name) for name in sorted(MEMBERS)}
    csv = pd.read_csv(BytesIO(raw[PREFIX + 'transfermarkt_player_values.csv']),
                      dtype={'player_id': str})
    parquet = pd.read_parquet(BytesIO(raw[PREFIX + 'transfermarkt_player_values.parquet']))
    parquet['player_id'] = parquet.player_id.astype(str)
    # Parquet stores seven absent nationalities as empty strings; CSV represents
    # those empty fields as missing. Preserve both raw files, normalize for parity.
    parquet = parquet.replace('', np.nan)
    pd.testing.assert_frame_equal(csv, parquet, check_dtype=False, check_exact=False,
                                  rtol=1e-12, atol=1e-12)
    history = pd.read_csv(BytesIO(raw[PREFIX + 'transfermarkt_value_history.csv']),
                          dtype={'player_id': str})
    dictionary = pd.read_csv(BytesIO(raw[PREFIX + 'data_dictionary.csv']))
    return csv, history, dictionary, raw


def audit_tables(profiles, history, first_observed_at):
    """Preserve contradictory dates/fields, quarantine them, expose diagnostics."""
    if profiles.player_id.isna().any() or profiles.player_id.duplicated().any():
        raise ValueError('Profile source IDs must be present and unique')
    if history.player_id.isna().any() or not set(history.player_id) <= set(profiles.player_id):
        raise ValueError('History contains missing or orphan source IDs')
    if history.duplicated(['player_id', 'valuation_date']).any():
        raise ValueError('Duplicate history observation key; review before consolidation')
    stamp = pd.Timestamp(first_observed_at)
    if stamp.tzinfo is None:
        raise ValueError('First observed timestamp requires a timezone')
    p, h = profiles.copy(), history.copy()
    h['valuation_date_reported'] = pd.to_datetime(h.valuation_date, format='%d/%m/%Y', errors='coerce')
    if h.valuation_date_reported.isna().any():
        raise ValueError('Invalid reported history dates')
    # This is an audit hypothesis, not a correction or eligible effective date.
    h['valuation_date_one_day_earlier_hypothesis'] = h.valuation_date_reported - pd.Timedelta(days=1)
    h['reported_year_month_agree'] = (h.valuation_date_reported.dt.year.eq(h.year) &
                                     h.valuation_date_reported.dt.month.eq(h.month))
    h['earlier_hypothesis_year_month_agree'] = (
        h.valuation_date_one_day_earlier_hypothesis.dt.year.eq(h.year) &
        h.valuation_date_one_day_earlier_hypothesis.dt.month.eq(h.month))
    grouped = h.groupby('player_id').agg(
        history_points=('value_eur', 'size'), first_history_date=('valuation_date_reported', 'min'),
        last_history_date=('valuation_date_reported', 'max'), history_peak_eur=('value_eur', 'max'))
    checks = p.set_index('player_id').join(grouped)
    for name in ('first', 'last'):
        checks[name + '_summary_to_history_days'] = (
            checks[name + '_history_date'] - pd.to_datetime(checks[name + '_date'], format='%Y-%m-%d')
        ).dt.days
    peak_pairs = h.merge(p[['player_id', 'peak_date', 'peak_value_eur']], on='player_id', validate='many_to_one')
    matched_peaks = peak_pairs[
        peak_pairs.value_eur.eq(peak_pairs.peak_value_eur) &
        peak_pairs.valuation_date_one_day_earlier_hypothesis.eq(pd.to_datetime(peak_pairs.peak_date))
    ].player_id.nunique()
    p['position_reported_invalid'] = p.position.astype(str).str.startswith('€')
    p['current_club_equals_nationality'] = p.current_club.eq(p.nationality)
    # All current-club entries are quarantined because this export field has a
    # systemic extraction failure; do not promote the seven missing-nationality rows.
    p['position_clean'] = pd.NA
    p['current_club_clean'] = pd.NA
    p['profile_quality_status'] = 'position_and_current_club_quarantined'
    h = h.rename(columns={'valuation_date': 'valuation_date_raw', 'player_id': 'source_player_id'})
    h['market_value_eur'] = pd.to_numeric(h.value_eur, errors='coerce')
    h['amount_valid'] = h.market_value_eur.notna() & np.isfinite(h.market_value_eur) & h.market_value_eur.ge(0)
    # No automatic correction, source-publication assertion, or historical budget attachment.
    h['valuation_date'] = pd.NaT
    h['valuation_known_at'] = stamp.tz_convert('UTC')
    h['date_quality_status'] = 'unresolved_summary_history_one_day_disagreement'
    h['source_publication_known_at'] = pd.NaT
    h['currency'] = 'EUR'
    p = p.rename(columns={'player_id': 'source_player_id'})
    for frame in (p, h):
        frame['source'] = 'kaggle_user_upload_transfermarkt'
        frame['original_source'] = 'Transfermarkt.com'
        frame['first_observed_at_utc'] = stamp.tz_convert('UTC')
        frame['provenance_status'] = 'uploader_declared_provider_not_independently_verified'
        frame['ml_use_status'] = RESTRICTED
        frame['identity_match_status'] = 'unmatched'
        frame['source_use_authorized'] = False
        frame['historical_budget_eligible'] = False
        frame['model_use_eligible'] = False
    diagnostics = {
        'profile_rows': len(p), 'history_rows': len(h), 'unique_players': p.source_player_id.nunique(),
        'league_labels': profiles.league_name.value_counts().to_dict(),
        'position_price_rows': int(p.position_reported_invalid.sum()),
        'position_group_counts': profiles.position_group.value_counts().to_dict(),
        'current_club_equals_nationality_rows': int(p.current_club_equals_nationality.sum()),
        'age_missing_rows': int(p.age.isna().sum()),
        'current_vs_last_amount_mismatch_players': int(p.current_value_eur.ne(p.last_value_eur).sum()),
        'is_at_peak_flag_vs_current_peak_amount_equality_disagreements': int(
            p.is_at_peak.ne(p.current_value_eur.eq(p.peak_value_eur).astype(int)).sum()),
        'history_date_range': [h.valuation_date_reported.min().date().isoformat(),
                               h.valuation_date_reported.max().date().isoformat()],
        'reported_year_month_disagreement_rows': int((~h.reported_year_month_agree).sum()),
        'reported_year_disagreement_rows': int(h.valuation_date_reported.dt.year.ne(h.year).sum()),
        'one_day_earlier_hypothesis_year_month_disagreements': int((~h.earlier_hypothesis_year_month_agree).sum()),
        'first_summary_history_offset_days': checks.first_summary_to_history_days.value_counts().to_dict(),
        'last_summary_history_offset_days': checks.last_summary_to_history_days.value_counts().to_dict(),
        'players_peak_amount_date_matches_one_day_earlier_hypothesis': int(matched_peaks),
        'history_point_count_mismatch_players': int(checks.history_points.ne(checks.num_valuation_points).sum()),
        'peak_amount_mismatch_players': int(checks.history_peak_eur.ne(checks.peak_value_eur).sum()),
        'invalid_amount_rows': int((~h.amount_valid).sum()),
        'reported_zero_value_rows': int(h.market_value_eur.eq(0).sum()),
        'archive_declared_build_dates': profiles.dataset_built_at.unique().tolist(),
        'historical_budget_eligible_rows': 0,
    }
    return p, h, checks.reset_index(), diagnostics
