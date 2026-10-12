import pandas as pd
from src.models.evaluate import temporal_proxy
from src.models.recommend import PlayerRecommender
from src.scraping.transfermarkt import money_eur


def test_temporal_proxy_executes_queries_not_zero_tests(players):
    # Synthetic unit fixtures, not final football experiments.
    later=players.copy();later['season']='2023-2024';later['player_id']+=10
    out=temporal_proxy(pd.concat([players,later],ignore_index=True))
    assert set(out.method)=={'cosine_profile','euclidean_profile','random','goals_only'}
    assert (out.queries==4).all()
    assert out.mrr.between(0,1).all()
    assert (out[out.method=='euclidean_profile'].recall_at_5==1).all()


def test_no_unsupported_tactical_style(players):
    import pytest
    rec=PlayerRecommender().fit(players,feature_cols=['gls_p90','ast_p90'])
    with pytest.raises(ValueError,match='Insufficient'):
        rec.recommend('solidez_defensiva')


def test_units_and_unknown_transfer_fee():
    assert money_eur('€1.50m')==1500000
    assert money_eur('€500k')==500000
    assert money_eur('free transfer')==0
    assert money_eur('loan') is None
    assert money_eur('-') is None
