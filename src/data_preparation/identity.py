"""Auditable multi-feature identity proposals; scores are rules, not probabilities."""
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
import hashlib
import json
import re
import unicodedata

import pandas as pd

from src.data.matching import normalize_name

# Explicit spelling aliases observed in the retained three-source La Liga tables.
# Do not strip generic prefixes globally: that could merge different clubs.
CLUB_ALIASES = {
    'realbetis': 'betis', 'realbetisbalompie': 'betis',
    'sdhuesca': 'huesca', 'realoviedo': 'oviedo',
    'realvalladolid': 'valladolid', 'realvalladolidcf': 'valladolid',
    'athleticbilbao': 'athleticclub', 'atleticodemadrid': 'atleticomadrid',
    'caosasuna': 'osasuna', 'celtadevigo': 'celtavigo', 'cadizcf': 'cadiz',
    'deportivoalaves': 'alaves', 'elchecf': 'elche', 'fcbarcelona': 'barcelona',
    'getafecf': 'getafe', 'gironafc': 'girona', 'granadacf': 'granada',
    'levanteud': 'levante', 'rcdespanyolbarcelona': 'espanyol',
    'rcdmallorca': 'mallorca', 'sdeibar': 'eibar', 'sevillafc': 'sevilla',
    'udalmeria': 'almeria', 'valenciacf': 'valencia', 'villarrealcf': 'villarreal',
}
MATCH_COLUMNS = [
    'left_source', 'left_id', 'right_source', 'right_id', 'season_cutoff',
    'left_name', 'right_name', 'exact_name', 'name_similarity',
    'overlapping_club_seasons', 'birth_year_agreement', 'birth_year_conflict',
    'profile_conflict', 'upstream_id_mapping', 'evidence_score',
    'left_margin', 'right_margin', 'proposal_status', 'evidence',
]


def club_key(value):
    if pd.isna(value):
        return ''
    key = normalize_name(value)
    return CLUB_ALIASES.get(key, key)


def _league(row):
    value = getattr(row, 'league', getattr(row, 'comp_name', pd.NA))
    return 'unknown' if pd.isna(value) else normalize_name(value)


def _name(value):
    return '' if pd.isna(value) else normalize_name(value)


@lru_cache(maxsize=20000)
def _tokens(value):
    text = unicodedata.normalize('NFKD', str(value))
    text = ''.join(c for c in text if not unicodedata.combining(c)).lower()
    return tuple(re.findall(r'[a-z0-9]+', text))


def _entities(frame, cutoff):
    """Use only source rows at/before the requested season, including name aliases."""
    required = {'source_player_id', 'player', 'team', 'season'}
    if not required <= set(frame):
        raise ValueError('Identity matching requires player ID, name, club and season')
    if frame[['source_player_id', 'season']].isna().any().any():
        raise ValueError('Missing source identity or season')
    if not frame.season.astype(str).str.fullmatch(r'20\d{2}-20\d{2}').all():
        raise ValueError('Invalid identity season')
    if not frame.season.map(lambda s: int(s[5:]) == int(s[:4]) + 1).all():
        raise ValueError('Invalid consecutive identity season')
    rows = frame[frame.season.le(cutoff)]
    entities = {}
    for pid, group in rows.groupby('source_player_id', sort=True):
        names = sorted({str(v).strip() for v in group.player.dropna() if _name(v)})
        years = set()
        if 'birth_year' in group:
            years.update(pd.to_numeric(group.birth_year, errors='coerce').dropna().astype(int))
        dobs = set()
        if 'date_of_birth' in group:
            dobs = set(pd.to_datetime(group.date_of_birth, errors='coerce').dropna())
            years.update(d.year for d in dobs)
        entities[str(pid)] = dict(
            names=names, keys={_name(v) for v in names}, years=years,
            profile_conflict=len(years) > 1 or len(dobs) > 1,
            contexts={(_league(r), club_key(r.team), r.season) for r in group.itertuples() if club_key(r.team)},
        )
    return entities


@lru_cache(maxsize=150000)
def _pair_similarity(a, b):
    ta, tb = _tokens(a), _tokens(b)
    ratio = max(SequenceMatcher(None, _name(a), _name(b)).ratio(),
                SequenceMatcher(None, ''.join(sorted(ta)), ''.join(sorted(tb))).ratio())
    # Fuzzy proposals need multi-token names with at least one exact token.
    return ratio, len(ta) >= 2 and len(tb) >= 2 and bool(set(ta) & set(tb))


def _similarity(left, right):
    if not left['names'] or not right['names']:
        return 0., False
    return max(_pair_similarity(a, b) for a in left['names'] for b in right['names'])


def match_identities(left, right, right_source, cutoff, mapping=None):
    """Propose FBref↔source links using names, club-season history and birth year.

    No learned weights, automatic approvals or measured matching accuracy. Retain
    ties and competing identities. Margins and reciprocal best matches enforce
    one-to-one proposals within each source pair and season snapshot.
    """
    a, b = _entities(left, cutoff), _entities(right, cutoff)
    by_name, by_context = defaultdict(set), defaultdict(set)
    for pid, person in b.items():
        for key in person['keys']:
            by_name[key].add(pid)
        for context in person['contexts']:
            by_context[context].add(pid)
    upstream = set()
    if mapping is not None and right_source == 'transfermarkt':
        upstream = {(str(r.fbref_id), str(r.transfermarkt_id))
                    for r in mapping[['fbref_id', 'transfermarkt_id']].dropna().itertuples()}
    upstream_by_left = defaultdict(set)
    for lid, rid in upstream:
        if rid in b:
            upstream_by_left[lid].add(rid)
    records = []
    for lid, person in a.items():
        blocked = set(upstream_by_left[lid])
        for key in person['keys']:
            blocked.update(by_name[key])
        for context in person['contexts']:
            blocked.update(by_context[context])
        for rid in sorted(blocked):
            other = b[rid]
            exact = bool(person['keys'] & other['keys'])
            similarity, fuzzy_supported = _similarity(person, other)
            upstream_match = (lid, rid) in upstream
            if not exact and similarity < .80 and not upstream_match:
                continue
            overlap = len(person['contexts'] & other['contexts'])
            known_years = bool(person['years'] and other['years'])
            year_conflict = known_years and person['years'] != other['years']
            year_agree = known_years and not year_conflict
            profile_conflict = person['profile_conflict'] or other['profile_conflict']
            score = (50 if exact else 35 if similarity >= .92 and fuzzy_supported else 0)
            score += 20 * bool(overlap) + 5 * (overlap >= 2) + 20 * year_agree + 5 * upstream_match
            # Evidence does not establish identity if authoritative details conflict.
            eligible = not (year_conflict or profile_conflict) and (
                (exact and (bool(overlap) or year_agree)) or
                (similarity >= .92 and fuzzy_supported and bool(overlap) and year_agree))
            evidence = dict(normalized_name_agreement=exact, club_season_overlap=overlap,
                            birth_year='conflict' if year_conflict else 'agreement' if year_agree else 'unknown',
                            upstream_mapping=upstream_match, fuzzy_name_supported=fuzzy_supported)
            records.append(dict(left_source='fbref', left_id=lid, right_source=right_source,
                right_id=rid, season_cutoff=cutoff,
                left_name=' | '.join(person['names']), right_name=' | '.join(other['names']),
                exact_name=exact, name_similarity=round(similarity, 6),
                overlapping_club_seasons=overlap, birth_year_agreement=year_agree,
                birth_year_conflict=year_conflict, profile_conflict=profile_conflict,
                upstream_id_mapping=upstream_match, evidence_score=int(score),
                evidence=json.dumps(evidence, sort_keys=True), _eligible=eligible))
    if not records:
        return pd.DataFrame(columns=MATCH_COLUMNS)
    result = pd.DataFrame(records)
    result['left_margin'] = 0
    result['right_margin'] = 0
    for key, margin in [('left_id', 'left_margin'), ('right_id', 'right_margin')]:
        # Conflict candidates cannot veto otherwise consistent matches.
        valid = result[~(result.birth_year_conflict | result.profile_conflict)]
        best = valid.groupby(key).evidence_score.max()
        winners = valid[valid.evidence_score.eq(valid[key].map(best))]
        winner_count = winners.groupby(key).size()
        second = valid[valid.evidence_score.lt(valid[key].map(best))].groupby(key).evidence_score.max()
        sole_winner = (result.evidence_score.eq(result[key].map(best)) &
                       result[key].map(winner_count).eq(1) &
                       ~(result.birth_year_conflict | result.profile_conflict))
        runner_up = result[key].map(best).fillna(0).where(~sole_winner, result[key].map(second).fillna(0))
        result[margin] = (result.evidence_score - runner_up).astype(int)
    result['proposal_status'] = 'review_required'
    supported = result._eligible & result.left_margin.ge(10) & result.right_margin.ge(10)
    result.loc[supported, 'proposal_status'] = 'high_support_proposal'
    result.loc[result.birth_year_conflict | result.profile_conflict, 'proposal_status'] = 'conflicting_identity'
    proposed = result[result.proposal_status.eq('high_support_proposal')]
    if proposed.left_id.duplicated().any() or proposed.right_id.duplicated().any():
        raise ValueError('Proposed identity mapping is not one-to-one')
    return result[MATCH_COLUMNS].sort_values(['left_id', 'right_id']).reset_index(drop=True)


def build_crosswalk(trials):
    """Stable FBref-anchored person ID; neither name nor season enters this key."""
    links = trials[trials.proposal_status.eq('high_support_proposal')].copy()
    links = links.sort_values(['season_cutoff', 'right_source', 'left_id', 'right_id']).reset_index(drop=True)
    links['canonical_player_id'] = 'fbref:' + links.left_id
    links['identity_match_status'] = 'provisional_not_reviewed'
    # Flag changes only when they become visible; later conflicts must not change
    # earlier snapshots or retrospectively select historical observations.
    right_history, left_history = defaultdict(set), defaultdict(set)
    unstable = []
    for row in links.itertuples():
        right_history[(row.right_source, row.right_id)].add(row.left_id)
        left_history[(row.right_source, row.left_id)].add(row.right_id)
        unstable.append(len(right_history[(row.right_source, row.right_id)]) > 1 or
                        len(left_history[(row.right_source, row.left_id)]) > 1)
    links['unstable_across_cutoffs'] = pd.Series(unstable, dtype=bool)
    links.loc[links.unstable_across_cutoffs, 'identity_match_status'] = 'unstable_mapping_review_required'
    return links.reset_index(drop=True)


def join_preview(clubs, shooters, valuations, crosswalk):
    """Source-prefixed club-season preview, never attach current prices to history."""
    out = clubs.copy()
    out['canonical_player_id'] = out.entity_id
    out['club_join_key'] = out.team.map(club_key)
    out['league_join_key'] = [_league(r) for r in out.itertuples()]
    keys = ['source_player_id', 'league_join_key', 'season', 'club_join_key']
    if out.duplicated(keys).any():
        raise ValueError('Conflicting canonical FBref club-season join keys')
    out['identity_match_status'] = 'provisional_not_reviewed'
    out['model_eligible'] = False
    out['baseline_candidate'] = False
    out['historical_candidate'] = False
    out['tactical_proxy_candidate'] = False
    out['budget_filter_supported'] = False
    out['identity_temporal_status'] = 'season_bounded_evidence; publication_dates_unknown'
    for source, frame, columns in [
        ('understat', shooters, ['player', 'shots', 'goals', 'own_goals', 'xg', 'matches_with_shot_records']),
        ('transfermarkt', valuations, ['player', 'date_of_birth', 'height_cm', 'foot',
                                      'market_value_eur', 'valuation_date', 'valuation_known_at', 'ml_use_status'])]:
        links = crosswalk[crosswalk.right_source.eq(source) & ~crosswalk.unstable_across_cutoffs]
        links = links[['left_id', 'right_id', 'season_cutoff', 'evidence_score']]
        if links.duplicated(['right_id', 'season_cutoff']).any() or links.duplicated(['left_id', 'season_cutoff']).any():
            raise ValueError('Crosswalk contains conflicting source-season links')
        context = frame.copy()
        context['club_join_key'] = context.team.map(club_key)
        context['league_join_key'] = [_league(r) for r in context.itertuples()]
        # No arbitrary first record if the source has conflicting club-season rows.
        context_keys = ['source_player_id', 'league_join_key', 'season', 'club_join_key']
        context['context_conflict'] = context.duplicated(context_keys, keep=False)
        context = context[~context.context_conflict]
        context = context[['source_player_id', 'league_join_key', 'season', 'club_join_key'] + columns]
        context = context.rename(columns={'source_player_id': 'right_id', **{c: source+'_'+c for c in columns}})
        attached = links.merge(context, left_on=['right_id', 'season_cutoff'],
                               right_on=['right_id', 'season'], validate='one_to_many')
        attached = attached.drop(columns='season_cutoff').rename(columns={
            'left_id': 'source_player_id', 'right_id': source+'_player_id',
            'evidence_score': source+'_identity_score'})
        out = out.merge(attached, on=keys, how='left', validate='one_to_one')
    out['mapping_source'] = out.transfermarkt_player_id.map(
        lambda x: 'transfermarkt' if pd.notna(x) else pd.NA)
    return out.sort_values(keys).reset_index(drop=True)


def code_fingerprint(paths):
    return hashlib.sha256(json.dumps(paths, sort_keys=True).encode()).hexdigest()
