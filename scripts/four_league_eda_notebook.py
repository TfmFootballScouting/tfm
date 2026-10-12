"""Build and execute source-separated four-league EDA without model refits."""
from pathlib import Path
import json
import nbformat
from nbclient import NotebookClient
from src.config import ROOT
from src.data.provenance import sha256


def main():
    n=nbformat.v4.new_notebook()
    n.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}}
    md=nbformat.v4.new_markdown_cell;code=nbformat.v4.new_code_cell
    n.cells=[md('''# Four-league shots: cleaning, attacking EDA and identity review

This notebook analyzes real Understat data for Premier League, Bundesliga, Serie A and Ligue 1, 2020/21 through a partial September-2025 snapshot of 2025/26. It checks richer retained FBref-category exposure and creates conservative identity proposals. It does not refit the recommendation model or validate transfer success.

Raw source archives, current models and earlier experiments are preserved. Cross-source identities remain provisional, and normalized source rows remain local. Recorded shot-taking players are not a complete appearance/player universe.'''),code('''from pathlib import Path
import sys,json
ROOT=Path.cwd() if (Path.cwd()/'src').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
import pandas as pd
from IPython.display import display,Image
from src.data.provenance import sha256
folder=ROOT/'reports/four_league_preprocessing'
report=json.loads((folder/'preprocessing.json').read_text())
for path,info in report['outputs'].items():assert sha256(ROOT/path)==info['sha256']
shots=pd.read_parquet(ROOT/'data/processed/real/four_league_clean_shots.parquet')
players=pd.read_parquet(ROOT/'data/processed/real/four_league_player_seasons.parquet')
print({k:report[k] for k in ['shot_events','attempts_excluding_own_goals','own_goal_events','player_seasons','player_club_seasons']})'''),md('''## 1. Quality and missingness

All required shot IDs, player IDs/names, dates, teams, coordinates and xG are present in the retained extraction. Coordinates and xG are bounded [0,1]; minutes are source match-clock values, including stoppage time. Alternate source home/away fields are reconciled conservatively in the acquisition step, with conflicts tracked rather than guessed.

Own-goal events are retained, but excluded from attempts, goals and summed shooting xG. No missing values are filled with zero. No observations are removed solely because their xG or finishing residual is unusual.'''),code('''display(pd.read_csv(folder/'quality.csv'))
display(shots[['player','source_player_id','shot_date','team','X','Y','xG','minute']].isna().sum().rename('missing'))
display(shots[['X','Y','xG','minute']].describe())
display(pd.read_csv(folder/'outcomes.csv').groupby('result').events.sum().sort_values(ascending=False))'''),md('''## 2. Season coverage and fair descriptive cohorts

All 2025/26 data is partial. Bundesliga 2024/25 is missing one expected match, and Serie A is missing six. Raw/clean tables preserve these cohorts and their coverage flags; comparisons below use completed seasons with the expected match count and at least 20 observed attempts per player.

This support rule is descriptive, not an optimal threshold or a chronological ML validation split. Match-count agreement does not independently guarantee every shot was recorded. There are no verified player-minute denominators here, so **no per-90 shot metrics or appearance counts are fabricated**.'''),code('''coverage=pd.read_csv(ROOT/'reports/four_league_acquisition/coverage.csv')
display(coverage[coverage.source.eq('understat_worldfootballr')][['league','season','rows','matches','expected_schedule_matches','status']])
cohort=players[~players.partial_season & players.observed_schedule_fraction.eq(1) & players.shots.ge(20)].copy()
assert len(cohort)==report['completed_full_schedule_20_shot_eda_rows']
display(cohort.groupby('league').agg(player_seasons=('source_player_id','size'),median_shots=('shots','median'),median_xg_per_shot=('xg_per_shot','median')))
print('Descriptive cohort rows:',len(cohort))'''),md('''## 3. Shot maps, distributions and expected-goals residuals

Map examples are selected by observed non-penalty shot support within the eligible league cohorts, not by future outcomes or market prices. Coordinates are the source's normalized X/Y values, not observed pitch meters; no map depicts a player's physical tracking trajectory.

Goals-minus-xG measures observed over/underperformance against the source's expected-goals estimates. Sample size, chance mix and stochastic conversion affect this residual. A large residual does not establish stable finishing talent. Shots, goals and xG share volume information, so correlations are not independent evidence of predictive ability.'''),code('''display(Image(filename=str(folder/'shot_maps.png')))
display(Image(filename=str(folder/'attacking_eda.png')))
display(cohort[['shots','goals','xg','xg_per_shot','conversion_rate','goals_minus_xg']].describe().round(3))
display(pd.read_csv(folder/'correlations.csv',index_col=0).round(3))
display(pd.read_csv(folder/'situations.csv').groupby('situation').agg(events=('events','sum')))
display(pd.read_csv(folder/'shot_types.csv').groupby('shotType').events.sum())'''),md('''## 4. Season-specific FBref identity proposals

Use the same league, season, conservatively normalized club and exact normalized name. Explicit observed club spellings (for example Manchester United/Manchester Utd and Bayer Leverkusen/Leverkusen) are recorded in `club_aliases.csv`; no fuzzy player matching is used. Reject same-season one-to-many identities. Current/future season observations cannot supply evidence for an earlier season because the matching keys include the season.

These proposals lack independent shared DOB evidence or an approved crosswalk. They are a **review queue**, not canonical merged training records. Name differences, club spelling differences, non-shooters and different source coverage explain some unresolved players. A shot taking-player's identity may be supported in one season but unresolved in another; counts below are player-season observations, not globally unique reviewed people.'''),code('''identities=pd.read_csv(folder/'identity_coverage.csv')
display(identities)
print('Supported player-season proposals:',int(identities.supported_identity_candidates.sum()))
print('Approved cross-source identities:',report['approved_cross_source_identities'])
assert report['approved_cross_source_identities']==0
review=pd.read_parquet(ROOT/'data/processed/real/four_league_identity_candidates.parquet')
assert review.identity_match_status.eq('provisional_not_reviewed').all()
assert not review.model_use_eligible.any()'''),md('''## 5. Richer FBref features and next integration boundary

The acquired category tables retain passing distances/lengths, key and progressive passing, penalty-area entries, tackle/block zones, touches and take-ons. Exposure compatibility must be checked before deriving per-90 metrics or combining categories. An incompatible category value is retained audit evidence, not a valid complete-season feature.

Avoid filling an unavailable FBref defensive category with Understat shooting values. A combined dashboard should preserve source identities and distinguish confirmed observations, missing categories and provisional cross-source links. Recruitment context and reported valuations remain separately restricted review inputs.'''),code('''advanced=pd.read_csv(folder/'advanced_feature_eligibility.csv')
display(advanced.groupby(['category','season']).agg(rows=('rows','sum'),compatible_rows=('valid_exposure_rows','sum')))
display(advanced[advanced.valid_exposure_rows.lt(advanced.rows)][['league','season','category','rows','valid_exposure_rows']])
print('Current recommender refitted:',report['current_model_refitted'])
assert not report['current_model_refitted']'''),md('''## Interpretation and decisions

Use these outputs for source-specific shot maps, attacking descriptions and a scoped player-development dashboard. Preserve all partial/incomplete cohorts with explicit flags; exclude them from full-season descriptive comparisons. Show shot support and avoid unsupported per-90 denominators or causal/transfer-success claims. Identity review is the prerequisite for attaching Understat metrics to a FBref recommendation, not a reason to fabricate identifiers or silently relax matching.

Reproduce the data stage with `python -m scripts.four_league_preprocessing` and this notebook with `python -m scripts.four_league_eda_notebook`. Private source tables and identity rows are not redistributed in Git.''')]
    NotebookClient(n,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute()
    path=ROOT/'notebooks/13_four_league_shot_eda.ipynb';nbformat.write(n,path)
    cells=[c for c in n.cells if c.cell_type=='code']
    assert all(c.execution_count is not None for c in cells)
    assert not any(o.output_type=='error' for c in cells for o in c.outputs)
    evidence={'notebook':str(path.relative_to(ROOT)),'sha256':sha256(path),'executed_code_cells':len(cells),'errors':0,'generator_sha256':sha256(Path(__file__))}
    (ROOT/'reports/four_league_preprocessing/notebook_execution.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))


if __name__=='__main__':main()
