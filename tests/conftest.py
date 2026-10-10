"""Small unit-test fixtures only; never used in football experiments."""
import sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

@pytest.fixture
def players():
    # Deliberately artificial unit-test observations.
    return pd.DataFrame(dict(player_id=[1,2,3,4],entity_id=['a','b','c','d'],player=['A','B','C','D'],
        team=['T1','T2','T3','T4'],league=['La Liga']*4,season=['2022-2023']*4,
        pos=['FW','MF','DF','MF,FW'],pos_main=['FW','MF','DF','MF'],age=[20,25,30,22],
        minutes=[900,1200,1800,1000],gls_p90=[.5,.2,0,.3],ast_p90=[.1,.5,0,.4],ga_p90=[.6,.7,0,.7]))
