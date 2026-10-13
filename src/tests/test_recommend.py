import numpy as np
import pytest
from src.models.recommender import PlayerRecommender


def test_recommendation_filters_and_excludes_self(players):
    rec=PlayerRecommender(n_clusters=2).fit(players)
    out=rec.recommend('finisher',position='FW',max_age=21,top_n=5)
    assert out.player_id.tolist()==[1]
    assert 1 not in rec.similar_players(1).player_id.tolist()
    assert rec.artifacts.pca.n_components_<=min(len(players),len(rec.artifacts.feature_cols))


def test_unknown_budget_is_not_free(players):
    rec=PlayerRecommender().fit(players)
    with pytest.raises(ValueError,match='dated EUR'):
        rec.recommend('finisher',max_budget=5)


def test_known_budget_excludes_missing_and_future(players):
    players['market_value_eur']=[1e6,np.nan,2e6,2e6]
    players['valuation_date']=['2023-06-01']*3+['2024-01-01']
    players['valuation_known_at']=['2023-06-01']*4
    rec=PlayerRecommender().fit(players)
    out=rec.recommend('finisher',max_budget=5,cutoff='2023-07-01')
    assert set(out.player_id)=={1,3}


def test_future_model_rejected(players):
    rec=PlayerRecommender().fit(players)
    with pytest.raises(ValueError,match='future'):
        rec.recommend('finisher',cutoff='2023-01-01')


def test_median_is_training_only(players):
    players.loc[0,'ast_p90']=np.nan
    rec=PlayerRecommender().fit(players)
    before=rec.artifacts.imputer.statistics_.copy()
    future=players.copy();future['ast_p90']=999
    rec.transform(future)
    np.testing.assert_equal(before,rec.artifacts.imputer.statistics_)


def test_similarity_excludes_other_seasons_same_entity(players):
    players.loc[1,'entity_id']='a'
    rec=PlayerRecommender().fit(players)
    assert 'a' not in rec.similar_players(1).entity_id.tolist()
    assert rec.recommend('finisher').entity_id.is_unique


def test_small_and_constant_input(players):
    with pytest.raises(ValueError,match='two'):
        PlayerRecommender().fit(players.iloc[:1])
    constant=players.copy();constant['gls_p90']=1
    constant['ast_p90']=1;constant['ga_p90']=2
    with pytest.raises(ValueError,match='usable'):
        PlayerRecommender().fit(constant)
