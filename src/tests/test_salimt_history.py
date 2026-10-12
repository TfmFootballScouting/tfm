"""Checks for source-grain preservation and real uploaded history evidence."""
import json
import pandas as pd
from scripts.salimt_history_audit import season_year, sha
from src.config import ROOT
from src.data.source_rights import require_model_data_use, SourceUseRestricted
import pytest

def test_season_validation():
    values = season_year(pd.Series(['20/21', '25/26', '99/00', '80/81', '20/22', None, '2020/21']))
    assert values.iloc[:4].tolist() == [2020, 2025, 1999, 1980]
    assert values.iloc[4:].isna().all()

def test_real_history_grain_and_provenance():
    report = json.loads((ROOT / 'reports/salimt_history_audit.json').read_text())
    for name, expected in {**report['preserved_input_sha256'], **report['outputs_sha256']}.items():
        assert sha(ROOT / name) == expected
    assert sha(ROOT / 'scripts/salimt_history_audit.py') == report['code_sha256']
    for name, receipt in report['receipt']['files'].items():
        base = ROOT / 'data/raw/sources/salimt_uploaded/histories'
        assert sha(base / (name + '.zip')) == receipt['archive_sha256']
        assert sha(base / (name + '.txt')) == receipt['payload_sha256']
    data = pd.read_parquet(ROOT / 'data/processed/real/collected_salimt_performance_history.parquet')
    assert len(data) == report['statistics']['player_performances']['target_rows']
    assert data.competition_id.isin(['ES1', 'ES2']).all()
    assert data.season_start_year.between(2020, 2025).all()
    assert data.source_row_number.is_unique
    assert data.source_publication_known_at.isna().all()
    assert not data.model_use_eligible.any()
    assert data.groupby(['player_id', 'season']).team_id.nunique().gt(1).any()
    with pytest.raises(SourceUseRestricted): require_model_data_use(data)
    assert all(row['performance_rows'] > 0 for row in report['coverage'])
    assert all(row['players'] > 0 for row in report['coverage'])
