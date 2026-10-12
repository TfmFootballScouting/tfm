"""Prepare separate four-league source tables from checksum-pinned real archives."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,argparse,time
import requests
import numpy as np
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.data.source_rights import RESTRICTED
from scripts.worldfootballr_archive import ensure_snapshot,read_rds
from scripts.top_five_leagues import select_rows,KEYS
from scripts.salimt_history_audit import season_year

LEAGUES={'Premier League':'GB1','Bundesliga':'L1','Serie A':'IT1','Ligue 1':'FR1'}
UNDERSTAT={'Premier League':'EPL','Bundesliga':'Bundesliga','Serie A':'Serie_A','Ligue 1':'Ligue_1'}
FOLDER=ROOT/'reports/four_league_acquisition'
DEST=ROOT/'data/external/four_league_expansion'


def archive_frame(path):
    try:return read_rds(path)
    except UnicodeDecodeError:
        import rdata
        frame=rdata.conversion.convert(rdata.parser.parse_file(path),default_encoding='latin1')
        if not isinstance(frame,pd.DataFrame):raise ValueError('Expected a data frame')
        return frame,'rdata_encoding_aware_latin1_default'


def pinned_archive(record, download=False):
    path=ROOT/record['path']
    if not path.exists():
        if not download:raise FileNotFoundError(f"Missing archive: {path}; use --download")
        r=requests.get(record['url'],timeout=90);r.raise_for_status()
        assert __import__('hashlib').sha256(r.content).hexdigest()==record['sha256'],'Archive changed; expected checksum must not be replaced'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(r.content);time.sleep(3)
    assert sha256(path)==record['sha256']
    return path


def run(download=False,public_only=False):
    FOLDER.mkdir(exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    inputs={};outputs={};coverage=[];dictionary=[];problems=[];missing_fixtures=[]
    def save(frame,name,private=False):
        path=DEST/(name+'.parquet');frame.to_parquet(path,index=False)
        outputs[str(path.relative_to(ROOT))]={'rows':len(frame),'sha256':sha256(path),'private':private}
        for col in frame:
            dictionary.append({'table':name,'field':str(col),'dtype':str(frame[col].dtype),'missing':int(frame[col].isna().sum()),'definition':'Original source field; do not assume common units across categories' if col not in {'source','league','season','source_player_id','shot_date','category_exposure_compatible','ml_use_status','model_use_eligible'} else {'source':'Original provider plus archive provenance route','league':'Explicit league; never inferred from player name','season':'Explicit source season, normalized YYYY-YYYY','source_player_id':'Provider ID; no approved cross-source join implied','shot_date':'Source match date without independently confirmed timezone/publication time','category_exposure_compatible':'Category Mins_Per_90 matches standard minutes/90 within .061','ml_use_status':'Retained provider-use restriction','model_use_eligible':'False for review-only provider context'}[col]})
    sources=json.loads((FOLDER/'understat_sources.json').read_text())
    for record in sources:
        path=pinned_archive(record,download);inputs[record['path']]=record['sha256']
        frame,reader=archive_frame(path);record['reader']=reader
        assert {v.replace('_',' ').casefold() for v in frame.league.dropna().astype(str)}=={UNDERSTAT[record['league']].replace('_',' ').casefold()}
        years=pd.to_numeric(frame.season,errors='raise')
        selected=frame[years.between(2020,2025)].copy()
        selected.columns=selected.columns.astype(str)
        selected['source_season']=selected.season
        selected['season']=years.loc[selected.index].map(lambda y:f'{int(y)}-{int(y)+1}')
        selected['league']=record['league'];selected['source']='understat_worldfootballr'
        selected['source_player_id']=pd.to_numeric(selected.player_id,errors='raise').astype('Int64').astype('string')
        selected['shot_id']=pd.to_numeric(selected.id,errors='raise').astype('Int64')
        selected['match_id']=pd.to_numeric(selected.match_id,errors='raise').astype('Int64')
        selected['shot_date']=pd.to_datetime(selected.date,errors='raise')
        assert not selected.shot_id.isna().any() and not selected.shot_id.duplicated().any()
        assert selected[['X','Y','xG']].apply(lambda c:c.between(0,1)).all().all()
        side=selected.h_a.where(selected.h_a.isin(['h','a']))
        alternate=selected.home_away.where(selected.home_away.isin(['h','a']))
        selected['side_field_conflict']=(side.notna() & alternate.notna() & side.ne(alternate)).fillna(False)
        side=side.fillna(alternate).mask(selected.side_field_conflict)
        selected['team']=selected.home_team.where(side.eq('h')).combine_first(selected.away_team.where(side.eq('a')))
        selected['team_side_resolved']=side.notna()
        selected['partial_season']=selected.season.eq('2025-2026')
        selected['archive_sha256']=record['sha256']
        selected['source_publication_known_at']=pd.NaT
        selected['first_observed_at_utc']=pd.Timestamp(record['retrieved_at'])
        name='understat_'+record['league'].lower().replace(' ','_')+'_shots'
        save(selected.reset_index(drop=True),name)
        for start in range(2020,2026):
            g=selected[selected.season.eq(f'{start}-{start+1}')]
            expected=306 if record['league']=='Bundesliga' or (record['league']=='Ligue 1' and start>=2023) else 380
            if start<2025 and len(g):
                games=g[['match_id','home_team','away_team']].drop_duplicates()
                assert games.match_id.is_unique
                clubs=set(g.home_team)|set(g.away_team)
                observed=set(zip(games.home_team,games.away_team))
                for home,away in sorted((h,a) for h in clubs for a in clubs if h!=a and (h,a) not in observed):
                    missing_fixtures.append({'league':record['league'],'season':f'{start}-{start+1}','home_team':home,'away_team':away,'evidence':'Expected round-robin pairing absent from shot archive; date/result/match ID unknown'})
            coverage.append({'source':'understat_worldfootballr','league':record['league'],'season':f'{start}-{start+1}','category':'shots','rows':len(g),'players':g.source_player_id.nunique(),'matches':g.match_id.nunique(),'expected_schedule_matches':expected,'valid_exposure_rows':None,'status':'partial_snapshot' if start==2025 else ('observed_expected_match_count' if g.match_id.nunique()==expected else 'observed_incomplete_match_count'),'earliest_event':str(g.shot_date.min()),'latest_event':str(g.shot_date.max())})
        print(record['league'],'Understat shots',len(selected),flush=True)
    (FOLDER/'understat_sources.json').write_text(json.dumps(sources,indent=2)+'\n')
    records=[r for r in json.loads((ROOT/'reports/worldfootballr_sources.json').read_text()) if r['original_source']=='fbref']
    standard_record=next(r for r in records if r['category']=='standard')
    standard=select_rows(read_rds(ensure_snapshot(standard_record,download))[0]);standard=standard[standard.league.isin(LEAGUES)]
    for record in records:
        path=ensure_snapshot(record,download);inputs[record['path']]=record['sha256']
        frame=select_rows(read_rds(path)[0]);frame=frame[frame.league.isin(LEAGUES)].copy()
        if record['category']=='standard':frame['category_exposure_compatible']=True
        else:
            frame=frame.merge(standard[KEYS+['Min_Playing']],on=KEYS,how='left',validate='one_to_one',suffixes=('','_standard'))
            diff=(pd.to_numeric(frame.Min_Playing,errors='coerce')/90-pd.to_numeric(frame.Mins_Per_90,errors='coerce')).abs()
            frame['category_exposure_compatible']=diff.le(.061)
        frame['source']='fbref_worldfootballr';frame['archive_sha256']=record['sha256'];frame['partial_season']=frame.season.eq('2025-2026')
        save(frame.reset_index(drop=True),'fbref_'+record['category'])
        for league in LEAGUES:
            for start in range(2020,2026):
                g=frame[frame.league.eq(league)&frame.season.eq(f'{start}-{start+1}')]
                coverage.append({'source':'fbref_worldfootballr','league':league,'season':f'{start}-{start+1}','category':record['category'],'rows':len(g),'players':g.source_player_id.nunique(),'matches':None,'expected_schedule_matches':None,'valid_exposure_rows':int(g.category_exposure_compatible.sum()),'status':'partial_snapshot' if start==2025 else ('observed_aligned' if g.category_exposure_compatible.all() else 'observed_exposure_mismatch'),'earliest_event':None,'latest_event':None})
    if not public_only:
        # Source-only context; no FBref identities, price parsing or model integration.
        raw=ROOT/'data/raw/sources/salimt_uploaded'
        receipt=json.loads((raw/'receipt.json').read_text())
        for key in ['team_competitions_seasons','player_profiles']:
            info=receipt['files'][key];assert sha256(ROOT/info['path'])==info['sha256'];inputs[info['path']]=info['sha256']
        teams=pd.read_csv(raw/'team_competitions_seasons.csv',dtype=str)
        years=pd.to_numeric(teams.season_id,errors='coerce')
        teams=teams[teams.competition_id.isin(LEAGUES.values())&years.between(2020,2025)].copy()
        teams['season']=years.loc[teams.index].map(lambda y:f'{int(y)}-{int(y)+1}')
        teams['league']=teams.competition_id.map({v:k for k,v in LEAGUES.items()})
        clubs=teams[['club_id','league','season']].drop_duplicates()
        assert not clubs.duplicated(['club_id','season']).any()
        history_receipt=json.loads((raw/'histories/receipt.json').read_text())
        payload=raw/'histories/player_performances.txt'
        assert sha256(payload)==history_receipt['files']['player_performances']['payload_sha256'];inputs[str(payload.relative_to(ROOT))]=sha256(payload)
        parts=[]
        for chunk in pd.read_csv(payload,dtype=str,chunksize=100000):
            years=season_year(chunk.season_name);mask=chunk.competition_id.isin(LEAGUES.values())&years.between(2020,2025).fillna(False)
            part=chunk[mask].copy();part['source_row_number']=part.index+2
            part['season']=years.loc[mask].map(lambda y:f'{y}-{y+1}')
            part['league']=part.competition_id.map({v:k for k,v in LEAGUES.items()});parts.append(part)
        performance=pd.concat(parts,ignore_index=True)
        transfers_path=ROOT/'data/processed/real/collected_salimt_transfer_history.parquet'
        history_manifest=json.loads((ROOT/'reports/salimt_history_audit.json').read_text())
        expected=history_manifest.get('outputs_sha256',{}).get(str(transfers_path.relative_to(ROOT)))
        assert expected is not None and sha256(transfers_path)==expected
        inputs[str(transfers_path.relative_to(ROOT))]=sha256(transfers_path)
        transfers=pd.read_parquet(transfers_path)
        contexts=[]
        for direction,column in [('origin','from_team_id'),('destination','to_team_id')]:
            g=transfers.merge(clubs,left_on=[column,'season'],right_on=['club_id','season'],how='inner',validate='many_to_one')
            g['club_context_direction']=direction;contexts.append(g)
        contexts=pd.concat(contexts,ignore_index=True)
        for name,frame in [('transfermarkt_team_seasons_review',teams),('transfermarkt_performances_review',performance),('transfermarkt_transfer_context_review',contexts)]:
            frame['original_source']='Transfermarkt.com';frame['ml_use_status']=RESTRICTED;frame['model_use_eligible']=False;frame['source_publication_known_at']=pd.NaT
            save(frame.reset_index(drop=True),name,private=True)
            for league in LEAGUES:
                for start in range(2020,2026):
                    g=frame[frame.league.eq(league)&frame.season.eq(f'{start}-{start+1}')]
                    coverage.append({'source':'uploaded_transfermarkt','league':league,'season':f'{start}-{start+1}','category':name.replace('transfermarkt_','').replace('_review',''),'rows':len(g),'players':g.player_id.nunique() if 'player_id' in g else None,'matches':None,'expected_schedule_matches':None,'valid_exposure_rows':None,'status':'retained_review_only_completeness_unverified','earliest_event':None,'latest_event':None})
    pd.DataFrame(coverage).to_csv(FOLDER/'coverage.csv',index=False)
    pd.DataFrame(missing_fixtures,columns=['league','season','home_team','away_team','evidence']).to_csv(FOLDER/'missing_fixture_pairs.csv',index=False)
    pd.DataFrame(dictionary).to_csv(FOLDER/'dictionary.csv',index=False)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'script_sha256':sha256(Path(__file__)),'inputs_sha256':inputs,'outputs':outputs,'understat_sources':sources,'leagues':list(LEAGUES),'current_app_or_models_changed':False,'limits':['FBref/Understat release snapshots are dated September 2025; 2025/26 is partial. Uploaded Transfermarkt context completeness is unverified.','Understat IDs are source-specific; cross-source joins are not approved by this collection.','FBref exposure-mismatched category rows are flagged and must not be used as aligned full-season features.','Transfermarkt context is retained review-only, private and blocked from model fitting; fees and publication times are not independently verified.','New Understat archives were fetched from published GitHub assets, not provider pages; secondary publication is not a provider redistribution license.'],'network_observations':{'github_api':'Proxy CONNECT 403; no retry','github_release_assets':'Successful public release listing and four asset downloads'},'problems':problems,'missing_expected_fixture_pairs':len(missing_fixtures)}
    (FOLDER/'acquisition.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v['rows'] for k,v in outputs.items()},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true');parser.add_argument('--public-only',action='store_true');args=parser.parse_args();run(args.download,args.public_only)
