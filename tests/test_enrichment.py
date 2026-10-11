import json

import numpy as np
import pandas as pd
import pytest

from src.config import ROOT
from src.preprocessing.enrichment import numeric_reported, aggregate_seasons, merge_review_only
from src.data.source_rights import require_model_data_use, SourceUseRestricted
from scripts.salimt_history_audit import sha


def test_numeric_unknown_negative_fractional_counts():
    values, invalid = numeric_reported(pd.Series(['0', '90.0', None, '-', '-1', '2.5', 'inf']))
    assert values.iloc[:2].tolist() == [0, 90]
    assert values.iloc[2:].isna().all()
    assert invalid.tolist() == [False, False, False, True, True, True, True]


def test_real_missing_stint_does_not_create_full_season_rate():
    stints = pd.read_parquet(ROOT / 'data/processed/real/collected_enrichment_player_club_seasons.parquet')
    group = next(group for _, group in stints.groupby(['player_id', 'season', 'league'])
                 if len(group) > 1 and group.minutes_played.isna().any())
    result = aggregate_seasons(group).iloc[0]
    assert pd.isna(result.minutes_played)
    assert pd.isna(result.gls_p90)
    assert not result.minutes_eligible
    assert result.club_count > 1


def test_real_join_preserves_base_and_never_enters_models():
    base = pd.read_parquet(ROOT / 'data/processed/real/collected_player_seasons.parquet')
    enriched = pd.read_parquet(ROOT / 'data/processed/real/collected_enrichment_integration_review.parquet')
    pd.testing.assert_frame_equal(base.drop(columns=['ml_use_status']),
                                  enriched[base.columns].drop(columns=['ml_use_status']))
    assert enriched.salimt_source_player_id.notna().any()
    assert not enriched.model_use_eligible.any()
    with pytest.raises(ValueError, match='Unreviewed'): require_model_data_use(enriched)
    proposals = pd.read_parquet(ROOT / 'data/processed/real/collected_salimt_identity_candidates.parquet')
    bad = pd.concat([proposals, proposals[proposals.supported_review_candidate].iloc[:1]])
    seasons = pd.read_parquet(ROOT / 'data/processed/real/collected_enrichment_player_seasons.parquet')
    with pytest.raises(ValueError, match='Ambiguous'): merge_review_only(base, seasons, bad)


def test_real_transfer_deduplication_zero_semantics_and_date_bound_prices():
    events = pd.read_parquet(ROOT / 'data/processed/real/collected_enrichment_transfers.parquet')
    raw = pd.read_parquet(ROOT / 'data/processed/real/collected_salimt_transfer_history.parquet')
    assert len(raw) - len(events) == 37
    assert events.source_event_id.is_unique
    assert sum(len(json.loads(value)) for value in events.source_row_numbers) == len(raw)
    zeros = events[events.transfer_fee_zero_ambiguous]
    assert zeros.fee_semantics.eq('unknown_or_zero_not_verified_free').all()
    assert zeros.transfer_type.eq('Loan').any()
    with pytest.raises(SourceUseRestricted): require_model_data_use(events)
    prices = pd.read_parquet(ROOT / 'data/processed/real/collected_enrichment_reported_price_context.parquet')
    assert (prices.reported_value_date.dropna() <= prices.loc[prices.reported_value_date.notna(), 'report_cutoff']).all()
    assert not prices.historical_budget_eligible.any()


def test_real_artifacts_and_eligible_model_reruns():
    report = json.loads((ROOT / 'reports/enrichment/pipeline.json').read_text())
    for name, expected in {**report['preserved_input_sha256'], **report['outputs_sha256'], **report['code_sha256']}.items():
        assert sha(ROOT / name) == expected
    original = json.loads((ROOT / 'reports/collected_model_results.json').read_text())
    for name, info in report['new_model_experiments'].items():
        assert info['exported_artifacts'] > 10
        assert info['learned_features_source'].startswith('FBref only')
        np.testing.assert_allclose(info['holdout_mrr'], original['experiments'][name]['holdout_metrics']['mrr'])
        assert info['selected_method'] == original['experiments'][name]['selected_method']
    assert len(report['new_model_experiments']) == 3
