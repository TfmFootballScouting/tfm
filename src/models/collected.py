"""Temporal profile-retrieval experiments on collected FBref observations.

Future profiles are evaluation targets, never model-fitting inputs. Identity
retrieval measures profile persistence, not recommendation relevance or transfers.
"""
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from src.config import FEATURE_COLS, RANDOM_SEED
from src.models.recommend import PlayerRecommender

EXPERIMENTS = {
    'offensive': dict(table='collected_baseline_candidates', split='experiment_split',
                      features=['gls_p90', 'ast_p90', 'sh_p90', 'sot_p90', 'xg_p90', 'xag_p90']),
    'core': dict(table='collected_tactical_candidates', split='core_proxy_split',
                 features=[c for c in FEATURE_COLS if c != 'ga_p90']),
    'attack_on_core': dict(table='collected_tactical_candidates', split='core_proxy_split',
                           features=['gls_p90', 'ast_p90', 'sh_p90', 'sot_p90', 'xg_p90', 'xag_p90']),
}
PROFILE_METHODS = ['cosine_profile', 'euclidean_profile', 'pca2_cosine', 'pca2_euclidean',
                   'pca4_cosine', 'pca4_euclidean', 'cluster_cosine']


def cohorts(players, split):
    """Validate chronology and one observation per source person/league/season."""
    if players.duplicated(['entity_id', 'league', 'season']).any():
        raise ValueError('Aggregate club stints before model evaluation')
    if 'source' not in players or not players.source.isin(['fbref', 'fbref_worldfootballr']).all():
        raise ValueError('Collected models require source-separated real FBref data')
    result = {part: players[players[split].eq(part)].sort_values(['season', 'entity_id']).copy()
              for part in ['train', 'validation', 'holdout']}
    if any(len(v) < 2 for v in result.values()):
        raise ValueError('Training, validation and holdout cohorts are required')
    if not (result['train'].season.max() < result['validation'].season.min() < result['holdout'].season.min()):
        raise ValueError('Chronological cohorts overlap or run backwards')
    if result['validation'].season.nunique() != 1 or result['holdout'].season.nunique() != 1:
        raise ValueError('One evaluation season per fold is required')
    return result


def cosine_scores(A, B):
    return (A @ B.T) / np.maximum(np.linalg.norm(A, axis=1)[:, None] * np.linalg.norm(B, axis=1), 1e-12)


def score_methods(rec, queries, candidates):
    A, B = rec.transform(queries), rec.transform(candidates)
    return _transformed_scores(rec, A, B)


def _transformed_scores(rec, A, B):
    names = rec.artifacts.feature_cols
    scores = dict(cosine_profile=cosine_scores(A, B), euclidean_profile=-cdist(A, B),
                  random=np.random.default_rng(RANDOM_SEED).random((len(A), len(B))))
    goals = names.index('gls_p90')
    assists = names.index('ast_p90')
    scores['goals_only'] = -np.abs(A[:, goals, None] - B[None, :, goals])
    scores['goals_assists'] = -cdist(A[:, [goals, assists]], B[:, [goals, assists]])
    pa, pb = rec.artifacts.pca.transform(A), rec.artifacts.pca.transform(B)
    for n in [2, 4]:
        width = min(n, pa.shape[1])
        scores[f'pca{n}_cosine'] = cosine_scores(pa[:, :width], pb[:, :width])
        scores[f'pca{n}_euclidean'] = -cdist(pa[:, :width], pb[:, :width])
    same_cluster = rec.artifacts.kmeans.predict(A)[:, None] == rec.artifacts.kmeans.predict(B)[None, :]
    scores['cluster_cosine'] = np.where(same_cluster, scores['cosine_profile'], -np.inf)
    return scores


def target_metrics(scores, target):
    """Uniform tie handling: expected reciprocal rank and hit probability.

    Baselines with many zero goals must not benefit from source-ID row ordering.
    A hard cluster gate that excludes the target receives zero, not a fake rank.
    """
    value = scores[target]
    if not np.isfinite(value):
        return dict(mean_rank=np.nan, reciprocal_rank=0., recall_at_5=0., recall_at_10=0.,
                    ndcg_at_10=0., target_available=False, tie_size=0)
    greater = int((scores > value + 1e-10).sum())
    ties = int(np.isclose(scores, value, atol=1e-10, rtol=0).sum())
    ranks = np.arange(greater + 1, greater + ties + 1)
    return dict(mean_rank=float(ranks.mean()), reciprocal_rank=float((1/ranks).mean()),
                recall_at_5=float(np.clip((5-greater)/ties, 0, 1)),
                recall_at_10=float(np.clip((10-greater)/ties, 0, 1)),
                ndcg_at_10=float(np.where(ranks <= 10, 1/np.log2(ranks+1), 0).mean()),
                target_available=True, tie_size=ties)


def evaluate_pair(rec, previous, future, phase):
    if previous.entity_id.duplicated().any() or future.entity_id.duplicated().any():
        raise ValueError('Evaluation requires unique season-level identities')
    if previous.season.max() >= future.season.min():
        raise ValueError('Queries must precede the evaluation season')
    if rec.players.season.max() >= future.season.min():
        raise ValueError('Model was fitted using future evaluation observations')
    previous = previous.sort_values('entity_id').reset_index(drop=True)
    future = future.sort_values('entity_id').reset_index(drop=True)
    common = sorted(set(previous.entity_id) & set(future.entity_id))
    if not common:
        raise ValueError('No returning identities for the temporal proxy')
    query = previous[previous.entity_id.isin(common)].reset_index(drop=True)
    targets = {eid: i for i, eid in enumerate(future.entity_id)}
    scores = score_methods(rec, query, future)
    details = []
    for method, matrix in scores.items():
        for i, row in query.iterrows():
            details.append(dict(phase=phase, method=method, entity_id=row.entity_id, player=row.player,
                position=row.pos_main, query_season=row.season, evaluation_season=future.season.iloc[0],
                candidate_count=len(future), **target_metrics(matrix[i], targets[row.entity_id])))
    details = pd.DataFrame(details)
    metrics = []
    rng = np.random.default_rng(RANDOM_SEED)
    boot = rng.integers(0, len(common), (200, len(common)))
    for method, group in details.groupby('method', sort=True):
        row = dict(phase=phase, method=method, query_season=previous.season.iloc[0],
                   evaluation_season=future.season.iloc[0], queries=len(common),
                   previous_players=len(previous), candidate_count=len(future),
                   returning_player_fraction=len(common)/len(previous),
                   target_available_fraction=float(group.target_available.mean()),
                   random_expected_recall_at_5=min(5, len(future))/len(future))
        for field in ['reciprocal_rank', 'recall_at_5', 'recall_at_10', 'ndcg_at_10']:
            values = group[field].to_numpy()
            key = 'mrr' if field == 'reciprocal_rank' else field
            row[key] = float(values.mean())
            sample = values[boot].mean(axis=1)
            row[key+'_ci_low'], row[key+'_ci_high'] = map(float, np.quantile(sample, [.025, .975]))
        # Paired bootstrap compares the same returning players; uncertainty is
        # conditional on this archive cohort, not a population causal estimate.
        baseline = details[details.method.eq('goals_assists')].reciprocal_rank.to_numpy()
        difference = group.reciprocal_rank.to_numpy() - baseline
        row['mrr_delta_goals_assists'] = float(difference.mean())
        row['mrr_delta_ci_low'], row['mrr_delta_ci_high'] = map(float, np.quantile(difference[boot].mean(axis=1), [.025, .975]))
        metrics.append(row)
    return pd.DataFrame(metrics), details


def select_training_clusters(rec):
    rows = []
    for k in range(2, min(8, len(np.unique(rec.X, axis=0))-1)+1):
        model = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_SEED).fit(rec.X)
        value = silhouette_score(rec.X, model.labels_, sample_size=min(800, len(rec.X)), random_state=RANDOM_SEED)
        rows.append(dict(k=k, training_silhouette=float(value), min_cluster_size=int(np.bincount(model.labels_).min()),
                         selection_scope='training_only'))
    if not rows:
        raise ValueError('Too few distinct profiles for cluster analysis')
    search = pd.DataFrame(rows)
    selected = int(search.sort_values(['training_silhouette', 'k'], ascending=[False, True]).iloc[0].k)
    return selected, search


def cluster_analysis(rec):
    stability = []
    for seed in [0, 1, 7, 42, 100]:
        labels = KMeans(n_clusters=rec.artifacts.kmeans.n_clusters, n_init=10, random_state=seed).fit_predict(rec.X)
        stability.append(dict(seed=seed, adjusted_rand=float(adjusted_rand_score(rec.players.cluster, labels))))
    centroids = pd.DataFrame(rec.artifacts.kmeans.cluster_centers_, columns=rec.artifacts.feature_cols)
    centroids.index.name = 'cluster'
    profiles = rec.players.groupby('cluster')[rec.artifacts.feature_cols].mean()
    sizes = rec.players.groupby('cluster').agg(observations=('player_id', 'size'), people=('entity_id', 'nunique'))
    summary = dict(position_nmi=float(normalized_mutual_info_score(rec.players.cluster, rec.players.pos_main)),
                   season_nmi=float(normalized_mutual_info_score(rec.players.cluster, rec.players.season)),
                   seed_ari_mean=float(np.mean([r['adjusted_rand'] for r in stability])))
    return pd.DataFrame(stability), centroids, profiles, sizes, summary


def shortlist_robustness(rec):
    """Resample real training observations; never perturb/invent football rows."""
    gallery = rec.players[rec.players.season.eq(rec.players.season.max())].sort_values('entity_id').copy()
    references = []
    for pos in ['FW', 'MF', 'DF']:
        eligible = gallery[gallery.pos_main.eq(pos)]
        if len(eligible) >= 6:
            references.append(eligible.sort_values(['minutes', 'entity_id'], ascending=[False, True]).iloc[0])
    if not references:
        raise ValueError('Not enough position-specific players for shortlist analysis')
    queries = pd.DataFrame(references)
    method = getattr(rec, 'neighbor_method', 'cosine_profile')
    baseline = score_methods(rec, queries, gallery)[method]
    def top(matrix, i):
        mask = gallery.pos_main.eq(queries.iloc[i].pos_main) & gallery.entity_id.ne(queries.iloc[i].entity_id)
        allowed = np.flatnonzero(mask)
        return set(gallery.iloc[allowed[np.argsort(-matrix[i, allowed], kind='stable')[:5]]].entity_id)
    originals = [top(baseline, i) for i in range(len(queries))]
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    for trial in range(20):
        sampled = rec.players.iloc[rng.integers(0, len(rec.players), len(rec.players))][rec.artifacts.feature_cols]
        imputer, scaler = SimpleImputer(strategy='median'), StandardScaler()
        scaler.fit(imputer.fit_transform(sampled))
        A = scaler.transform(imputer.transform(queries[rec.artifacts.feature_cols]))
        B = scaler.transform(imputer.transform(gallery[rec.artifacts.feature_cols]))
        scores = _transformed_scores(rec, A, B)[method]
        for i in range(len(queries)):
            current = top(scores, i)
            rows.append(dict(trial=trial, reference=queries.iloc[i].player, position=queries.iloc[i].pos_main,
                             method=method, top5_jaccard=len(current & originals[i])/len(current | originals[i])))
    return pd.DataFrame(rows)


def qualitative_shortlists(rec, selected_method):
    gallery = rec.players[rec.players.season.eq(rec.players.season.max())].sort_values('entity_id').copy()
    rows = []
    for pos in ['FW', 'MF', 'DF']:
        subset = gallery[gallery.pos_main.eq(pos)]
        if len(subset) < 2:
            continue
        reference = subset.sort_values(['minutes', 'entity_id'], ascending=[False, True]).iloc[:1]
        matrix = score_methods(rec, reference, subset)[selected_method][0]
        allowed = subset.entity_id.ne(reference.entity_id.iloc[0]) & subset.age.notna() & subset.age.le(27)
        # Do not infer current club for the aggregated multi-club season label.
        allowed &= subset.club_count.eq(1) & subset.team.ne(reference.team.iloc[0])
        indexes = np.flatnonzero(allowed & np.isfinite(matrix))
        ranked = indexes[np.argsort(-matrix[indexes], kind='stable')[:5]]
        for rank, index in enumerate(ranked, 1):
            candidate = subset.iloc[index]
            rows.append(dict(reference=reference.player.iloc[0], reference_entity=reference.entity_id.iloc[0],
                reference_club=reference.team.iloc[0], position=pos, season=candidate.season, rank=rank,
                player=candidate.player, entity_id=candidate.entity_id, team=candidate.team, age=candidate.age,
                minutes=candidate.minutes, method=selected_method, similarity_score=float(matrix[index]),
                budget_status='not_applied; dated valuations unavailable',
                interpretation='descriptive alternatives; no transfer/relevance labels',
                **{c: float(candidate[c]) if pd.notna(candidate[c]) else None for c in rec.artifacts.feature_cols}))
    return pd.DataFrame(rows)


def fit_experiment(players, spec):
    parts = cohorts(players, spec['split'])
    # Fit transformations once on development seasons. Never refit on validation
    # or holdout, including when the previous-season query is from validation.
    rec = PlayerRecommender(n_clusters=2, n_pca=4).fit(parts['train'], spec['features'])
    k, search = select_training_clusters(rec)
    rec = PlayerRecommender(n_clusters=k, n_pca=4).fit(parts['train'], spec['features'])
    past = parts['train'][parts['train'].season.eq(parts['train'].season.max())]
    validation, validation_details = evaluate_pair(rec, past, parts['validation'], 'validation')
    selected = validation[validation.method.isin(PROFILE_METHODS)].sort_values(['mrr', 'method'], ascending=[False, True]).iloc[0].method
    holdout, holdout_details = evaluate_pair(rec, parts['validation'], parts['holdout'], 'holdout')
    scores = pd.concat([validation, holdout], ignore_index=True)
    scores['selected_on_validation'] = scores.method.eq(selected)
    rec.configure_neighbors(selected)
    return rec, parts, search, scores, pd.concat([validation_details, holdout_details], ignore_index=True), selected
