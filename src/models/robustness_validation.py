"""Post-hoc diagnostics on fixed real-data models, without holdout tuning.

Person-block bootstraps retain all observed seasons of a sampled identity.
Bootstrap copies are fitting weights, not new football observations. Reported
stability is conditional on the archive cohort and the previously selected k.
"""
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.linalg import subspace_angles
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist, jensenshannon
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from src.features.styles import affinity_scores, measured_weight_fraction
from src.models.experiments import _transformed_scores


def person_block_indices(players, rng):
    """Draw people with replacement, retaining every season row per draw."""
    if players.entity_id.isna().any():
        raise ValueError('Person-block bootstrap requires nonmissing identities')
    identities = sorted(players.entity_id.unique())
    blocks = {identity: np.flatnonzero(players.entity_id.eq(identity)) for identity in identities}
    drawn = rng.choice(identities, size=len(identities), replace=True)
    return np.concatenate([blocks[identity] for identity in drawn]), set(drawn)


def pca_alignment(base_pca, other_pca, base_scale, other_scale):
    """Align score directions in the original training-standardized coordinates.

    x_other = x_base * base_scale/other_scale + a translation. Translation
    changes centering, not directions. Sign and component order are arbitrary;
    principal angles compare the entire subspace even when axes rotate.
    """
    base = base_pca.components_
    other = other_pca.components_ * (np.asarray(base_scale)/np.asarray(other_scale))
    other = other/np.linalg.norm(other, axis=1, keepdims=True)
    rows, cols = linear_sum_assignment(-np.abs(base @ other.T))
    components = [dict(component=int(i+1), matched_component=int(j+1),
                       absolute_loading_cosine=float(abs(base[i] @ other[j]))) for i, j in zip(rows, cols)]
    subspaces = []
    for width in sorted(set([min(2, len(base)), len(base)])):
        angles = np.rad2deg(subspace_angles(base[:width].T, other[:width].T))
        subspaces.append(dict(dimensions=width, maximum_angle_degrees=float(angles.max()),
                              mean_angle_degrees=float(angles.mean())))
    return components, subspaces


def _top_ids(gallery, scores, position, exclude_entity=None, n=5):
    mask = gallery.pos_main.eq(position).to_numpy() & np.isfinite(scores)
    if exclude_entity is not None:
        mask &= gallery.entity_id.ne(exclude_entity).to_numpy()
    indexes = np.flatnonzero(mask)
    indexes = indexes[np.argsort(-scores[indexes], kind='stable')[:n]]
    return gallery.iloc[indexes].entity_id.tolist()


def _jaccard(left, right):
    left, right = set(left), set(right)
    return len(left & right)/len(left | right) if left or right else np.nan


def resampling_validation(rec, trials=30, seed=42):
    if trials < 2:
        raise ValueError('At least two bootstrap trials required')
    players = rec.players
    cols = rec.artifacts.feature_cols
    if players.duplicated(['entity_id', 'league', 'season']).any():
        raise ValueError('Bootstrap input must have one player/league/season observation')
    gallery = players[players.season.eq(players.season.max())].sort_values('entity_id').reset_index(drop=True)
    if gallery.entity_id.duplicated().any():
        raise ValueError('Historical gallery requires unique identities')
    positions = [p for p in ['DF', 'MF', 'FW'] if gallery.pos_main.eq(p).sum() >= 6]
    references = pd.DataFrame([gallery[gallery.pos_main.eq(p)].sort_values(
        ['minutes', 'entity_id'], ascending=[False, True]).iloc[0] for p in positions])
    if references.empty:
        raise ValueError('Insufficient position-specific gallery')
    B = rec.transform(gallery)
    A = rec.transform(references)
    method = getattr(rec, 'neighbor_method', 'cosine_profile')
    original_neighbors = _transformed_scores(rec, A, B)[method]
    original_styles = ['posesion', 'presion_alta', 'vertical', 'contraataque',
                       'solidez_defensiva', 'desborde_banda']
    styles = {style: measured_weight_fraction(style, cols) for style in original_styles}
    supported = [style for style, coverage in styles.items() if coverage >= .6]
    original_styles = {style: affinity_scores(B, style, cols) for style in supported}
    shortlist_rows, overlap_rows = [], []
    for position in positions:
        lists = {style: _top_ids(gallery, scores, position) for style, scores in original_styles.items()}
        for style, ids in lists.items():
            for rank, identity in enumerate(ids, 1):
                index = gallery.index[gallery.entity_id.eq(identity)][0]
                row = gallery.loc[index]
                shortlist_rows.append(dict(style=style, position=position, rank=rank,
                    entity_id=identity, player=row.player, season=row.season, team=row.team,
                    measured_weight_fraction=styles[style], affinity=float(original_styles[style][index]),
                    interpretation='Expert-weighted descriptive style; no relevance label or budget'))
        for i, left in enumerate(supported):
            for right in supported[i+1:]:
                overlap_rows.append(dict(position=position, style_left=left, style_right=right,
                                         top5_jaccard=_jaccard(lists[left], lists[right])))
    rng = np.random.default_rng(seed)
    clusters, loadings, subspaces, variances, ranking, spectra = [], [], [], [], [], []
    def spectrum(X, trial):
        eigenvalues = np.linalg.eigvalsh(np.cov(X, rowvar=False))[::-1]
        for i, value in enumerate(eigenvalues):
            spectra.append(dict(trial=trial, component=i+1, eigenvalue=float(value),
                gap_to_next=float(value-eigenvalues[i+1]) if i+1 < len(eigenvalues) else np.nan,
                scope='original_development' if trial == -1 else 'bootstrap_development'))
    spectrum(rec.X, -1)
    original_labels = rec.artifacts.kmeans.predict(rec.X)
    for trial in range(trials):
        indexes, sampled_people = person_block_indices(players, rng)
        sample = players.iloc[indexes][cols]
        imputer, scaler = SimpleImputer(strategy='median'), StandardScaler()
        X = scaler.fit_transform(imputer.fit_transform(sample))
        if X.shape[1] != len(cols) or len(np.unique(X, axis=0)) < rec.artifacts.kmeans.n_clusters:
            raise ValueError('Degenerate bootstrap: feature or cluster coverage lost; do not silently skip')
        pca = PCA(n_components=rec.artifacts.pca.n_components_, random_state=seed).fit(X)
        spectrum(X, trial)
        kmeans = KMeans(n_clusters=rec.artifacts.kmeans.n_clusters, n_init=10,
                        random_state=seed+trial).fit(X)
        ref = scaler.transform(imputer.transform(players[cols]))
        labels = kmeans.predict(ref)
        oob = ~players.entity_id.isin(sampled_people).to_numpy()
        oob_valid = oob.sum() >= 2 and len(np.unique(labels[oob])) > 1 and len(np.unique(original_labels[oob])) > 1
        # Convert centres back to the common ORIGINAL standardized feature space.
        centers = rec.artifacts.scaler.transform(scaler.inverse_transform(kmeans.cluster_centers_))
        distances = cdist(rec.artifacts.kmeans.cluster_centers_, centers)
        ii, jj = linear_sum_assignment(distances)
        clusters.append(dict(trial=trial, sampled_rows=len(indexes), sampled_unique_people=len(sampled_people),
            reference_rows=len(players), out_of_bag_rows=int(oob.sum()),
            out_of_bag_people=int(players.loc[oob, 'entity_id'].nunique()),
            adjusted_rand_reference=float(adjusted_rand_score(original_labels, labels)),
            adjusted_rand_out_of_bag=float(adjusted_rand_score(original_labels[oob], labels[oob])) if oob_valid else np.nan,
            out_of_bag_status='measured' if oob_valid else 'insufficient_cluster_diversity',
            matched_centroid_distance_mean=float(distances[ii, jj].mean())))
        component_rows, space_rows = pca_alignment(rec.artifacts.pca, pca,
            rec.artifacts.scaler.scale_, scaler.scale_)
        loadings.extend(dict(trial=trial, **row) for row in component_rows)
        subspaces.extend(dict(trial=trial, **row) for row in space_rows)
        variances.extend(dict(trial=trial, component=i+1, explained_variance=float(value),
                              cumulative_variance=float(pca.explained_variance_ratio_[:i+1].sum()))
                         for i, value in enumerate(pca.explained_variance_ratio_))
        boot = SimpleNamespace(artifacts=SimpleNamespace(feature_cols=cols, pca=pca, kmeans=kmeans))
        Anew = scaler.transform(imputer.transform(references[cols]))
        Bnew = scaler.transform(imputer.transform(gallery[cols]))
        neighbors = _transformed_scores(boot, Anew, Bnew)[method]
        for i, query in references.reset_index(drop=True).iterrows():
            old = _top_ids(gallery, original_neighbors[i], query.pos_main, query.entity_id)
            new = _top_ids(gallery, neighbors[i], query.pos_main, query.entity_id)
            ranking.append(dict(trial=trial, kind='neighbor', method=method, position=query.pos_main,
                reference=query.player, top5_jaccard=_jaccard(old, new), gallery_season=gallery.season.iloc[0]))
        for style in supported:
            scores = affinity_scores(Bnew, style, cols)
            for position in positions:
                ranking.append(dict(trial=trial, kind='style', method=style, position=position,
                    reference='expert_weight_vector',
                    top5_jaccard=_jaccard(_top_ids(gallery, original_styles[style], position),
                                         _top_ids(gallery, scores, position)), gallery_season=gallery.season.iloc[0]))
    return dict(cluster_bootstrap=pd.DataFrame(clusters), pca_loading_bootstrap=pd.DataFrame(loadings),
        pca_subspace_bootstrap=pd.DataFrame(subspaces), pca_variance_bootstrap=pd.DataFrame(variances),
        pca_eigenvalues=pd.DataFrame(spectra),
        ranking_bootstrap=pd.DataFrame(ranking), style_shortlists=pd.DataFrame(shortlist_rows),
        style_overlap=pd.DataFrame(overlap_rows), style_coverage=pd.DataFrame([
            dict(style=style, measured_weight_fraction=value, supported=value >= .6) for style, value in styles.items()]))


def position_retrieval(details, bootstrap_trials=500, seed=42):
    """Report seasonal/position slices, pairing baseline by explicit identity."""
    keys = ['phase', 'query_season', 'evaluation_season', 'position']
    if details.duplicated(keys+['method', 'entity_id']).any():
        raise ValueError('Duplicate retrieval queries')
    if details[keys+['entity_id']].isna().any().any():
        raise ValueError('Missing retrieval identity or subgroup')
    rows = []
    for group_keys, subgroup in details.groupby(keys, sort=True):
        baseline = subgroup[subgroup.method.eq('goals_assists')].set_index('entity_id')
        for method, group in subgroup.groupby('method', sort=True):
            group = group.sort_values('entity_id').set_index('entity_id')
            if set(group.index) != set(baseline.index):
                raise ValueError('Each method must evaluate the same identities as its baseline')
            if group.candidate_count.nunique() != 1 or not group.candidate_count.eq(baseline.loc[group.index].candidate_count).all():
                raise ValueError('Inconsistent evaluation candidate universe')
            n = len(group)
            boot = np.random.default_rng(seed).integers(0, n, (bootstrap_trials, n))
            rr = group.reciprocal_rank.to_numpy()
            delta = rr-baseline.loc[group.index].reciprocal_rank.to_numpy()
            mrr_low, mrr_high = np.quantile(rr[boot].mean(axis=1), [.025, .975])
            delta_low, delta_high = np.quantile(delta[boot].mean(axis=1), [.025, .975])
            rows.append(dict(zip(keys, group_keys), method=method, queries=n,
                candidate_count=int(group.candidate_count.iloc[0]), mrr=float(rr.mean()),
                mrr_ci_low=float(mrr_low), mrr_ci_high=float(mrr_high),
                recall_at_5=float(group.recall_at_5.mean()), recall_at_10=float(group.recall_at_10.mean()),
                ndcg_at_10=float(group.ndcg_at_10.mean()),
                target_available_fraction=float(group.target_available.mean()),
                mrr_delta_goals_assists=float(delta.mean()), delta_ci_low=float(delta_low),
                delta_ci_high=float(delta_high), inference='post_hoc_conditional_subgroup_not_independent_confirmation'))
    return pd.DataFrame(rows)


def feature_drift(train, future, cols, scales):
    """Descriptive drift: observed rates, fixed training quantile bins; no tests."""
    rows = []
    for i, feature in enumerate(cols):
        a = train[feature].dropna().to_numpy()
        b = future[feature].dropna().to_numpy()
        if not len(a) or not len(b):
            raise ValueError('No observed values for drift analysis')
        edges = np.unique(np.quantile(a, np.arange(1, 10)/10))
        bins = np.r_[-np.inf, edges, np.inf]
        p = np.histogram(a, bins)[0]/len(a)
        q = np.histogram(b, bins)[0]/len(b)
        rows.append(dict(feature=feature, observed_train=len(a), observed_future=len(b),
            missing_train=len(train)-len(a), missing_future=len(future)-len(b), histogram_bins=len(bins)-1,
            mean_train=float(a.mean()), mean_future=float(b.mean()),
            mean_shift_training_sd=float((b.mean()-a.mean())/scales[i]),
            js_divergence=float(jensenshannon(p, q, base=2)**2)))
    return pd.DataFrame(rows)


def temporal_validation(rec, parts):
    """Freeze development transformations/centres for all later seasons."""
    if list(parts)[0] != 'train':
        raise ValueError('Temporal diagnostics must start with development data')
    last_season = None
    for part, cohort in parts.items():
        if cohort.empty or cohort.duplicated(['entity_id', 'season']).any():
            raise ValueError('Temporal diagnostics require unique, nonempty season cohorts')
        if last_season is not None and cohort.season.min() <= last_season:
            raise ValueError('Temporal diagnostic seasons overlap or run backwards')
        if part != 'train' and cohort.season.min() <= rec.players.season.max():
            raise ValueError('Future diagnostic cohort overlaps fitted model seasons')
        last_season = cohort.season.max()
    distribution, quality, drift, transitions = [], [], [], []
    previous = None
    for part, cohort in parts.items():
        for season, players in cohort.groupby('season', sort=True):
            players = players.sort_values('entity_id').copy()
            X = rec.transform(players)
            players['frozen_cluster'] = rec.artifacts.kmeans.predict(X)
            for (position, cluster), group in players.groupby(['pos_main', 'frozen_cluster']):
                distribution.append(dict(phase=part, season=season, position=position, cluster=cluster,
                    observations=len(group), position_fraction=len(group)/players.pos_main.eq(position).sum()))
            diversity = 1 < players.frozen_cluster.nunique() < len(players)
            quality.append(dict(phase=part, season=season, observations=len(players),
                silhouette=float(silhouette_score(X, players.frozen_cluster, sample_size=min(800, len(players)),
                                                 random_state=42)) if diversity else np.nan,
                status='measured' if diversity else 'insufficient_cluster_diversity'))
            if part != 'train':
                frame = feature_drift(parts['train'], players, rec.artifacts.feature_cols, rec.artifacts.scaler.scale_)
                drift.extend(dict(phase=part, season=season, **row) for row in frame.to_dict('records'))
            if previous is not None:
                old = previous[['entity_id', 'season', 'pos_main', 'frozen_cluster']]
                paired = old.merge(players[['entity_id', 'frozen_cluster']], on='entity_id',
                                   suffixes=('_previous', '_future'), validate='one_to_one')
                for (position, before, after), group in paired.groupby(['pos_main', 'frozen_cluster_previous', 'frozen_cluster_future']):
                    transitions.append(dict(phase=part, query_season=previous.season.iloc[0], evaluation_season=season,
                        position=position, cluster_previous=before, cluster_future=after,
                        returning_players=len(group),
                        position_returners=int(paired.pos_main.eq(position).sum())))
            previous = players
    return dict(cluster_distribution=pd.DataFrame(distribution), temporal_cluster_quality=pd.DataFrame(quality),
                feature_drift=pd.DataFrame(drift), cluster_transitions=pd.DataFrame(transitions))
