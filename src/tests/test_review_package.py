"""Teacher-review data contracts checked on retained real source/clean tables."""
import json
import pandas as pd
import pytest
from src.config import ROOT
from src.data.provenance import sha256
from src.preprocessing.review_dataset import load_raw_csv


def test_raw_source_csvs_are_present_and_byte_verified():
    catalog=json.loads((ROOT/'data/raw/review_manifest.json').read_text(encoding='utf-8'))
    assert catalog['real_data_only'] and len(catalog['raw_csvs'])==15
    assert {item['provider'] for item in catalog['raw_csvs']}=={'fbref','understat','transfermarkt'}
    for item in catalog['raw_csvs']:
        assert sha256(ROOT/item['path'])==item['sha256']


def test_csv_preprocessing_matches_served_real_gallery():
    manifest=json.loads((ROOT/'data/processed/review/manifest.json').read_text(encoding='utf-8'))
    assert manifest['frozen_gallery_numeric_parity_verified'] and not manifest['model_fitting_performed']
    info=manifest['outputs']['fbref_core_gallery']
    rebuilt=pd.read_parquet(ROOT/info['parquet_path'])
    frozen=pd.read_parquet(ROOT/'data/processed/real/five_league_pipeline_core_gallery.parquet')
    columns=['entity_id','season','league','minutes','gls_p90','ast_p90','sh_p90','sot_p90','crs_p90','int_p90','tklw_p90','fls_p90','fld_p90']
    order=['entity_id','season']
    pd.testing.assert_frame_equal(rebuilt.sort_values(order)[columns].reset_index(drop=True),frozen.sort_values(order)[columns].reset_index(drop=True),check_dtype=False,rtol=1e-12,atol=1e-12)


def test_all_review_outputs_have_verified_fingerprints():
    manifest=json.loads((ROOT/'data/processed/review/manifest.json').read_text(encoding='utf-8'))
    for info in manifest['outputs'].values():
        for kind in ['csv','parquet']:
            assert sha256(ROOT/info[f'{kind}_path'])==info[f'{kind}_sha256']
    values=pd.read_parquet(ROOT/manifest['outputs']['transfermarkt_values']['parquet_path'])
    assert not values.model_use_eligible.any()
    assert values.currency_evidence.eq('EUR_assumed_not_explicit_in_raw').all()


def test_corrupt_source_is_rejected_without_imputation(tmp_path,monkeypatch):
    import src.preprocessing.review_dataset as review
    monkeypatch.setattr(review,'ROOT',tmp_path)
    path=tmp_path/'fixture.csv';path.write_text('not-the-original-source')
    with pytest.raises(ValueError,match='fingerprint'):
        load_raw_csv({'path':'fixture.csv','sha256':'0'*64})
