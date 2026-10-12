import json
from pathlib import Path
import pandas as pd
import pytest
from src.config import ROOT
from src.data.provenance import sha256
from src.data.source_rights import require_model_data_use


def test_real_four_league_shots_and_partial_coverage():
    folder=ROOT/'reports/four_league_acquisition'
    report=json.loads((folder/'acquisition.json').read_text())
    assert sha256(ROOT/'scripts/four_league_acquisition.py')==report['script_sha256']
    counts={'Premier League':49970,'Bundesliga':40518,'Serie A':48673,'Ligue 1':43777}
    for league,count in counts.items():
        record=next(r for r in report['understat_sources'] if r['league']==league)
        assert sha256(ROOT/record['path'])==record['sha256']
        path=ROOT/'data/external/four_league_expansion'/('understat_'+league.lower().replace(' ','_')+'_shots.parquet')
        frame=pd.read_parquet(path)
        assert len(frame)==count and frame.shot_id.is_unique
        assert frame.league.eq(league).all() and frame.season.between('2020-2021','2025-2026').all()
        assert frame[['X','Y','xG']].apply(lambda c:c.between(0,1)).all().all()
        assert frame.team_side_resolved.all() and not frame.side_field_conflict.any()
        assert frame.shot_date.notna().all()
        assert frame.partial_season.eq(frame.season.eq('2025-2026')).all()
    coverage=pd.read_csv(folder/'coverage.csv')
    shot=coverage[coverage.source.eq('understat_worldfootballr')]
    assert len(shot)==24
    partial=shot[shot.season.eq('2025-2026')]
    assert partial.status.eq('partial_snapshot').all() and partial.matches.lt(partial.expected_schedule_matches).all()
    missing=pd.read_csv(folder/'missing_fixture_pairs.csv')
    assert missing.groupby('league').size().to_dict()=={'Bundesliga':1,'Serie A':6}


def test_recruitment_context_is_restricted_and_previous_artifacts_preserved():
    report=json.loads((ROOT/'reports/four_league_acquisition/acquisition.json').read_text())
    for path,info in report['outputs'].items():
        assert sha256(ROOT/path)==info['sha256']
        if 'transfermarkt_' in path:
            frame=pd.read_parquet(ROOT/path)
            assert not frame.model_use_eligible.any()
            with pytest.raises(ValueError):require_model_data_use(frame)
    previous=json.loads((ROOT/'reports/five_league_pipeline/pipeline.json').read_text())
    for path,digest in previous['preserved_sha256'].items():assert sha256(ROOT/path)==digest
    for path,digest in previous['code_sha256'].items():assert sha256(ROOT/path)==digest
    for info in previous['outputs'].values():assert sha256(ROOT/info['path'])==info['sha256']
    for info in previous['experiments'].values():assert sha256(ROOT/info['model_path'])==info['model_sha256']
    fbref=pd.read_parquet(ROOT/'data/external/four_league_expansion/fbref_passing.parquet')
    assert {'PPA','KP','PrgP','Cmp_Long','Att_Long','category_exposure_compatible'} <=set(fbref)
    assert set(fbref.league)==set(report['leagues'])
