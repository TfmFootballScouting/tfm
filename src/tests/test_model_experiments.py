"""Artificial unit fixtures; real experiments never use these observations."""
import numpy as np
import pandas as pd
import pytest

from src.models.experiments import cohorts, evaluate_pair, score_methods, target_metrics
from src.models.recommender import PlayerRecommender


def test_uniform_ties_are_not_broken_by_player_id_order():
    expected = target_metrics(np.zeros(100), 0)
    assert expected == target_metrics(np.zeros(100), 99)
    assert expected['recall_at_5'] == .05 and expected['recall_at_10'] == .1
    assert expected['reciprocal_rank'] == pytest.approx(np.mean(1/np.arange(1, 101)))
    assert expected['tie_size'] == 100
    excluded = target_metrics(np.array([1., 0., -np.inf]), 2)
    assert not excluded['target_available'] and excluded['reciprocal_rank'] == 0


def test_future_rows_do_not_change_fitted_preprocessing(players):
    rec = PlayerRecommender(n_clusters=2).fit(players, ['gls_p90', 'ast_p90'])
    future = players.assign(season='2023-2024', player_id=players.player_id+100)
    statistics = rec.artifacts.imputer.statistics_.copy()
    scale = rec.artifacts.scaler.mean_.copy()
    scores, details = evaluate_pair(rec, players, future, 'validation')
    assert (scores.queries == 4).all() and set(details.entity_id) == set(players.entity_id)
    assert scores[scores.method.eq('euclidean_profile')].mrr.iloc[0] == 1
    future['gls_p90'] = 999.
    evaluate_pair(rec, players, future, 'validation')
    np.testing.assert_array_equal(rec.artifacts.imputer.statistics_, statistics)
    np.testing.assert_array_equal(rec.artifacts.scaler.mean_, scale)
    with pytest.raises(ValueError, match='Queries must precede'):
        evaluate_pair(rec, future, players, 'bad')
    future_fit = PlayerRecommender().fit(future, ['gls_p90', 'ast_p90'])
    with pytest.raises(ValueError, match='future evaluation'):
        evaluate_pair(future_fit, players, future, 'bad')


def test_cohort_chronology_keys_and_sources_are_enforced(players):
    source = players.assign(source='fbref')
    rows = pd.concat([source.assign(experiment_split='train'),
                      source.assign(season='2023-2024', player_id=players.player_id+10, experiment_split='validation'),
                      source.assign(season='2024-2025', player_id=players.player_id+20, experiment_split='holdout')], ignore_index=True)
    assert len(cohorts(rows, 'experiment_split')['train']) == 4
    with pytest.raises(ValueError, match='Aggregate'):
        cohorts(pd.concat([rows, rows.iloc[:1]]), 'experiment_split')
    with pytest.raises(ValueError, match='source-separated'):
        cohorts(rows.assign(source='transfermarkt'), 'experiment_split')
    bad = rows.copy()
    bad.loc[bad.experiment_split.eq('holdout'), 'season'] = '2021-2022'
    with pytest.raises(ValueError, match='Chronological'):
        cohorts(bad, 'experiment_split')


def test_cluster_gate_excludes_target_instead_of_granting_a_fake_rank(players):
    rec = PlayerRecommender(n_clusters=2).fit(players, ['gls_p90', 'ast_p90'])
    scores = score_methods(rec, players, players)
    for i in range(len(players)):
        assert np.isfinite(scores['cluster_cosine'][i, i])
        excluded = np.flatnonzero(~np.isfinite(scores['cluster_cosine'][i]))
        for j in excluded:
            assert target_metrics(scores['cluster_cosine'][i], j)['reciprocal_rank'] == 0
    assert any((~np.isfinite(row)).any() for row in scores['cluster_cosine'])


def test_selected_neighbor_method_survives_model_roundtrip(players, tmp_path):
    rec = PlayerRecommender(n_clusters=2).fit(players, ['gls_p90', 'ast_p90'])
    original_mean = rec.artifacts.scaler.mean_.copy()
    for method in ['euclidean_profile', 'pca2_euclidean', 'pca4_cosine', 'cluster_cosine']:
        rec.configure_neighbors(method)
        path = rec.save(tmp_path/'model.joblib')
        loaded = PlayerRecommender.load(path)
        assert loaded.neighbor_method == method
        out = loaded.similar_players(1, top_n=3)
        assert 1 not in out.player_id.tolist() and out.distance.is_monotonic_increasing
        np.testing.assert_array_equal(loaded.artifacts.scaler.mean_, original_mean)
    rec.configure_neighbors('euclidean_profile')
    matrix = score_methods(rec, players.iloc[:1], players)['euclidean_profile'][0]
    order = np.argsort(-matrix)
    expected = players.iloc[order].query('player_id != 1').player_id.tolist()
    assert rec.similar_players(1, top_n=3).player_id.tolist() == expected
    assert rec.similar_players(1).similarity.between(0, 1).all()
    rec.fit(players, ['gls_p90', 'ast_p90'])
    assert rec.artifacts.knn.metric == 'euclidean'
