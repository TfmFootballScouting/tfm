"""Teacher-review data contracts checked on retained real source/clean tables."""
import json
import pandas as pd
import pytest
from src.config import ROOT
from src.data.provenance import sha256
from src.preprocessing.prepare_datasets import load_raw_csv


def test_raw_source_csvs_are_present_and_byte_verified():
    catalog=json.loads((ROOT/'data/raw/source_manifest.json').read_text(encoding='utf-8'))
    assert catalog['real_data_only'] and len(catalog['raw_csvs'])==15
    assert {item['provider'] for item in catalog['raw_csvs']}=={'fbref','understat','transfermarkt'}
    for item in catalog['raw_csvs']:
        assert sha256(ROOT/item['path'])==item['sha256']


def test_shared_dataset_matches_original_model_training_observations():
    from src.models.recommender import PlayerRecommender
    manifest=json.loads((ROOT/'data/processed/manifest.json').read_text())
    assert manifest['shared_by_app_and_notebooks'] and not manifest['model_fitting_performed']
    saved=PlayerRecommender.load(ROOT/'models/scouting_recommender.joblib')
    prepared=pd.read_parquet(ROOT/manifest['outputs']['fbref_scouting_gallery']['parquet_path'])
    keys=['entity_id','league','season']
    training=saved.players[keys+saved.artifacts.feature_cols].sort_values(keys).reset_index(drop=True)
    rebuilt=prepared.merge(training[keys],on=keys,how='inner',validate='one_to_one')
    rebuilt=rebuilt[keys+saved.artifacts.feature_cols].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(rebuilt,training,check_dtype=False,rtol=1e-12,atol=1e-12)
    assert len(training)>0


def test_all_review_outputs_have_verified_fingerprints():
    manifest=json.loads((ROOT/'data/processed/manifest.json').read_text(encoding='utf-8'))
    for info in manifest['outputs'].values():
        for kind in ['csv','parquet']:
            assert sha256(ROOT/info[f'{kind}_path'])==info[f'{kind}_sha256']
    values=pd.read_parquet(ROOT/manifest['outputs']['transfermarkt_values']['parquet_path'])
    assert not values.model_use_eligible.any()
    assert values.currency_evidence.eq('EUR_assumed_not_explicit_in_raw').all()


def test_corrupt_source_is_rejected_without_imputation(tmp_path,monkeypatch):
    import src.preprocessing.prepare_datasets as review
    monkeypatch.setattr(review,'ROOT',tmp_path)
    path=tmp_path/'fixture.csv';path.write_text('not-the-original-source')
    with pytest.raises(ValueError,match='fingerprint'):
        load_raw_csv({'path':'fixture.csv','sha256':'0'*64})
