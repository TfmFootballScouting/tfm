import pandas as pd
import numpy as np
import pytest
from src.preprocessing.player_records import clean_players
from src.data.fbref import merge_tables
from src.data.matching import propose_matches,value_asof
from src.scraping.collect import parse_understat,parse_fbref,Client,AccessBlocked


def raw():
    return pd.DataFrame(dict(player=['A','B'],team=['Club1','Club2'],pos=['FW','DF'],age=[20,25],
        minutes=[900,1800],season=['2022-2023']*2,league=['La Liga']*2,source=['fbref']*2,
        source_player_id=['a','b'],gls=[5,0],ast=[2,None]))


def test_missing_is_not_zero_and_no_invented_budget():
    out=clean_players(raw())
    assert out.gls_p90.iloc[0]==.5
    assert pd.isna(out.ast_p90.iloc[1]) and out.int_p90.isna().all()
    assert 'budget_est' not in out


def test_synthetic_rejected():
    df=raw();df.loc[0,'source']='demo'
    with pytest.raises(ValueError,match='synthetic'):
        clean_players(df)


def test_stable_ids_and_conflicting_duplicates():
    df=raw()
    a,b=clean_players(df),clean_players(df.iloc[::-1])
    assert a.set_index('player').player_id.to_dict()==b.set_index('player').player_id.to_dict()
    bad=pd.concat([df,df.iloc[:1].assign(gls=9)])
    with pytest.raises(ValueError,match='Conflicting'):
        clean_players(bad)


def test_transfer_total_preferred():
    df=raw();more=df.iloc[:1].copy();more['team']='2 squads';more['minutes']=1000
    out=clean_players(pd.concat([df,more]))
    assert out[out.source_player_id=='a'].team.tolist()==['2 squads']


def test_merge_uses_player_and_club_keys():
    std=raw();aux=std[['source_player_id','team','league','season']].iloc[::-1].copy()
    aux['shots']=[10,20]
    merged=merge_tables(std,[aux])
    assert merged.sh.tolist()==[20,10]
    with pytest.raises(Exception):
        merge_tables(std,[pd.concat([aux,aux])])


def test_matching_ambiguous_and_exact_dob():
    left=pd.DataFrame(dict(source_player_id=['a'],player=['Álex García'],date_of_birth=['2000-01-01']))
    right=pd.DataFrame(dict(source_player_id=['b','c'],player=['Alex Garcia','Alex Garcia'],date_of_birth=['2000-01-01']*2))
    assert propose_matches(left,right).status.iloc[0]=='review_required'
    assert propose_matches(left,right.iloc[:1]).status.iloc[0]=='exact_name_dob'
    no_dob=left.drop(columns='date_of_birth')
    assert propose_matches(no_dob,right.iloc[:1]).status.iloc[0]=='review_required'


def test_asof_excludes_future_publication():
    v=pd.DataFrame(dict(source_player_id=['a','a','b'],valuation_date=['2020-01-01','2022-01-01','2020-01-01'],
        known_at=['2020-01-01','2022-01-01','2023-01-01'],currency=['EUR']*3,value_eur=[1,2,3]))
    out=value_asof(v,'2021-01-01')
    assert out.value_eur.tolist()==[1]


def test_understat_parser_preserves_accents():
    html="<script>var playersData = JSON.parse('[{\"id\":\"1\",\"player_name\":\"Álex\"}]');</script>"
    assert parse_understat(html).player_name.iloc[0]=='Álex'
    with pytest.raises(ValueError,match='absent'):
        parse_understat('<html>No data</html>')


def test_fbref_comment_tables():
    html='<!-- <table id="stats_standard"><tbody><tr><th data-stat="player"><a href="/en/players/abc/X">X</a></th><td data-stat="team">A</td></tr></tbody></table> -->'
    assert parse_fbref(html,'standard').source_player_id.iloc[0]=='abc'


def test_no_retry_on_network_denial(monkeypatch):
    import requests
    calls=[]
    def denied(*a,**k):
        calls.append(1);raise requests.exceptions.ProxyError('403 Forbidden')
    client=Client();monkeypatch.setattr(client.session,'get',denied)
    for _ in range(2):
        with pytest.raises(AccessBlocked):
            client.get('https://fbref.com/en/comps/12','fbref')
    assert len(calls)==1
