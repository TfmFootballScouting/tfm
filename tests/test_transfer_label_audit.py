"""Artificial audit fixtures only; final experiments must use real observations."""
import pandas as pd
from scripts.transfer_label_audit import classify_events, audit_cases


def histories():
    rows = [
        ('2021-07-01', 'Transfer', 'Club A', 'Club B', 'a', 'b'),
        ('2021-08-01', 'Loan', 'Club A', 'Club C', 'a', 'c'),
        ('2022-06-30', 'Return from loan', 'Club C', 'Club A', 'c', 'a'),
        ('2021-09-01', 'Transfer', 'Club A', 'Retired', 'a', 'r'),
        ('2021-06-30', 'Transfer', 'Club A', 'Club D', 'a', 'd'),
        ('bad-date', 'Transfer', 'Club A', 'Club B', 'a', 'b'),
    ]
    return pd.DataFrame([dict(player_id='t1', transfer_date=date, transfer_type=kind,
        from_team_name=origin, to_team_name=destination, from_team_id=left, to_team_id=right,
        season_start_year=2021) for date, kind, origin, destination, left, right in rows])


def fixtures():
    gallery = pd.DataFrame([
        dict(entity_id='fbref:f1', source_player_id='f1', season='2020-2021', league='La Liga'),
        dict(entity_id='fbref:f1', source_player_id='f1', season='2021-2022', league='La Liga'),
        dict(entity_id='fbref:f2', source_player_id='f2', season='2020-2021', league='La Liga'),
    ])
    links = pd.DataFrame([dict(canonical_player_id_proposed='fbref:f1', source_player_id='t1', supported_review_candidate=True)])
    return gallery, links


def test_classifies_loans_non_club_and_unresolved_dates_separately():
    events = classify_events(histories())
    assert events.event_kind.tolist() == ['permanent_club_change', 'loan', 'loan_return',
        'non_club_or_unknown_transition', 'permanent_club_change', 'permanent_club_change']
    assert events.event_date_usable.tolist() == [True, True, True, True, False, False]


def test_labels_consecutive_seasons_without_inventing_negatives():
    gallery, links = fixtures()
    cases = audit_cases(gallery, links, classify_events(histories()))
    first, following, unmapped = cases.iloc[0], cases.iloc[1], cases.iloc[2]
    assert first.observed_positive_candidate == 1 and first.permanent_events == 1
    assert first.loan_events == 1 and first.loan_return_events == 1 and first.non_club_events == 1
    assert following.label_status == 'no_recorded_permanent_transfer_followup_unknown'
    assert pd.isna(following.observed_positive_candidate)
    assert unmapped.label_status == 'identity_unmapped'
    assert cases.verified_binary_target.isna().all()
    assert not cases.model_use_eligible.any()


def test_duplicate_events_do_not_inflate_positive_counts():
    gallery, links = fixtures()
    raw = histories()
    cases = audit_cases(gallery, links, classify_events(pd.concat([raw, raw.iloc[[0]]], ignore_index=True)))
    assert cases.iloc[0].permanent_events == 1
