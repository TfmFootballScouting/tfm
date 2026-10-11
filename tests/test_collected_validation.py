"""Artificial unit fixtures are isolated from real-data diagnostic runs."""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.models.recommend import PlayerRecommender
from src.models.validation import (feature_drift, pca_alignment, person_block_indices,
                                   position_retrieval, temporal_validation)


def test_person_bootstrap_keeps_all_seasons_and_multiplicity():
    players = pd.DataFrame({'entity_id': ['a', 'b', 'a', 'c', 'b']})
    class FixedDraw:
        def choice(self, identities, size, replace):
            assert identities == ['a', 'b', 'c'] and size == 3 and replace
            return ['b', 'a', 'b']
    indexes, sampled = person_block_indices(players, FixedDraw())
    assert indexes.tolist() == [1, 4, 0, 2, 1, 4]
    assert sampled == {'a', 'b'} and 'c' not in players.iloc[indexes].entity_id.tolist()
    with pytest.raises(ValueError, match='nonmissing'):
        person_block_indices(pd.DataFrame({'entity_id': ['a', None]}), FixedDraw())


def test_pca_sign_order_and_standardization_do_not_create_false_instability():
    original = SimpleNamespace(components_=np.eye(4))
    other = SimpleNamespace(components_=np.eye(4)[[1, 0, 3, 2]]*np.array([-1, 1, -1, 1])[:, None])
    components, spaces = pca_alignment(original, other, np.ones(4), np.ones(4))
    assert all(row['absolute_loading_cosine'] == pytest.approx(1) for row in components)
    assert all(row['maximum_angle_degrees'] == pytest.approx(0, abs=1e-10) for row in spaces)
    # A rotated two-dimensional subspace is stable even if individual axes change.
    rotation = np.eye(4)
    rotation[:2, :2] = [[2**-.5, 2**-.5], [-2**-.5, 2**-.5]]
    components, spaces = pca_alignment(original, SimpleNamespace(components_=rotation), np.ones(4), np.ones(4))
    assert components[0]['absolute_loading_cosine'] < .8
    assert spaces[0]['maximum_angle_degrees'] == pytest.approx(0, abs=1e-10)
    scaled = SimpleNamespace(components_=rotation*np.array([2, 3, 4, 5]))
    c2, s2 = pca_alignment(original, scaled, np.ones(4), np.array([2, 3, 4, 5]))
    assert c2 == components
    assert s2[0]['maximum_angle_degrees'] == pytest.approx(0, abs=1e-10)


def _retrieval_fixture():
    rows = []
    for method, values in [('goals_assists', [.1, .8]), ('euclidean_profile', [.3, .9])]:
        for identity, value in zip(['a', 'b'], values):
            rows.append(dict(phase='holdout', query_season='2022-2023', evaluation_season='2023-2024',
                position='DF', method=method, entity_id=identity, candidate_count=100,
                reciprocal_rank=value, recall_at_5=0., recall_at_10=0., ndcg_at_10=0., target_available=True))
    return pd.DataFrame(rows)


def test_subgroup_comparison_pairs_baseline_by_identity_not_row_order():
    details = _retrieval_fixture()
    forward = position_retrieval(details)
    backward = position_retrieval(details.iloc[::-1])
    pd.testing.assert_frame_equal(forward, backward)
    row = forward[forward.method.eq('euclidean_profile')].iloc[0]
    assert row.mrr_delta_goals_assists == pytest.approx(.15)
    assert row.delta_ci_low >= .1-1e-12 and row.delta_ci_high <= .2+1e-12
    with pytest.raises(ValueError, match='same identities'):
        position_retrieval(details.iloc[:-1])
    with pytest.raises(ValueError, match='Duplicate'):
        position_retrieval(pd.concat([details, details.iloc[:1]]))


def test_drift_uses_training_bins_and_reports_missing_instead_of_zero():
    train = pd.DataFrame({'rate': [0, 1, 2, 3, np.nan]})
    future = pd.DataFrame({'rate': [10, 11, 12, 13, np.nan]})
    same = feature_drift(train, train, ['rate'], [2]).iloc[0]
    changed = feature_drift(train, future, ['rate'], [2]).iloc[0]
    assert same.js_divergence == pytest.approx(0)
    assert changed.mean_shift_training_sd == pytest.approx(5)
    assert changed.missing_future == 1 and changed.mean_future == pytest.approx(11.5)
    assert 0 < changed.js_divergence <= 1
    assert changed.histogram_bins == same.histogram_bins


def test_temporal_diagnostics_freeze_model_and_record_cluster_changes(players):
    rec = PlayerRecommender(n_clusters=2).fit(players, ['gls_p90', 'ast_p90'])
    future = players.assign(season='2023-2024', player_id=players.player_id+100)
    future[['gls_p90', 'ast_p90']] = future[['gls_p90', 'ast_p90']].iloc[::-1].to_numpy()
    means, centers = rec.artifacts.scaler.mean_.copy(), rec.artifacts.kmeans.cluster_centers_.copy()
    out = temporal_validation(rec, {'train': players, 'validation': future})
    assert out['cluster_transitions'].returning_players.sum() == len(players)
    assert set(out['feature_drift'].phase) == {'validation'}
    np.testing.assert_array_equal(means, rec.artifacts.scaler.mean_)
    np.testing.assert_array_equal(centers, rec.artifacts.kmeans.cluster_centers_)
    assert not out['cluster_transitions'].cluster_previous.eq(out['cluster_transitions'].cluster_future).all()
    with pytest.raises(ValueError, match='overlap or run backwards'):
        temporal_validation(rec, {'train': players, 'validation': players})
