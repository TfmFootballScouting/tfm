"""Artificial collision/temporal fixtures; the script itself reads real archives."""
import pandas as pd
import pytest

from src.data_preparation.identity import build_crosswalk, club_key, join_preview, match_identities
from src.data_preparation.source_rights import require_model_data_use


def people(ids=('a',), names=('Álex García',), teams=('Betis',), years=(1998,), season='2020-2021'):
    return pd.DataFrame(dict(source_player_id=ids, player=names, team=teams,
                             birth_year=years, season=[season]*len(ids)))


def test_name_plus_club_season_and_year_and_stable_person_key():
    fb = people()
    us = people(ids=('u',), names=('Alex Garcia',), teams=('Real Betis',)).drop(columns='birth_year')
    trial = match_identities(fb, us, 'understat', '2020-2021')
    row = trial.iloc[0]
    assert row.proposal_status == 'high_support_proposal'
    assert row.evidence_score == 70 and not row.birth_year_agreement
    assert row.overlapping_club_seasons == 1
    another = match_identities(fb.assign(season='2021-2022', team='Valencia'),
                              us.assign(season='2021-2022', team='Valencia'), 'understat', '2021-2022')
    crosswalk = build_crosswalk(pd.concat([trial, another], ignore_index=True))
    assert crosswalk.canonical_player_id.tolist() == ['fbref:a', 'fbref:a']
    assert not crosswalk.unstable_across_cutoffs.any()
    with pytest.raises(ValueError, match='Unreviewed'):
        require_model_data_use(crosswalk)


def test_same_name_same_club_tie_stays_unresolved():
    fb = people(ids=('a', 'b'), names=('Alex Garcia', 'Alex Garcia'), teams=('Betis', 'Betis'), years=(1998, 1999))
    us = people(ids=('u',)).drop(columns='birth_year')
    trial = match_identities(fb, us, 'understat', '2020-2021')
    assert len(trial) == 2 and trial.proposal_status.eq('review_required').all()
    assert build_crosswalk(trial).empty


def test_birth_year_disambiguates_and_conflict_is_never_accepted():
    fb = people(ids=('a', 'b'), names=('Alex Garcia', 'Alex Garcia'), teams=('Betis', 'Betis'), years=(1998, 1999))
    tm = people(ids=('t',), names=('Alex Garcia',), teams=('Real Betis Balompié',))
    tm['date_of_birth'] = pd.Timestamp('1998-05-20')
    trial = match_identities(fb, tm, 'transfermarkt', '2020-2021')
    assert trial.set_index('left_id').proposal_status.to_dict() == {
        'a': 'high_support_proposal', 'b': 'conflicting_identity'}
    assert trial.set_index('left_id').loc['a', 'birth_year_agreement']


def test_near_name_requires_birth_year_and_club_evidence():
    fb = people(names=('Alexander Garcia',))
    other = people(ids=('t',), names=('Alexandre Garcia',))
    trial = match_identities(fb, other, 'transfermarkt', '2020-2021')
    assert not trial.exact_name.iloc[0] and trial.proposal_status.iloc[0] == 'high_support_proposal'
    no_year = match_identities(fb, other.drop(columns='birth_year'), 'understat', '2020-2021')
    assert no_year.proposal_status.iloc[0] == 'review_required'


def test_future_club_and_name_evidence_do_not_resolve_earlier_season():
    fb = people()
    us_early = people(ids=('u',), teams=('Sevilla',)).drop(columns='birth_year')
    us_later = people(ids=('u',), teams=('Real Betis',), season='2021-2022').drop(columns='birth_year')
    us = pd.concat([us_early, us_later], ignore_index=True)
    early = match_identities(fb, us, 'understat', '2020-2021')
    pd.testing.assert_frame_equal(early, match_identities(fb, us_early, 'understat', '2020-2021'))
    assert early.overlapping_club_seasons.iloc[0] == 0
    assert early.proposal_status.iloc[0] == 'review_required'
    # A future spelling alias cannot create even a name-only candidate early.
    future_alias = us.copy()
    future_alias.loc[0, 'player'] = 'Different Person'
    assert match_identities(fb, future_alias, 'understat', '2020-2021').empty


def test_cross_cutoff_identity_switch_is_flagged_and_order_is_stable():
    fb = people()
    us = people(ids=('u',)).drop(columns='birth_year')
    trial = match_identities(fb, us, 'understat', '2020-2021')
    switched = trial.assign(left_id='b', season_cutoff='2021-2022')
    crosswalk = build_crosswalk(pd.concat([trial, switched], ignore_index=True))
    assert crosswalk.unstable_across_cutoffs.tolist() == [False, True]
    assert crosswalk.identity_match_status.iloc[1] == 'unstable_mapping_review_required'
    pd.testing.assert_frame_equal(crosswalk.iloc[:1].reset_index(drop=True), build_crosswalk(trial))
    multi_fb = pd.concat([fb, people(ids=('b',), names=('Other Player',))], ignore_index=True)
    pd.testing.assert_frame_equal(match_identities(multi_fb, us, 'understat', '2020-2021'),
                                  match_identities(multi_fb.iloc[::-1], us.iloc[::-1], 'understat', '2020-2021'))


def test_join_preview_preserves_grain_and_source_values_without_budget_eligibility():
    fb = people().assign(entity_id='fbref:a', gls=3., xg=1.5)
    us = people(ids=('u',), teams=('Real Betis',)).assign(shots=10, goals=2, own_goals=0,
                                                        xg=1.2, matches_with_shot_records=5)
    us['season'] = '2021-2022'
    # No future source context is attached to the 2020/21 row, despite a trial mapping.
    trial = match_identities(people(), people(ids=('u',)), 'understat', '2020-2021')
    tm = people(ids=('t',)).assign(date_of_birth=pd.Timestamp('1998-05-20'), height_cm=180., foot='right',
                                  market_value_eur=10., valuation_date=pd.NaT,
                                  valuation_known_at=pd.NaT, ml_use_status='restricted_pending_explicit_license')
    tm_trial = match_identities(people(), tm, 'transfermarkt', '2020-2021')
    crosswalk = build_crosswalk(pd.concat([trial, tm_trial], ignore_index=True))
    preview = join_preview(fb, us, tm, crosswalk)
    assert len(preview) == len(fb) and preview.understat_player_id.isna().all()
    assert preview.gls.iloc[0] == 3. and preview.xg.iloc[0] == 1.5
    assert preview.transfermarkt_market_value_eur.iloc[0] == 10.
    assert preview.transfermarkt_valuation_date.isna().all()
    assert not preview.model_eligible.any() and not preview.budget_filter_supported.any()
    assert preview.mapping_source.iloc[0] == 'transfermarkt'
    with pytest.raises(ValueError, match='Unreviewed'):
        require_model_data_use(preview)
    current = join_preview(fb, us.assign(season='2020-2021'), tm, crosswalk)
    assert current.gls.iloc[0] == 3. and current.understat_goals.iloc[0] == 2
    assert current.xg.iloc[0] == 1.5 and current.understat_xg.iloc[0] == 1.2
    # Duplicate context must be excluded, never averaged or chosen arbitrarily.
    preview = join_preview(fb, us, pd.concat([tm, tm.assign(height_cm=185)]), crosswalk)
    assert preview.transfermarkt_player_id.isna().all()


def test_explicit_club_aliases_do_not_strip_unrelated_names():
    assert club_key('Athletic Bilbao') == club_key('Athletic Club')
    assert club_key('Atlético de Madrid') == club_key('Atlético Madrid')
    assert club_key('Real Sociedad') != club_key('Sociedad')
    assert club_key(pd.NA) == ''


def test_same_name_and_club_in_different_leagues_is_not_context_agreement():
    fb = people().assign(league='La Liga')
    us = people(ids=('u',)).drop(columns='birth_year').assign(league='Segunda')
    trial = match_identities(fb, us, 'understat', '2020-2021')
    assert trial.overlapping_club_seasons.iloc[0] == 0
    assert trial.proposal_status.iloc[0] == 'review_required'
