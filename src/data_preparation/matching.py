"""Conservative cross-source identity proposals, never fuzzy auto-merges."""
import re
import unicodedata

import pandas as pd


def normalize_name(value):
    text = unicodedata.normalize('NFKD', str(value))
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in text if not unicodedata.combining(c)).lower())


def propose_matches(left, right, approved=None):
    """Require unique exact name + DOB. Otherwise produce a review candidate.

    Source IDs remain authoritative within each source. Approved mappings are explicit
    (left_id, right_id); enforce one-to-one cardinality before using them.
    """
    approved = approved if approved is not None else pd.DataFrame(columns=['left_id', 'right_id'])
    if approved.left_id.duplicated().any() or approved.right_id.duplicated().any():
        raise ValueError('Approved identity mapping must be one-to-one')
    if left.source_player_id.duplicated().any() or right.source_player_id.duplicated().any():
        raise ValueError('Resolve source entities before cross-source matching')
    decisions = []
    for _, a in left.iterrows():
        explicit = approved[approved.left_id.astype(str) == str(a.source_player_id)]
        candidates = right[right.player.map(normalize_name) == normalize_name(a.player)]
        status, target = 'unmatched', None
        if len(explicit):
            target = str(explicit.iloc[0].right_id)
            if target not in set(right.source_player_id.astype(str)):
                raise ValueError('Approved target ID does not exist')
            status = 'approved'
        elif len(candidates):
            dob = a.get('date_of_birth')
            same_dob = candidates[candidates.get('date_of_birth', pd.Series(index=candidates.index, dtype=object)) == dob] if pd.notna(dob) else candidates.iloc[:0]
            # A duplicated left-side identity with the same name/DOB also prevents auto-match.
            same_left = left[(left.player.map(normalize_name) == normalize_name(a.player)) & (left.get('date_of_birth', pd.Series(index=left.index, dtype=object)) == dob)]
            if len(same_dob) == 1 and len(same_left) == 1:
                status, target = 'exact_name_dob', str(same_dob.iloc[0].source_player_id)
            else:
                status = 'review_required'
        decisions.append(dict(left_id=str(a.source_player_id), right_id=target, status=status,
                              candidate_ids='|'.join(candidates.source_player_id.astype(str))))
    result = pd.DataFrame(decisions)
    if not result.empty and result.right_id.dropna().duplicated().any():
        raise ValueError('Multiple left identities map to one right identity; manual review required')
    return result


def value_asof(valuations, cutoff):
    """Historical EUR valuations only; current snapshots never backfill history."""
    v = valuations.copy()
    for c in ['valuation_date', 'known_at']:
        v[c] = pd.to_datetime(v[c], utc=True, errors='raise')
    t = pd.Timestamp(cutoff)
    t = t.tz_localize('UTC') if t.tzinfo is None else t
    v = v[(v.valuation_date <= t) & (v.known_at <= t) & (v.currency == 'EUR')]
    return v.sort_values('valuation_date').drop_duplicates('source_player_id', keep='last')
