"""Descriptive evaluation, temporal proxies and honest baselines (not transfer success)."""
import itertools
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from src.config import PLAY_STYLES, RANDOM_SEED
from src.features.styles import affinity_scores, style_vector, measured_weight_fraction
from src.models.recommend import PlayerRecommender


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else None


def analyze(rec):
    X, a = rec.X, rec.artifacts
    labels = rec.players.cluster.to_numpy()
    metrics = {}
    if 1 < len(np.unique(labels)) < len(X):
        metrics['silhouette_kmeans'] = float(silhouette_score(X, labels))
    metrics['pca_explained_variance_sum'] = float(a.pca.explained_variance_ratio_.sum())
    ranks, robustness, baselines, scenarios = [], [], [], []
    rng = np.random.default_rng(RANDOM_SEED)
    for style in PLAY_STYLES:
        coverage = measured_weight_fraction(style, a.feature_cols)
        if coverage < .6:
            baselines.append(dict(style=style, measured_weight_fraction=coverage, status='unsupported_missing_statistics'))
            continue
        top = rec.recommend(style, top_n=10)
        ranks.append((style, set(top.player_id)))
        linear = rec.players.iloc[np.argsort(-(X @ style_vector(style, a.feature_cols)), kind='stable')[:10]]
        baseline_sets = {'linear_weighted': set(linear.player_id), 'minutes': set(rec.players.nlargest(10, 'minutes').player_id),
                         'goals_assists': set(rec.players.nlargest(10, 'ga_p90').player_id)}
        baselines.append(dict(style=style, measured_weight_fraction=coverage, status='supported_descriptive',
                              **{f'overlap_{name}': jaccard(top.player_id, ids) for name,ids in baseline_sets.items()}))
        reference = style_vector(style, a.feature_cols)
        for trial in range(20):
            weights = reference * rng.uniform(.8, 1.2, len(reference))
            denom = np.maximum(np.linalg.norm(X, axis=1)*np.linalg.norm(weights), 1e-12)
            scores = X @ weights / denom
            perturbed = rec.players.iloc[np.argsort(-scores, kind='stable')[:10]].player_id
            robustness.append(dict(style=style, perturbation='weight_20_percent', trial=trial, top10_jaccard=jaccard(top.player_id, perturbed)))
        # Resample observed training rows, refit preprocessing only, and rank the fixed
        # original candidate set. This captures preprocessing sensitivity without
        # inventing football observations or future labels.
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
        for trial in range(30):
            sampled = rec.players.iloc[rng.integers(0,len(X),len(X))][a.feature_cols]
            imputer = SimpleImputer(strategy='median')
            scaler = StandardScaler()
            scaler.fit(imputer.fit_transform(sampled))
            boot_X = scaler.transform(imputer.transform(rec.players[a.feature_cols]))
            score = affinity_scores(boot_X,style,a.feature_cols)
            ranked = rec.players.iloc[np.argsort(-score,kind='stable')[:10]].player_id
            robustness.append(dict(style=style,perturbation='training_bootstrap',trial=trial,
                                   top10_jaccard=jaccard(top.player_id,ranked)))
        for pos in ['FW', 'MF', 'DF']:
            candidates = rec.recommend(style, position=pos, top_n=5)
            for rank,(_,row) in enumerate(candidates.iterrows(), 1):
                scenarios.append(dict(style=style, position=pos, rank=rank, player=row.player,
                                      team=row.team, season=row.season, affinity=row.affinity,
                                      budget_status='blocked: no verified historical EUR valuations'))
    overlaps = [jaccard(a,b) for (_,a),(_,b) in itertools.combinations(ranks,2)]
    metrics['mean_top10_jaccard_overlap'] = float(np.mean(overlaps))
    cluster_rows = []
    for seed in [0,1,7,42,100]:
        other = KMeans(n_clusters=a.kmeans.n_clusters, n_init=10, random_state=seed).fit_predict(X)
        cluster_rows.append(dict(seed=seed, adjusted_rand=float(adjusted_rand_score(labels,other))))
    metrics['cluster_seed_ari_mean'] = float(np.mean([r['adjusted_rand'] for r in cluster_rows]))
    return metrics, pd.DataFrame(baselines), pd.DataFrame(robustness), pd.DataFrame(cluster_rows), pd.DataFrame(scenarios)


def temporal_proxy(players):
    """One-period player retrieval: can a historical profile retrieve its next-season
    counterpart? Candidate future features are used solely as evaluation labels.
    This is identity/profile persistence, not scouting quality or transfer relevance.
    """
    rows = []
    seasons = sorted(players.season.unique())
    for past, future in zip(seasons, seasons[1:]):
        if int(future[:4]) != int(past[:4]) + 1:
            continue
        train = players[players.season <= past].copy()
        previous = players[players.season == past].copy()
        test = players[players.season == future].copy()
        if test.entity_id.duplicated().any() or previous.entity_id.duplicated().any():
            raise ValueError('Aggregate club stints before temporal evaluation')
        rec = PlayerRecommender().fit(train)
        A, B = rec.transform(previous), rec.transform(test)
        common = sorted(set(previous.entity_id) & set(test.entity_id))
        if not common:
            continue
        features = rec.artifacts.feature_cols
        cols = {name: features.index(name) for name in features}
        predictions = {'cosine_profile': (A @ B.T)/(np.maximum(np.linalg.norm(A,axis=1)[:,None]*np.linalg.norm(B,axis=1),1e-12)),
                       'euclidean_profile': -np.linalg.norm(A[:,None,:]-B[None,:,:],axis=2),
                       'random': np.random.default_rng(RANDOM_SEED).random((len(A),len(B)))}
        if 'gls_p90' in cols:
            predictions['goals_only'] = -abs(A[:,None,cols['gls_p90']]-B[None,:,cols['gls_p90']])
        for method, score in predictions.items():
            rank_values = []
            for entity in common:
                i = np.flatnonzero(previous.entity_id.to_numpy() == entity)[0]
                target = np.flatnonzero(test.entity_id.to_numpy() == entity)[0]
                order = np.argsort(-score[i], kind='stable')
                rank_values.append(int(np.flatnonzero(order == target)[0])+1)
            rows.append(dict(train_through=past, evaluation_season=future, method=method,
                             queries=len(common), candidate_count=len(test),
                             recall_at_5=float(np.mean(np.array(rank_values)<=5)),
                             mrr=float(np.mean(1/np.array(rank_values)))))
    return pd.DataFrame(rows, columns=['train_through','evaluation_season','method','queries','candidate_count','recall_at_5','mrr'])
