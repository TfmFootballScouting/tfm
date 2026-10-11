"""Real-data quality analysis and scientific plots; no fitted models or downloads."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.config import ROOT, FEATURE_COLS
from src.data.provenance import sha256
from src.features.requirements import MODEL_CANDIDATE_FEATURES


def load_verified_tables():
    manifest = json.loads((ROOT/'reports/collected_preprocessing.json').read_text())
    tables = {}
    for name, item in manifest['outputs'].items():
        path = ROOT / item['path']
        if sha256(path) != item['sha256']:
            raise ValueError(f'Processed dataset changed without updating provenance: {name}')
        tables[name] = pd.read_parquet(path)
    return manifest, tables


def save_plot(name, figure):
    figure.tight_layout()
    figure.savefig(ROOT/'reports'/name, dpi=140, bbox_inches='tight')
    plt.close(figure)


def run():
    manifest, tables = load_verified_tables()
    players = tables['collected_player_seasons']
    eligible = tables['collected_baseline_candidates']
    training = eligible[eligible.experiment_split.eq('train')]
    core_training = tables['collected_tactical_candidates'].query("core_proxy_split == 'train'")
    coverage = pd.read_csv(ROOT/'reports/mandatory_feature_coverage.csv')
    features = [c for c in MODEL_CANDIDATE_FEATURES + ['ga_p90'] if c != 'xa_p90']
    availability = coverage[coverage.feature.isin(features)].assign(observed_fraction=lambda d: 1-d.missing_fraction)
    matrix = availability.pivot(index='season',columns='feature',values='observed_fraction')[features]
    fig, ax = plt.subplots(figsize=(13,4))
    sns.heatmap(matrix, vmin=0, vmax=1, annot=True, fmt='.2f', cmap='YlGnBu', ax=ax)
    ax.set_title('Observed feature fractions — all player seasons; 2025/26 is partial')
    save_plot('collected_feature_availability.png', fig)

    fig, axes = plt.subplots(2,3,figsize=(13,7))
    for column, ax in zip(['minutes','age','gls_p90','ast_p90','sh_p90','xg_p90'],axes.flat):
        sns.histplot(training[column].dropna(),bins=30,ax=ax)
        ax.set_title(column)
    fig.suptitle('Development seasons 2020/21–2022/23; outfield players with 450+ minutes',y=1.03)
    save_plot('collected_distributions.png',fig)

    corr_features = [c for c in MODEL_CANDIDATE_FEATURES if core_training[c].notna().any() and core_training[c].nunique()>1]
    correlations = core_training[corr_features].corr(method='spearman')
    correlations.to_csv(ROOT/'reports/collected_training_correlations.csv')
    fig, ax = plt.subplots(figsize=(11,9))
    sns.heatmap(correlations,center=0,vmin=-1,vmax=1,cmap='vlag',ax=ax)
    ax.set_title('Spearman correlations, 2020/21–2021/22 development only; redundant G+A excluded')
    save_plot('collected_training_correlations.png',fig)

    comparisons = eligible.groupby(['season','pos_main']).agg(
        rows=('player','size'),median_minutes=('minutes','median'),
        median_goals_p90=('gls_p90','median'),median_assists_p90=('ast_p90','median'),
        median_shots_p90=('sh_p90','median'),median_interceptions_p90=('int_p90','median'),
        interceptions_observed=('int_p90','count')).reset_index()
    comparisons.to_csv(ROOT/'reports/collected_position_comparisons.csv',index=False)
    fig, axes = plt.subplots(1,3,figsize=(13,4))
    for column, ax in zip(['median_goals_p90','median_shots_p90','median_interceptions_p90'],axes):
        sns.heatmap(comparisons.pivot(index='season',columns='pos_main',values=column),annot=True,fmt='.2f',cmap='YlGnBu',ax=ax)
        ax.set_title(column)
    save_plot('collected_position_comparisons.png',fig)

    seasons = players.groupby('season').agg(rows=('player','size'),
        minute_eligible=('minutes_eligible','sum'),historical_outfield_candidates=('historical_candidate','sum'),
        complete_core_outfield=('tactical_proxy_candidate','sum'),
        transferred_players=('club_count',lambda s:int(s.gt(1).sum()))).reset_index()
    seasons.to_csv(ROOT/'reports/collected_season_summary.csv',index=False)
    fig, ax = plt.subplots(figsize=(10,4))
    seasons.set_index('season')[['rows','historical_outfield_candidates','complete_core_outfield']].plot.bar(ax=ax)
    ax.set_title('Player-season coverage and eligibility; partial 2025/26 excluded from history')
    ax.set_ylabel('Observations')
    save_plot('collected_season_coverage.png',fig)

    shots = tables['collected_understat_shots']
    shot_coverage = shots.groupby('season').agg(recorded_events=('shot_id','size'),
        attacking_shots=('attacking_shot','sum'),own_goals=('own_goal','sum'),
        matches=('match_id','nunique'),first_date=('match_datetime','min'),last_date=('match_datetime','max')).reset_index()
    shot_coverage.to_csv(ROOT/'reports/collected_understat_coverage.csv',index=False)
    outliers = players[players.quality_outlier | players.quality_inconsistent_counts]
    outliers[['source_player_id','player','season','minutes','gls_p90','sh_p90','quality_outlier',
              'quality_inconsistent_counts','historical_candidate']].to_csv(ROOT/'reports/collected_outliers.csv',index=False)
    candidates = tables['identity_candidates']
    candidates.to_csv(ROOT/'reports/collected_identity_candidates.csv',index=False)
    vals = tables['collected_profiles_valuations']
    transfers = tables['collected_transfers']
    summary = dict(dataset_version=manifest['dataset_version'],
        player_club_rows=len(tables['collected_player_club_seasons']),player_season_rows=len(players),
        fbref_unique_players=int(players.source_player_id.nunique()),
        historical_baseline_candidates=len(eligible),historical_complete_core_candidates=len(tables['collected_tactical_candidates']),
        development_candidates=len(training),
        core_proxy_development_candidates=len(core_training),
        multi_club_seasons=int(players.club_count.gt(1).sum()),
        missing_ages=int(players.age.isna().sum()),
        missing_core_counts={c:int(players[c].isna().sum()) for c in FEATURE_COLS},
        outlier_flags=len(outliers),outliers_in_historical_candidates=int(outliers.historical_candidate.sum()),
        understat_shot_records=len(shots),understat_attacking_shots=int(shots.attacking_shot.sum()),
        understat_own_goals=int(shots.own_goal.sum()),understat_shooter_club_seasons=len(tables['collected_understat_shooters']),
        transfermarkt_profiles=len(vals),missing_market_values=int(vals.market_value_eur.isna().sum()),
        segunda_scorer_sample_rows=len(tables['collected_segunda_scorer_sample']),
        parsed_dobs=int(vals.date_of_birth.notna().sum()),parsed_heights=int(vals.height_cm.notna().sum()),
        transfer_records=len(transfers),potential_movement_groups=int(transfers.potential_movement_id.nunique()),
        unverified_zero_fees=int(transfers.fee_zero_unverified.sum()),missing_fees=int(transfers.fee_eur.isna().sum()),
        reviewed_identity_pairs=len(tables['identity_matches_approved']),candidate_identity_pairs=len(candidates),
        identity_birth_year_conflicts=int(candidates.status.eq('conflicting_birth_year').sum()),
        identity_ambiguous_pairs=int(candidates.ambiguous.sum()),
        eligible_historical_budget_records=0,raw_data_modified=False,model_trained=False,
        imputation_or_scaling_fitted=False,
        league_comparison='Unavailable: no complete real Segunda performance dataset; synthetic rows excluded',
        pressure_or_goalkeeper_metrics='Not collected; broad tactical labels remain proxies; GK excluded from outfield candidates')
    (ROOT/'reports/collected_eda.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return summary


if __name__ == '__main__':
    run()
