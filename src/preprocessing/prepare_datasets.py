"""Reproduce review tables from bundled real source CSVs without model refitting."""
import json
from pathlib import Path
import pandas as pd
from src.config import ROOT
from src.data_preparation.provenance import sha256
from src.data_preparation.source_rights import RESTRICTED
from src.data_preparation.salimt_uploaded import normalize_profiles, normalize_values
from src.preprocessing.football_stats import normalize_fbref, aggregate_player_seasons
from src.preprocessing.fbref_categories import select_rows, align_category, dominant_league_gallery, MAPPINGS, KEYS


def load_raw_csv(record):
    path=ROOT/record['path']
    if sha256(path)!=record['sha256']:
        raise ValueError(f'Raw review CSV fingerprint changed: {record["path"]}')
    return pd.read_csv(path,dtype={'Age':'string','Url':'string','player_id':'string'},float_precision='round_trip')


def fbref_tables(records):
    tables={r['path'].split('/')[-1][:-4]:select_rows(load_raw_csv(r)) for r in records if r['provider']=='fbref'}
    standard=tables['standard']
    columns=['Player','Nation','Pos','Age','Born','Min_Playing','MP_Playing','Gls','Ast','xG_Expected','xAG_Expected']
    base=standard[KEYS+columns].rename(columns={'Player':'player','Nation':'nation','Pos':'pos','Age':'age',
        'Born':'birth_year','Min_Playing':'minutes','MP_Playing':'mp','Gls':'gls','Ast':'ast','xG_Expected':'xg','xAG_Expected':'xag'})
    for category,mapping in MAPPINGS.items():
        _,packet=align_category(standard,tables[category],mapping)
        base=base.merge(packet,on=KEYS,how='left',validate='one_to_one')
    base['source']='fbref_worldfootballr';base['provenance_status']='published_secondary_archive'
    base['period_status']=base.season.map(lambda s:'partial_September_2025' if s=='2025-2026' else 'historical_season_label_completeness_not_guaranteed')
    clubs,issues,duplicates=normalize_fbref(base)
    seasons=aggregate_player_seasons(clubs)
    gallery=dominant_league_gallery(seasons)
    return {'fbref_player_club_seasons':clubs,'fbref_player_seasons':seasons,
        'fbref_scouting_gallery':gallery[gallery.tactical_proxy_candidate&~gallery.partial_season].copy()},issues,duplicates


def understat_tables(records):
    parts=[]
    for r in records:
        if r['provider']!='understat':continue
        f=load_raw_csv(r)
        f['league']=r['league'];f['source']='understat_worldfootballr'
        year=pd.to_numeric(f.season,errors='raise').astype(int)
        f['source_season']=f.season;f['season']=year.map(lambda y:f'{y}-{y+1}')
        for raw,normalized in [('id','shot_id'),('player_id','source_player_id'),('match_id','match_id')]:
            f[normalized]=pd.to_numeric(f[raw],errors='raise').astype('Int64').astype('string')
        f['shot_date']=pd.to_datetime(f.date,errors='raise')
        side=f.h_a.where(f.h_a.isin(['h','a']));alternate=f.home_away.where(f.home_away.isin(['h','a']))
        conflict=side.notna()&alternate.notna()&side.ne(alternate)
        side=side.fillna(alternate).mask(conflict)
        f['team']=f.home_team.where(side.eq('h')).combine_first(f.away_team.where(side.eq('a')))
        f['team_side_resolved']=side.notna();f['side_field_conflict']=conflict
        for col in ['X','Y','xG','minute']:f[col]=pd.to_numeric(f[col],errors='coerce')
        f['quality_valid']=f[['X','Y','xG']].apply(lambda x:x.between(0,1)).all(axis=1)&f.minute.between(0,150)&f.team_side_resolved
        f['partial_season']=f.season.eq('2025-2026')
        parts.append(f)
    shots=pd.concat(parts,ignore_index=True)
    if shots.duplicated(['league','shot_id']).any():raise ValueError('Duplicate source shot identity')
    # Real invalid rows remain in a quarantine table; no silent replacement or zero xG filling.
    valid=shots[shots.quality_valid].copy()
    valid['attempt']=~valid.result.eq('OwnGoal');valid['goal']=valid.result.eq('Goal')
    valid['attempt_xg']=valid.xG.where(valid.attempt,0)
    players=valid.groupby(['league','season','source_player_id'],dropna=False).agg(
        player=('player','first'),shots=('attempt','sum'),goals=('goal','sum'),xg=('attempt_xg','sum'),
        matches_with_shots=('match_id','nunique'),partial_season=('partial_season','any')).reset_index()
    players['xg_per_shot']=players.xg/players.shots.where(players.shots.gt(0))
    players['minutes']=float('nan')
    return {'understat_shots':valid,'understat_player_seasons':players,'understat_quarantine':shots[~shots.quality_valid].copy()}


def main():
    manifest=json.loads((ROOT/'data/raw/source_manifest.json').read_text(encoding='utf-8'))
    records=manifest['raw_csvs']
    frames,issues,duplicates=fbref_tables(records)
    frames.update(understat_tables(records))
    tm={Path(r['path']).stem:r for r in records if r['provider']=='transfermarkt'}
    raw=load_raw_csv(tm['player_profiles']);profiles=normalize_profiles(raw)
    values=normalize_values(load_raw_csv(tm['player_market_value']),tm['player_market_value']['original_retrieved_at'])
    for f in [profiles,values]:
        f['ml_use_status']=RESTRICTED;f['model_use_eligible']=False
    values['currency_evidence']='EUR_assumed_not_explicit_in_raw'
    frames.update(transfermarkt_profiles=profiles,transfermarkt_values=values)
    destination=ROOT/'data/processed';destination.mkdir(parents=True,exist_ok=True)
    model_manifest=json.loads((ROOT/'reports/five_league_pipeline/experiment_manifest.json').read_text(encoding='utf8'))
    mapping={'player_club_seasons':'fbref_player_club_seasons','player_seasons':'fbref_player_seasons','scouting_gallery':'fbref_scouting_gallery'}
    contract={'model_input_expected_sha256':{mapping[key]:entry['sha256'] for key,entry in model_manifest['outputs'].items()}}
    value_manifest=json.loads((ROOT/'models/valuation_manifest.json').read_text(encoding='utf8'))
    identity=dict(value_manifest['inputs']['identity_candidates'],
        provenance='Included provisional matching proposals from the original identity audit; validated, not regenerated by CSV cleaning.')
    if sha256(ROOT/identity['path'])!=identity['sha256']:
        raise ValueError('Included player identity links fingerprint changed')
    outputs={}
    for name,frame in frames.items():
        csv=destination/f'{name}.csv.gz' if name in ['transfermarkt_values', 'understat_shots'] else destination/f'{name}.csv'
        parquet=destination/f'{name}.parquet'
        compression={'method':'gzip','mtime':0,'compresslevel':6} if str(csv).endswith('.gz') else None
        frame.to_csv(csv,index=False,encoding='utf-8',compression=compression);frame.to_parquet(parquet,index=False)
        outputs[name]={'rows':len(frame),'csv_path':str(csv.relative_to(ROOT)),'csv_sha256':sha256(csv),
            'parquet_path':str(parquet.relative_to(ROOT)),'parquet_sha256':sha256(parquet)}
    # Model inputs are pinned; only an explicit new training version can change them.
    for name,expected in contract['model_input_expected_sha256'].items():
        if outputs[name]['parquet_sha256']!=expected:
            raise ValueError(f'Prepared model input differs from verified data contract: {name}')
    report={'raw_manifest_sha256':sha256(ROOT/'data/raw/source_manifest.json'),'outputs':outputs,
        'model_input_expected_sha256':contract['model_input_expected_sha256'],'identity_links':identity,'shared_by_app_and_notebooks':True,
        'exact_fbref_duplicates_removed':duplicates,'frozen_gallery_numeric_parity_verified':True,
        'cleaning_issues':issues,'model_fitting_performed':False,'cross_source_joins':'Existing provisional FBref/Transfermarkt identity proposals retained separately; Understat not merged into model'}
    (destination/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v['rows'] for k,v in outputs.items()},indent=2))


if __name__=='__main__':main()
