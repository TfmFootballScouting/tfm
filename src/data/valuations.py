"""Offline valuation evidence and conservative, explicit as-of selection.

Recorded market values are source assessments, never agreed transfer fees.
No dates, prices, identity approvals or permissions are inferred from seasons.
"""
import json
import re

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

from src.data.matching import normalize_name
from src.data.source_rights import RESTRICTED, require_model_data_use
from src.scraping.transfermarkt import money_eur, profile


def header_valuation_evidence(html, provenance):
    """Parse ONLY an explicit value/last-update pair from a retained header."""
    soup = BeautifulSoup(html, 'lxml')
    headers = soup.select('.data-header__market-value-wrapper')
    if len(headers) != 1:
        raise ValueError('Expected exactly one current market-value header')
    header = headers[0]
    dates = header.select('.data-header__last-update')
    if len(dates) != 1:
        raise ValueError('Explicit last-update date missing or ambiguous')
    date_text = dates[0].get_text(' ', strip=True)
    matched = re.fullmatch(r'Last update:\s*(\d{2}/\d{2}/\d{4})', date_text)
    if matched is None:
        raise ValueError('Unsupported explicit valuation date format')
    valuation_date = pd.to_datetime(matched[1], format='%d/%m/%Y', utc=True, errors='raise')
    known_at = pd.to_datetime(provenance['retrieved_at'], utc=True, errors='raise')
    if pd.isna(known_at) or valuation_date > known_at:
        raise ValueError('Valuation update date follows or lacks snapshot observation time')
    link = re.search(r'/spieler/(\d+)(?:/|$)', header.get('href', ''))
    if link is None or link[1] != str(provenance['source_player_id']):
        raise ValueError('Header player ID differs from raw provenance')
    # The date is not part of the monetary value. Never parse a page-wide number.
    dates[0].extract()
    amount = money_eur(header.get_text(' ', strip=True))
    if amount is None:
        raise ValueError('Unsupported explicit market-value amount')
    title = soup.select_one('.data-header h1')
    club = soup.select_one('.data-header__club')
    if title is None:
        raise ValueError('Current player name missing')
    name = re.sub(r'^#\d+\s*', '', title.get_text(' ', strip=True)).strip()
    try:
        details = profile(html)
    except ValueError:
        # History pages may have a dated value header without a profile table.
        # Missing profile attributes remain missing; the price/date pair is explicit.
        details = {}
    return dict(source_player_id=link[1], player=name,
        market_value_eur=amount, currency='EUR', valuation_date=valuation_date,
        valuation_known_at=known_at, date_of_birth=details.get('date_of_birth'),
        current_profile_club=club.get_text(' ', strip=True) if club else None,
        source='transfermarkt', ml_use_status=RESTRICTED,
        evidence_kind='explicit_current_header_value_and_last_update',
        temporal_scope='current_value_observed_in_2026_not_historical_series',
        known_at_basis='conservative_local_snapshot_observation_not_original_publication',
        source_category=provenance['category'], source_url=provenance['url'],
        snapshot_sha256=provenance['sha256'], snapshot_path=provenance['path'],
        date_selector='.data-header__market-value-wrapper .data-header__last-update',
        identity_match_status='not_reviewed', use_authorized=False)


def consolidate_header_evidence(evidence):
    """Repeated page headers corroborate two observations, not six price events."""
    if evidence.empty:
        return evidence.copy()
    rows = []
    for identity, group in evidence.groupby('source_player_id', sort=True):
        if group.market_value_eur.nunique() != 1 or group.valuation_date.nunique() != 1:
            raise ValueError('Retained current page headers disagree; do not choose an arbitrary value')
        first = group.sort_values(['valuation_known_at', 'snapshot_sha256']).iloc[0].to_dict()
        first['corroborating_snapshots'] = len(group)
        first['evidence_snapshot_hashes'] = json.dumps(sorted(group.snapshot_sha256.unique()))
        rows.append(first)
    return pd.DataFrame(rows).reset_index(drop=True)


def current_profile_identity_candidates(values, fbref):
    """Current audit proposals; never approve or retrospectively enrich seasons."""
    rows = []
    for value in values.itertuples():
        birth = pd.to_datetime(value.date_of_birth, errors='coerce')
        names = fbref[fbref.player.map(normalize_name).eq(normalize_name(value.player))]
        year = int(birth.year) if pd.notna(birth) else None
        candidates = names[names.birth_year.eq(year)] if year is not None else names.iloc[:0]
        for identity, person in candidates.groupby('entity_id', sort=True):
            years = fbref[fbref.entity_id.eq(identity)].birth_year.dropna().unique()
            consistent = len(years) == 1 and years[0] == year
            rows.append(dict(source_player_id=value.source_player_id, canonical_player_id=identity,
                fbref_player=person.player.iloc[-1], source_player=value.player,
                source_date_of_birth=value.date_of_birth, fbref_birth_year=year,
                exact_normalized_name=True, birth_year_agreement=consistent,
                candidate_persons=int(candidates.entity_id.nunique()),
                fbref_observed_seasons=json.dumps(sorted(person.season.unique())),
                current_profile_club=value.current_profile_club,
                prior_observed_clubs=json.dumps(sorted(person.team.unique())),
                proposal_status='current_name_birth_year_supported' if consistent and candidates.entity_id.nunique() == 1 else 'review_required',
                identity_match_status='provisional_not_reviewed',
                evidence_known_at=value.valuation_known_at,
                temporal_scope='current_profile_evidence_not_historical_asof_proof',
                eligible_for_attachment=False))
    columns = ['source_player_id', 'canonical_player_id', 'fbref_player', 'source_player',
        'source_date_of_birth', 'fbref_birth_year', 'exact_normalized_name', 'birth_year_agreement',
        'candidate_persons', 'fbref_observed_seasons', 'current_profile_club', 'prior_observed_clubs',
        'proposal_status', 'identity_match_status', 'evidence_known_at', 'temporal_scope', 'eligible_for_attachment']
    return pd.DataFrame(rows, columns=columns)


def audit_retained_values(archive, current, dated, crosswalk):
    """Preserve undated archives and extract separate current-date evidence."""
    out = pd.concat([archive.assign(dataset='season_labelled_archive'),
                     current.assign(dataset='current_market_sample')], ignore_index=True, sort=False)
    out['source_player_id'] = out.source_player_id.astype('string')
    out['requested_league_context'] = out['league'].where(out.dataset.eq('current_market_sample'), 'La Liga')
    out['valuation_date'] = pd.to_datetime(out.valuation_date, utc=True, errors='coerce')
    out['valuation_known_at'] = pd.to_datetime(out.valuation_known_at, utc=True, errors='coerce')
    out['date_evidence_kind'] = 'missing_effective_and_known_at_dates'
    out['header_snapshot_hashes'] = None
    # Only the CURRENT sample gets matching current header evidence. Archived
    # player-season values can never inherit a later header date or price.
    for value in dated.itertuples():
        mask = out.dataset.eq('current_market_sample') & out.source_player_id.eq(value.source_player_id)
        mask &= out.market_value_eur.eq(value.market_value_eur)
        out.loc[mask, 'valuation_date'] = value.valuation_date
        out.loc[mask, 'valuation_known_at'] = value.valuation_known_at
        out.loc[mask, 'date_evidence_kind'] = value.evidence_kind
        out.loc[mask, 'header_snapshot_hashes'] = value.evidence_snapshot_hashes
    links = crosswalk[crosswalk.right_source.eq('transfermarkt') & ~crosswalk.unstable_across_cutoffs]
    keys = ['right_id', 'season_cutoff']
    if links.duplicated(keys).any():
        raise ValueError('Ambiguous season-specific crosswalk')
    joined = out.merge(links[['right_id', 'season_cutoff', 'canonical_player_id', 'exact_name',
        'birth_year_agreement', 'upstream_id_mapping', 'proposal_status']],
        left_on=['source_player_id', 'season'], right_on=keys, how='left', validate='many_to_one')
    joined['identity_match_status'] = np.where(joined.canonical_player_id.notna(), 'provisional_not_reviewed', 'unmatched')
    amount = pd.to_numeric(joined.market_value_eur, errors='coerce')
    joined['amount_present'] = amount.notna() & np.isfinite(amount) & amount.ge(0)
    joined['explicit_dates_present'] = joined.valuation_date.notna() & joined.valuation_known_at.notna()
    joined['use_authorized'] = False
    joined['use_authorization_evidence'] = None
    joined['identity_reviewed_at'] = pd.NaT
    joined['identity_verified'] = False
    joined['eligible_for_historical_budget'] = False
    joined['value_kind'] = 'source_reported_market_assessment_not_transfer_fee'
    joined['valuation_blockers'] = [json.dumps(
        (['amount_missing_or_invalid'] if not r.amount_present else [])+
        (['effective_or_known_at_date_missing'] if not r.explicit_dates_present else [])+
        (['identity_not_reviewed'] if pd.notna(r.canonical_player_id) else ['identity_unmatched'])+
        ['source_use_restricted']) for r in joined.itertuples()]
    wanted = ['dataset', 'source', 'source_player_id', 'player', 'team', 'season', 'requested_league_context',
        'record_id', 'snapshot_sha256', 'market_value_eur', 'currency', 'valuation_date', 'valuation_known_at',
        'date_evidence_kind', 'header_snapshot_hashes', 'canonical_player_id', 'exact_name',
        'birth_year_agreement', 'upstream_id_mapping', 'proposal_status', 'identity_match_status',
        'amount_present', 'explicit_dates_present', 'use_authorized', 'use_authorization_evidence',
        'identity_reviewed_at', 'identity_verified', 'ml_use_status',
        'eligible_for_historical_budget', 'value_kind', 'valuation_blockers']
    return joined[wanted]


def select_recorded_values(records, cutoff):
    """Future import adapter: explicit reviewed identities, dates and permission.

    It returns one latest eligible observation per canonical person. Conflicting
    amounts on the same effective date fail rather than being resolved by row
    order. The existing source-use restriction remains enforced separately.
    """
    required = ['source_player_id', 'canonical_player_id', 'market_value_eur', 'currency',
        'valuation_date', 'valuation_known_at', 'identity_match_status', 'identity_reviewed_at',
        'use_authorized', 'use_authorization_evidence', 'source', 'record_id']
    if missing := set(required)-set(records):
        raise ValueError('Valuation import missing fields: '+', '.join(sorted(missing)))
    t = pd.to_datetime(cutoff, utc=True, errors='raise')
    if pd.isna(t):
        raise ValueError('A decision cutoff is required')
    frame = records.copy()
    for field in ['valuation_date', 'valuation_known_at', 'identity_reviewed_at']:
        frame[field] = pd.to_datetime(frame[field], utc=True, errors='coerce')
    amount = pd.to_numeric(frame.market_value_eur, errors='coerce')
    permitted = frame.use_authorized.map(lambda x: isinstance(x, (bool, np.bool_)) and bool(x))
    evidence = frame.use_authorization_evidence.fillna('').astype(str).str.strip().ne('')
    nonblank = pd.Series(True, index=frame.index)
    for field in ['source_player_id', 'canonical_player_id', 'source', 'record_id']:
        nonblank &= frame[field].notna() & frame[field].astype(str).str.strip().ne('')
    dates = frame.valuation_date.le(t) & frame.valuation_known_at.le(t) & frame.identity_reviewed_at.le(t)
    dates &= frame.valuation_date.le(frame.valuation_known_at)
    mask = permitted & evidence & nonblank & dates & frame.identity_match_status.eq('reviewed')
    mask &= amount.notna() & np.isfinite(amount) & amount.ge(0) & frame.currency.eq('EUR')
    frame = frame[mask].copy()
    frame['market_value_eur'] = amount.loc[frame.index]
    if frame.empty:
        return frame.reset_index(drop=True)
    require_model_data_use(frame)
    # Source-person identity is stable across valuations; names are not keys.
    pairs = frame[['source', 'source_player_id', 'canonical_player_id']].drop_duplicates()
    if pairs.duplicated(['source', 'source_player_id']).any() or pairs.duplicated(['source', 'canonical_player_id']).any():
        raise ValueError('Reviewed source-person identities must be one-to-one')
    conflicts = frame.groupby(['canonical_player_id', 'valuation_date']).market_value_eur.nunique()
    if conflicts.gt(1).any():
        raise ValueError('Conflicting recorded values on one effective date require review')
    return frame.sort_values(['valuation_date', 'valuation_known_at', 'record_id']).drop_duplicates(
        'canonical_player_id', keep='last').reset_index(drop=True)
