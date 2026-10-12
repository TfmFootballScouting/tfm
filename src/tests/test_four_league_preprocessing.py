import json
import numpy as np
import pandas as pd
import pytest
from src.config import ROOT
from src.data.provenance import sha256
from src.data.source_rights import require_model_data_use
from scripts.four_league_preprocessing import propose_links


def test_real_shot_summaries_do_not_count_own_goals_or_invent_minutes():
    r=json.loads((ROOT/'reports/four_league_preprocessing/preprocessing.json').read_text())
    for path,info in r['outputs'].items():assert sha256(ROOT/path)==info['sha256']
    assert sha256(ROOT/'scripts/four_league_preprocessing.py')==r['script_sha256']
    shots=pd.read_parquet(ROOT/'data/processed/real/four_league_clean_shots.parquet')
    players=pd.read_parquet(ROOT/'data/processed/real/four_league_player_seasons.parquet')
    assert len(shots)==182938 and shots.quality_valid.all()
    assert players.source_shot_events.sum()==182938
    assert players.shots.sum()==182300 and players.own_goal_events.sum()==638
    assert players.goals.sum()==shots.result.eq('Goal').sum()
    np.testing.assert_allclose(players.xg.sum(),shots.loc[shots.result.ne('OwnGoal'),'xG'].sum())
    assert not any('p90' in c or c=='appearances' for c in players)
    eligible=players[~players.partial_season & players.observed_schedule_fraction.eq(1)&players.shots.ge(20)]
    assert len(eligible)==2906 and eligible.season.lt('2025-2026').all()
    assert eligible[eligible.season.eq('2024-2025')].league.isin(['Premier League','Ligue 1']).all()


def test_identity_proposals_are_season_local_and_not_approved():
    shots=pd.read_parquet(ROOT/'data/processed/real/four_league_clean_shots.parquet')
    fbref=pd.read_parquet(ROOT/'data/processed/real/five_league_pipeline_player_club_seasons.parquet')
    full=propose_links(shots,fbref)
    cutoff='2022-2023'
    early=propose_links(shots[shots.season.le(cutoff)],fbref[fbref.season.le(cutoff)])
    columns=['league','season','source_player_id_understat','source_player_id_fbref','club_key','supported_review_candidate']
    def ordered(frame):return frame[columns].drop_duplicates().sort_values(columns).reset_index(drop=True)
    pd.testing.assert_frame_equal(ordered(full[full.season.le(cutoff)]),ordered(early))
    assert full.identity_match_status.eq('provisional_not_reviewed').all()
    assert not full.model_use_eligible.any()
    with pytest.raises(ValueError):require_model_data_use(full)
    supported=full[full.supported_review_candidate]
    a=supported.groupby(['league','season','source_player_id_understat']).source_player_id_fbref.nunique()
    b=supported.groupby(['league','season','source_player_id_fbref']).source_player_id_understat.nunique()
    assert a.eq(1).all() and b.eq(1).all()
