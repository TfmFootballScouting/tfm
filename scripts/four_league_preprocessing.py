"""Real-data shot cleaning/EDA and conservative, season-specific identity proposals."""
from datetime import datetime,timezone
from pathlib import Path
import json,subprocess
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.config import ROOT
from src.data.provenance import sha256
from src.data.matching import normalize_name
from src.data.identity import club_key

FOLDER=ROOT/'reports/four_league_preprocessing'
OUT=ROOT/'data/processed/real'
KEYS=['league','season','source_player_id']
# Explicit observed spelling equivalents, scoped by league; never fuzzy player matching.
CLUB_SPELLINGS=[('Bundesliga', 'Arminia Bielefeld', 'Arminia'), ('Bundesliga', 'Bayer Leverkusen', 'Leverkusen'), ('Bundesliga', 'Borussia Dortmund', 'Dortmund'), ('Bundesliga', 'Borussia M.Gladbach', 'Gladbach'), ('Bundesliga', "M'Gladbach", 'Gladbach'), ('Bundesliga', 'Darmstadt', 'Darmstadt 98'), ('Bundesliga', 'Eintracht Frankfurt', 'Eint Frankfurt'), ('Bundesliga', 'FC Cologne', 'Köln'), ('Bundesliga', 'FC Heidenheim', 'Heidenheim'), ('Bundesliga', 'Greuther Fuerth', 'Greuther Fürth'), ('Bundesliga', 'Hertha Berlin', 'Hertha BSC'), ('Bundesliga', 'RasenBallsport Leipzig', 'RB Leipzig'), ('Bundesliga', 'VfB Stuttgart', 'Stuttgart'), ('Premier League', 'Ipswich', 'Ipswich Town'), ('Premier League', 'Leeds', 'Leeds United'), ('Premier League', 'Leicester', 'Leicester City'), ('Premier League', 'Luton', 'Luton Town'), ('Premier League', 'Manchester United', 'Manchester Utd'), ('Premier League', 'Newcastle United', 'Newcastle Utd'), ('Premier League', 'Norwich', 'Norwich City'), ('Premier League', 'Nottingham Forest', "Nott'ham Forest"), ('Premier League', 'Sheffield United', 'Sheffield Utd'), ('Premier League', 'West Bromwich Albion', 'West Brom'), ('Premier League', 'Wolverhampton Wanderers', 'Wolves'), ('Ligue 1', 'Paris Saint Germain', 'Paris S-G'), ('Serie A', 'AC Milan', 'Milan'), ('Serie A', 'Parma Calcio 1913', 'Parma'), ('Serie A', 'Verona', 'Hellas Verona')]
CLUB_KEYS={(league,club_key(source)):club_key(target) for league,source,target in CLUB_SPELLINGS}


def summarize_shots(shots,by):
    f=shots.copy()
    f['attempt']=~f.result.eq('OwnGoal')
    f['goal']=f.result.eq('Goal')
    f['own_goal']=f.result.eq('OwnGoal')
    f['non_penalty_attempt']=f.attempt & f.situation.ne('Penalty')
    f['non_penalty_goal']=f.goal & f.situation.ne('Penalty')
    f['attempt_xg']=f.xG.where(f.attempt,0)
    f['non_penalty_xg']=f.xG.where(f.non_penalty_attempt,0)
    f['on_target']=f.result.isin(['Goal','SavedShot'])
    result=f.groupby(by,dropna=False).agg(
        player=('player',lambda s:s.mode().iloc[0]),source_shot_events=('shot_id','size'),
        shots=('attempt','sum'),goals=('goal','sum'),own_goal_events=('own_goal','sum'),
        shots_on_target=('on_target','sum'),xg=('attempt_xg','sum'),
        non_penalty_shots=('non_penalty_attempt','sum'),non_penalty_goals=('non_penalty_goal','sum'),
        non_penalty_xg=('non_penalty_xg','sum'),matches_with_shots=('match_id','nunique'),
        first_shot_date=('shot_date','min'),last_shot_date=('shot_date','max'),
        partial_season=('partial_season','any')).reset_index()
    result['xg_per_shot']=result.xg/result.shots.where(result.shots.gt(0))
    result['conversion_rate']=result.goals/result.shots.where(result.shots.gt(0))
    result['goals_minus_xg']=result.goals-result.xg
    result['source']='understat_worldfootballr'
    return result


def propose_links(shots,fbref):
    # Only the same league/season/club observations supply evidence; no future rows.
    left=shots[['league','season','source_player_id','player','team']].drop_duplicates().copy()
    right=fbref[['league','season','source_player_id','player','team']].drop_duplicates().copy()
    for frame in [left,right]:
        frame['name_key']=frame.player.map(normalize_name)
        frame['club_key']=[CLUB_KEYS.get((league,club_key(team)),club_key(team)) for league,team in zip(frame.league,frame.team)]
    keys=['league','season','name_key','club_key']
    left['left_identity_count']=left.groupby(keys).source_player_id.transform('nunique')
    right['right_identity_count']=right.groupby(keys).source_player_id.transform('nunique')
    pairs=left.merge(right,on=keys,how='inner',suffixes=('_understat','_fbref')).drop_duplicates()
    pairs['one_to_one_name_club_season']=(pairs.left_identity_count.eq(1)&pairs.right_identity_count.eq(1))
    # Also reject an entity proposed to several counterpart IDs within a season.
    a=pairs.groupby(['league','season','source_player_id_understat']).source_player_id_fbref.transform('nunique')
    b=pairs.groupby(['league','season','source_player_id_fbref']).source_player_id_understat.transform('nunique')
    pairs['supported_review_candidate']=pairs.one_to_one_name_club_season & a.eq(1) & b.eq(1)
    pairs['identity_match_status']='provisional_not_reviewed'
    pairs['evidence']='exact_normalized_name_and_club_same_league_same_season_no_DOB'
    pairs['model_use_eligible']=False
    return pairs


def run():
    FOLDER.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
    acquisition=json.loads((ROOT/'reports/four_league_acquisition/acquisition.json').read_text())
    inputs={};parts=[]
    for name,info in acquisition['outputs'].items():
        assert sha256(ROOT/name)==info['sha256'];inputs[name]=info['sha256']
        if '/understat_' in name:parts.append(pd.read_parquet(ROOT/name))
    shots=pd.concat(parts,ignore_index=True).sort_values(['league','season','shot_date','match_id','shot_id']).reset_index(drop=True)
    assert not shots.duplicated(['league','shot_id']).any()
    shots['quality_valid']=shots[['X','Y','xG']].apply(lambda c:c.between(0,1)).all(axis=1)&shots.minute.between(0,130)&shots.team_side_resolved&shots[['shot_id','source_player_id','player','shot_date','team','result']].notna().all(axis=1)
    assert shots.quality_valid.all(),'Invalid rows require quarantine, not silent imputation'
    shots['observation_id']='understat:'+shots.shot_id.astype(str)
    coverage=pd.read_csv(ROOT/'reports/four_league_acquisition/coverage.csv')
    coverage=coverage[coverage.source.eq('understat_worldfootballr')].copy()
    coverage['observed_schedule_fraction']=coverage.matches/coverage.expected_schedule_matches
    shots=shots.merge(coverage[['league','season','observed_schedule_fraction','status']].rename(columns={'status':'season_coverage_status'}),on=['league','season'],validate='many_to_one')
    seasons=summarize_shots(shots,KEYS)
    clubs=summarize_shots(shots,KEYS+['team'])
    seasons=seasons.merge(coverage[['league','season','observed_schedule_fraction','status']].rename(columns={'status':'season_coverage_status'}),on=['league','season'],validate='many_to_one')
    eligible=seasons[~seasons.partial_season & seasons.observed_schedule_fraction.eq(1)&seasons.shots.ge(20)].copy()
    pipeline=json.loads((ROOT/'reports/five_league_pipeline/pipeline.json').read_text())
    item=pipeline['outputs']['player_club_seasons'];assert sha256(ROOT/item['path'])==item['sha256'];inputs[item['path']]=item['sha256']
    fbref=pd.read_parquet(ROOT/item['path']);fbref=fbref[fbref.league.isin(acquisition['leagues'])]
    pairs=propose_links(shots,fbref)
    represented=pairs[pairs.supported_review_candidate][['league','season','source_player_id_understat']].drop_duplicates()
    support=seasons.merge(represented.assign(supported=True),left_on=KEYS,right_on=['league','season','source_player_id_understat'],how='left',validate='one_to_one')
    matching=support.groupby(['league','season']).agg(shot_taking_players=('source_player_id','size'),supported_identity_candidates=('supported','count')).reset_index()
    matching['unresolved_players']=matching.shot_taking_players-matching.supported_identity_candidates
    matching['approved_identities']=0
    pd.DataFrame(CLUB_SPELLINGS,columns=['league','source_spelling','canonical_spelling']).to_csv(FOLDER/'club_aliases.csv',index=False)
    matching.to_csv(FOLDER/'identity_coverage.csv',index=False)
    pairs.to_csv(FOLDER/'identity_review_queue.csv',index=False)
    quality=shots.groupby(['league','season']).agg(events=('shot_id','size'),valid_events=('quality_valid','sum'),players=('source_player_id','nunique'),own_goal_events=('result',lambda s:int(s.eq('OwnGoal').sum()))).reset_index()
    quality.to_csv(FOLDER/'quality.csv',index=False)
    shots.groupby(['league','season','result']).size().rename('events').reset_index().to_csv(FOLDER/'outcomes.csv',index=False)
    shots.groupby(['league','season','situation']).agg(events=('shot_id','size'),mean_xg=('xG','mean')).reset_index().to_csv(FOLDER/'situations.csv',index=False)
    shots.groupby(['league','season','shotType']).size().rename('events').reset_index().to_csv(FOLDER/'shot_types.csv',index=False)
    distributions=eligible.groupby('league')[['shots','goals','xg','xg_per_shot','goals_minus_xg']].describe()
    distributions.to_csv(FOLDER/'player_distributions.csv')
    eligible[['shots','goals','xg','xg_per_shot','conversion_rate','goals_minus_xg']].corr().to_csv(FOLDER/'correlations.csv')
    # Select maps using observed non-penalty shot support, not future targets or price.
    examples=eligible.sort_values(['league','non_penalty_shots','source_player_id'],ascending=[True,False,True]).groupby('league').head(1)
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for ax,row in zip(axes.flat,examples.itertuples()):
        g=shots[shots.league.eq(row.league)&shots.season.eq(row.season)&shots.source_player_id.eq(row.source_player_id)&shots.result.ne('OwnGoal')]
        ax.scatter(g.X,g.Y,s=15+g.xG*140,c=g.xG,cmap='viridis',alpha=.6,vmin=0,vmax=1)
        goals=g[g.result.eq('Goal')];ax.scatter(goals.X,goals.Y,s=20+goals.xG*140,facecolors='none',edgecolors='red')
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Source normalized X',ylabel='Source normalized Y',title=f'{row.player} | {row.league} {row.season}')
    fig.suptitle('Observed shots: size/color = xG; red outline = goal (no per-90 claims)');fig.tight_layout();fig.savefig(FOLDER/'shot_maps.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for league,g in eligible.groupby('league'):
        axes[0].scatter(g.xg,g.goals,s=10,alpha=.3,label=league)
    limit=max(eligible.goals.max(),eligible.xg.max());axes[0].plot([0,limit],[0,limit],'k--');axes[0].set(xlabel='Observed xG',ylabel='Goals',title='Completed, full-match-count cohorts; 20+ attempts');axes[0].legend(fontsize=7)
    axes[1].hist(eligible.goals_minus_xg,bins=40);axes[1].set(xlabel='Goals minus xG',ylabel='Player-season count',title='Descriptive residual, not proven finishing talent')
    fig.tight_layout();fig.savefig(FOLDER/'attacking_eda.png',dpi=140);plt.close(fig)
    fbcoverage=pd.read_csv(ROOT/'reports/four_league_acquisition/coverage.csv')
    advanced=fbcoverage[fbcoverage.source.eq('fbref_worldfootballr')].copy()
    advanced['exposure_eligible_fraction']=advanced.valid_exposure_rows/advanced.rows.where(advanced.rows.gt(0))
    advanced.to_csv(FOLDER/'advanced_feature_eligibility.csv',index=False)
    dictionary=[];outputs={}
    descriptions={'shots':'Attempts excluding OwnGoal source events; no unseen minutes denominator','matches_with_shots':'Matches where this player has a shot event; not appearances','xg':'Sum of xG for observed attempts, excluding own-goal events','xg_per_shot':'Mean expected goals per observed attempt, not per 90','goals_minus_xg':'Observed goals minus observed xG; descriptive, not a validated skill estimate','observed_schedule_fraction':'Observed distinct match IDs divided by expected league schedule; not independent event completeness','supported_review_candidate':'Unique exact normalized name+club+league+season proposal; not reviewed identity approval','model_use_eligible':'False for cross-source proposals; not integrated into model training'}
    for key,frame in [('clean_shots',shots),('player_seasons',seasons),('player_club_seasons',clubs),('identity_candidates',pairs)]:
        path=OUT/f'four_league_{key}.parquet';frame.to_parquet(path,index=False)
        outputs[str(path.relative_to(ROOT))]={'rows':len(frame),'sha256':sha256(path)}
        for col in frame:dictionary.append({'table':key,'field':col,'dtype':str(frame[col].dtype),'definition':descriptions.get(col,'Inherited source field or directly observed aggregate; see acquisition dictionary'),'missing':int(frame[col].isna().sum())})
    pd.DataFrame(dictionary).to_csv(FOLDER/'dictionary.csv',index=False)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'script_sha256':sha256(Path(__file__)),'inputs_sha256':inputs,'outputs':outputs,'shot_events':len(shots),'attempts_excluding_own_goals':int((~shots.result.eq('OwnGoal')).sum()),'own_goal_events':int(shots.result.eq('OwnGoal').sum()),'player_seasons':len(seasons),'player_club_seasons':len(clubs),'completed_full_schedule_20_shot_eda_rows':len(eligible),'supported_player_season_identity_candidates':int(matching.supported_identity_candidates.sum()),'proposed_stint_pairs':len(pairs),'approved_cross_source_identities':0,'current_model_refitted':False,'limits':['Shot-taking players are not a complete player/appearance universe. No per-90 statistics inferred without verified minutes.','OwnGoal events remain in cleaned source data but are excluded from attempts/goals/xG aggregates.','2025/26 and incomplete 2024/25 match cohorts remain source tables but are excluded from completed full-schedule EDA comparisons.','Exact name+club+league+season links remain provisional without independent DOB or approved crosswalk.','No source ID is silently merged into a FBref canonical identity. No Transfermarkt values or fees enter this preprocessing.','Goals-minus-xG is noisy and not a validated skill or transfer-success measure.']}
    (FOLDER/'preprocessing.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['shot_events','attempts_excluding_own_goals','own_goal_events','player_seasons','player_club_seasons','completed_full_schedule_20_shot_eda_rows','supported_player_season_identity_candidates','proposed_stint_pairs']},indent=2))


if __name__=='__main__':run()
