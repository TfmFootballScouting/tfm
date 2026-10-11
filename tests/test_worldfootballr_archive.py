"""Artificial unit fixtures; archive provenance checks use real saved file hashes."""
import json
import pandas as pd
import pytest
from scripts.worldfootballr_archive import aligned_stats,ensure_snapshot


def test_archive_merge_exposure_guard():
    std=pd.DataFrame(dict(source_player_id=['a','b'],team=['X','Y'],season=['2024-2025']*2,Min_Playing=[900,1800]))
    aux=std[['source_player_id','team','season']].iloc[::-1].copy()
    aux['Mins_Per_90']=[10,10];aux['shots']=[5,12]
    result=aligned_stats(std,aux,{'shots':'sh'})
    assert result.sh.iloc[0]==12
    assert pd.isna(result.sh.iloc[1]),'Partial-period totals must not be divided by full-season exposure'


def test_archive_checksum_mismatch(tmp_path,monkeypatch):
    import scripts.worldfootballr_archive as archive
    monkeypatch.setattr(archive,'ROOT',tmp_path)
    path=tmp_path/'raw.rds';path.write_bytes(b'unit fixture')
    with pytest.raises(ValueError,match='checksum'):
        ensure_snapshot({'path':'raw.rds','sha256':'0'*64,'category':'fixture'})
