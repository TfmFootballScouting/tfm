"""Artificial unit fixtures only; final preprocessing reads retained real files."""
import numpy as np
import pandas as pd
import pytest

from src.features.requirements import ALL_COUNTS
from src.preprocessing.collected import (aggregate_player_seasons, approved_matches,
    identity_candidates, normalize_fbref, normalize_shots, normalize_transfers, normalize_valuations)


def stints():
    frame = pd.DataFrame(dict(source_player_id=['f1', 'f1'], player=['Player A']*2,
        team=['Club A', 'Club B'], season=['2022-2023']*2, league=['La Liga']*2,
        source=['fbref_worldfootballr']*2, pos=['FW', 'MF'], age=['24', '24'],
        nation=['ESP']*2, minutes=[200., 300.], mp=[5, 8], birth_year=[1998]*2,
        period_status=['historical_season_label_completeness_not_guaranteed']*2))
    for column in ALL_COUNTS:
        frame[column] = [1., 2.]
    frame['sh'] = [4., 8.]
    return frame


def test_aggregate_before_minutes_floor_and_missing_stint_propagates():
    raw = stints()
    raw.loc[1, 'int'] = np.nan
    clubs, _, _ = normalize_fbref(raw)
    assert not clubs.minutes_eligible.any()
    seasons = aggregate_player_seasons(clubs)
    row = seasons.iloc[0]
    assert row.minutes == 500 and row.baseline_candidate
    assert row.team == '2 clubs' and row.club_count == 2
    assert row.gls_p90 == pytest.approx(3*90/500)
    assert pd.isna(row.int) and pd.isna(row.int_p90)
    assert not row.complete_core_features
    assert row.pos_main == 'MF'
    assert isinstance(row.player_id, (int, np.integer))
    assert row.player_id not in clubs.player_id.tolist()


def test_ids_and_aggregation_independent_of_input_order():
    a, _, _ = normalize_fbref(stints())
    b, _, _ = normalize_fbref(stints().iloc[::-1])
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(aggregate_player_seasons(a), aggregate_player_seasons(b))


def test_duplicate_conflicts_and_synthetic_are_rejected():
    frame = stints()
    with pytest.raises(ValueError, match='Conflicting'):
        normalize_fbref(pd.concat([frame, frame.iloc[:1].assign(gls=7)]))
    with pytest.raises(ValueError, match='Synthetic'):
        normalize_fbref(frame.assign(source='demo'))


def test_partial_and_gk_not_historical_outfield_candidates():
    frame = stints().assign(minutes=900, season='2025-2026')
    clubs, _, _ = normalize_fbref(frame)
    seasons = aggregate_player_seasons(clubs)
    assert seasons.partial_season.all() and not seasons.historical_candidate.any()
    clubs, _, _ = normalize_fbref(stints().assign(minutes=900, pos='GK'))
    assert not aggregate_player_seasons(clubs).baseline_candidate.any()


def test_xag_not_substituted_for_xa_and_invalid_is_unknown():
    raw = stints().drop(columns='xa')
    raw.loc[0, 'ast'] = -2
    raw.loc[1, 'xg'] = np.inf
    raw['passes_attempted'] = raw.passes_attempted.astype(object)
    raw.loc[0, 'passes_attempted'] = 'malformed'
    clubs, issues, _ = normalize_fbref(raw)
    assert clubs.xa_p90.isna().all() and clubs.xag_p90.notna().all()
    assert pd.isna(clubs.ast.iloc[0]) and pd.isna(clubs.ga.iloc[0])
    assert pd.isna(clubs.xg.iloc[1])
    assert sum(row['invalid_values_nulled'] for row in issues) == 3
    assert pd.isna(clubs.pass_completion_pct.iloc[0])
    assert clubs.market_value_eur.isna().all() and not clubs.budget_filter_supported.any()


def test_understat_side_schema_and_own_goals():
    raw = pd.DataFrame(dict(shot_id=['1','2'], source_player_id=['u1','u1'],
        season=['2022-2023']*2, player=['Player A']*2, home_team=['H']*2, away_team=['A']*2,
        match_id=[10,10], h_a=['h',None], home_away=[None,'h'], date=['2023-01-01']*2,
        X=[.8,.9], Y=[.4,.3], xG=[.2,.1], minute=[10,15], result=['Goal','OwnGoal']))
    shots, summaries, _ = normalize_shots(raw)
    assert shots.team.tolist() == ['H','H']
    assert summaries.goals.iloc[0] == 1 and summaries.own_goals.iloc[0] == 1
    assert summaries.shots.iloc[0] == 1 and summaries.recorded_shot_events.iloc[0] == 2
    assert summaries.xg.iloc[0] == pytest.approx(.2)
    assert summaries.minutes.isna().all() and 'xg_p90' not in summaries
    with pytest.raises(ValueError, match='shot-side'):
        normalize_shots(raw.assign(h_a=None, home_away='unknown'))


def test_profiles_keep_dates_and_unknown_values_separate():
    raw = pd.DataFrame(dict(source_player_id=['t1'], player_name=['Player A'], squad=['Club A'],
        player_dob=['1998-05-20'], player_height_mtrs=['1.85'], player_foot=['right'],
        player_age=[24], player_market_value_euro=[None], season=['2022-2023'], player_url=['/spieler/1']))
    cleaned, _ = normalize_valuations(raw)
    assert cleaned.height_cm.iloc[0] == 185
    assert cleaned.date_of_birth.iloc[0] == pd.Timestamp('1998-05-20')
    assert cleaned.market_value_eur.isna().all() and cleaned.valuation_date.isna().all()


def test_transfer_mirrors_not_claimed_unique_dated_events():
    raw = pd.DataFrame(dict(source_player_id=['t1']*3, team_name=['B','A','A'],
        club_2=['A','B','B'], transfer_type=['Arrivals','Departures','Departures'],
        season=['2022-2023']*3, window=['Summer']*3, transfer_fee=[0.,0.,0.]))
    cleaned, removed, _ = normalize_transfers(raw)
    assert removed == 1 and len(cleaned) == 2
    assert cleaned.potential_movement_id.nunique() == 1
    assert cleaned.fee_zero_unverified.all() and cleaned.transfer_date.isna().all()


def test_name_matches_require_review_and_ledger_evidence(tmp_path):
    clubs, _, _ = normalize_fbref(stints())
    shooters = pd.DataFrame(dict(source_player_id=['u1'], player=['Player A']))
    valuations = pd.DataFrame(columns=['source_player_id','player','date_of_birth'])
    mapping = pd.DataFrame(columns=['fbref_id','transfermarkt_id'])
    queue = identity_candidates(clubs, shooters, valuations, mapping)
    assert queue.status.tolist() == ['review_required']
    assert approved_matches(tmp_path/'absent.csv', queue).empty
    ledger = tmp_path/'reviewed.csv'
    pd.DataFrame(dict(left_source=['fbref'],left_id=['f1'],right_source=['understat'],right_id=['u1'],
        reviewer=[''],evidence=['name'],reviewed_at=['2026-10-11'])).to_csv(ledger,index=False)
    with pytest.raises(ValueError, match='reviewer'):
        approved_matches(ledger,queue)


def test_retained_real_segunda_sample_header_units_and_season():
    from src.config import ROOT
    from src.scraping.transfermarkt import scorer_sample
    path = ROOT/'data/raw/sources/transfermarkt/b8c738ba3c6685f9832bbae67b63e0c21e867a035781eeb4e4ad973ba2fda519.html'
    sample = scorer_sample(path.read_bytes(), '2024-2025')
    suarez = sample.set_index('source_player_id').loc['424784']
    assert suarez.minutes == 3648 and suarez.gls == 27 and suarez.ast == 8
    assert sample.ml_use_status.eq('restricted_pending_explicit_license').all()
    assert 'age' not in sample and sample.source_player_id.is_unique
    with pytest.raises(ValueError, match='does not confirm'):
        scorer_sample(path.read_bytes(), '2023-2024')
