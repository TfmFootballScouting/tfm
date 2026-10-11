"""Validate and export published worldfootballR archives without provider crawling.

Manifest pins the actual archive bytes. Release URLs are mutable: a changed checksum
is an error, never an instruction to change the expected hash or use fake data.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
import pandas as pd
import requests
from src.config import ROOT
from src.data.provenance import sha256, snapshot
from src.data.source_rights import require_source_use, RESTRICTED

TARGET_YEARS=range(2020,2026)
KEYS=['source_player_id','team','season']


def read_rds(path):
    import pyreadr
    try:
        values=pyreadr.read_r(str(path))
        if len(values)!=1:
            raise ValueError('Expected one data frame in the RDS snapshot')
        return next(iter(values.values())), 'pyreadr'
    except pyreadr.custom_errors.LibrdataError:
        # The older transfer archive has R strings requiring Latin-1 decoding.
        # Preserve original bytes and use the supported R-data parser, not a
        # modified raw file or lossy ignore/replace decoding.
        import rdata
        frame=rdata.conversion.convert(rdata.parser.parse_file(path),default_encoding='latin1')
        if not isinstance(frame,pd.DataFrame):
            raise ValueError('Expected an R data frame')
        return frame,'rdata_latin1_default'


def ensure_snapshot(record,download=False):
    path=ROOT/record['path']
    if not path.exists():
        if not download:
            raise FileNotFoundError(f'Missing {record["category"]} archive; use --download')
        rights_source = 'transfermarkt' if record.get('category') == 'player_mapping' else record.get('original_source', '')
        require_source_use(rights_source, 'archive acquisition')
        r=requests.get(record['url'],timeout=90)
        r.raise_for_status()
        if hashlib.sha256(r.content).hexdigest()!=record['sha256']:
            raise ValueError('Published archive changed: SHA-256 mismatch; do not replace the expected hash')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(r.content)
        time.sleep(3)
    if sha256(path)!=record['sha256']:
        raise ValueError('Local archive checksum mismatch')
    return path


def fbref_table(frame):
    frame=frame[(frame.Comp=='La Liga') & pd.to_numeric(frame.Season_End_Year).between(2021,2026)].copy()
    frame['source_player_id']=frame.Url.str.extract(r'/players/([^/]+)',expand=False)
    if frame.source_player_id.isna().any():
        raise ValueError('FBref archive row lacks a stable source player URL/ID')
    frame['team']=frame.Squad
    frame['season']=frame.Season_End_Year.map(lambda y:f'{int(y)-1}-{int(y)}')
    return frame


def exposure_audit(standard,aux,category):
    if standard.duplicated(KEYS).any() or aux.duplicated(KEYS).any():
        raise ValueError(f'{category}: conflicting duplicate join keys')
    b=standard[KEYS+['Min_Playing']].copy()
    a=aux[KEYS+['Mins_Per_90']].copy()
    a['Mins_Per_90']=pd.to_numeric(a.Mins_Per_90,errors='coerce')
    joined=b.merge(a,on=KEYS,how='left',validate='one_to_one',indicator=True)
    diff=(pd.to_numeric(joined.Min_Playing,errors='coerce')/90-joined.Mins_Per_90).abs()
    result=[]
    for season,g in joined.groupby('season'):
        d=diff.loc[g.index]
        result.append(dict(season=season,category=category,standard_rows=len(g),
            matched_rows=int((g._merge=='both').sum()),missing_keys=int((g._merge!='both').sum()),
            exposure_mismatch_rows=int((d>.061).sum()),valid_exposure_join_rows=int((d<=.061).sum()),
            max_exposure_difference_90s=float(d.max()) if d.notna().any() else None))
    return result


def aligned_stats(standard, aux, columns):
    """Null period-incompatible statistics, preserving raw archives separately."""
    if standard.duplicated(KEYS).any() or aux.duplicated(KEYS).any():
        raise ValueError('Duplicate source-ID/club/season keys')
    needed=KEYS+['Mins_Per_90']+list(columns)
    joined=standard[KEYS+['Min_Playing']].merge(aux[needed],on=KEYS,how='left',validate='one_to_one')
    exposure=(pd.to_numeric(joined.Min_Playing,errors='coerce')/90-pd.to_numeric(joined.Mins_Per_90,errors='coerce')).abs()
    compatible=exposure<=.061
    for original in columns:
        joined[original]=pd.to_numeric(joined[original],errors='coerce').where(compatible)
    return joined[KEYS+list(columns)].rename(columns=columns)


def run(download=False):
    records=json.loads((ROOT/'reports/worldfootballr_sources.json').read_text())
    out=ROOT/'data/external/worldfootballr';out.mkdir(parents=True,exist_ok=True)
    coverage=[];inventory=[];fb_tables={};inspection=[]
    for record in records:
        path=ensure_snapshot(record,download)
        source,cat=record['original_source'],record['category']
        if cat=='player_mapping':
            try:
                frame=pd.read_csv(path,encoding='utf8')
                encoding='utf8'
            except UnicodeDecodeError:
                frame=pd.read_csv(path,encoding='latin1')
                encoding='latin1_identifiers_are_ASCII'
            frame['archive_text_encoding']=encoding
            frame['fbref_id']=frame.UrlFBref.str.extract(r'/players/([^/]+)',expand=False)
            frame['transfermarkt_id']=frame.UrlTmarkt.str.extract(r'/spieler/(\d+)',expand=False)
            frame['mapping_status']='upstream_published_not_locally_reviewed'
            frame['ml_use_status']=RESTRICTED
            frame.to_parquet(out/'player_mapping.parquet',index=False)
            inspection.append(dict(category=cat,rows=len(frame),missing_fbref_ids=int(frame.fbref_id.isna().sum()),missing_tm_ids=int(frame.transfermarkt_id.isna().sum()),duplicate_fbref_ids=int(frame.fbref_id.duplicated().sum()),duplicate_tm_ids=int(frame.transfermarkt_id.duplicated().sum())))
            continue
        frame,reader=read_rds(path)
        inventory.append(dict(source=source,category=cat,reader=reader,raw_rows=len(frame),raw_columns=len(frame.columns),sha256=record['sha256'],archive_last_modified=record.get('last_modified')))
        if source=='fbref':
            selected=fbref_table(frame)
            fb_tables[cat]=selected
            year=selected.season.str[:4].astype(int)
            league='La Liga'
        elif source=='understat':
            selected=frame[pd.to_numeric(frame.season).between(2020,2025)].copy()
            year=pd.to_numeric(selected.season).astype(int)
            selected['source_player_id']=pd.to_numeric(selected.player_id).astype('Int64').astype(str)
            selected['season']=year.map(lambda y:f'{y}-{y+1}')
            if selected.id.duplicated().any():
                raise ValueError('Duplicate Understat shot IDs')
            selected['shot_id']=pd.to_numeric(selected.id).astype('Int64').astype(str)
            league='La Liga'
        else:
            year_column='season_start_year' if cat=='valuations' else 'season'
            selected=frame[(frame.country=='Spain') & pd.to_numeric(frame[year_column]).between(2020,2025)].copy()
            year=pd.to_numeric(selected[year_column]).astype(int)
            selected['source_player_id']=selected.player_url.str.extract(r'/spieler/(\d+)',expand=False)
            selected['season']=year.map(lambda y:f'{y}-{y+1}')
            selected['temporal_validation']='season_label_only_no_effective_date_or_known_at'
            selected['ml_use_status']=RESTRICTED
            league='La Liga'
        selected['source']=source
        selected['acquisition']='worldfootballr_archive'
        selected['snapshot_sha256']=record['sha256']
        selected.to_parquet(out/f'{source}_{cat}.parquet',index=False)
        for y in TARGET_YEARS:
            g=selected[year==y]
            status='available_snapshot' if len(g) else 'not_in_archive'
            note='Archive snapshot; season label is not proof of final completeness'
            if y==2025 and len(g):
                status='partial_season_snapshot';note='Archive from September 2025; not final 2025/26 data'
            row=dict(source=source,acquisition='worldfootballr_archive',league=league,season=f'{y}-{y+1}',category=cat,rows=len(g),players=g.source_player_id.nunique() if len(g) else 0,status=status,note=note)
            if source=='understat' and len(g):
                row.update(matches=g.match_id.nunique(),first_date=g.date.min(),last_date=g.date.max())
            if source=='transfermarkt' and len(g):
                row['note']='Archived season-labelled records; no valuation knowledge date or exact transfer date. Not ready for leakage-safe historical validation.'
            if source=='transfermarkt':
                row['ml_use_status']=RESTRICTED
                row['note']+=' Terms section 11.1: no AI/ML use without an explicit licence.'
            coverage.append(row)
            coverage.append(dict(source=source,acquisition='worldfootballr_archive',league='Segunda',season=f'{y}-{y+1}',category=cat,rows=0,players=0,status='not_in_archive',note='These selected assets cover Big Five top divisions / Understat La Liga, not Segunda'))
    audits=[]
    for cat,f in fb_tables.items():
        if cat!='standard':audits+=exposure_audit(fb_tables['standard'],f,cat)
    # Safe candidate table: no imputation, minute floor or model fitting occurs here.
    standard=fb_tables['standard']
    base=standard[KEYS+['Player','Nation','Pos','Age','Born','Min_Playing','MP_Playing','Gls','Ast','xG_Expected','xAG_Expected']].rename(columns={
        'Player':'player','Nation':'nation','Pos':'pos','Age':'age','Born':'birth_year',
        'Min_Playing':'minutes','MP_Playing':'mp','Gls':'gls','Ast':'ast','xG_Expected':'xg','xAG_Expected':'xag'})
    mappings={'shooting':{'Sh_Standard':'sh','SoT_Standard':'sot'},
        'defense':{'Int':'int','TklW_Tackles':'tklw'},
        'misc':{'Crs':'crs','Fls':'fls','Fld':'fld'},
        'passing':{'Cmp_Total':'passes_completed','Att_Total':'passes_attempted','KP':'key_passes'},
        'possession':{'Touches_Touches':'touches','Succ_Take':'successful_take_ons'}}
    for cat,columns in mappings.items():
        base=base.merge(aligned_stats(standard,fb_tables[cat],columns),on=KEYS,how='left',validate='one_to_one')
    base['league']='La Liga'
    base['source']='fbref_worldfootballr'
    base['provenance_status']='published_secondary_archive'
    base['period_status']=base.season.map(lambda s:'partial_September_2025' if s=='2025-2026' else 'historical_season_label_completeness_not_guaranteed')
    base.to_parquet(out/'fbref_player_seasons.parquet',index=False)
    for audit in audits:
        if audit['exposure_mismatch_rows']:
            for row in coverage:
                if row['source']=='fbref' and row['league']=='La Liga' and row['season']==audit['season'] and row['category']==audit['category']:
                    row['status']='available_with_period_mismatches'
                    row['note']=f"{audit['exposure_mismatch_rows']} matched rows have different exposure from standard; incompatible stats nulled in candidate table"
    pd.DataFrame(audits).to_csv(ROOT/'reports/worldfootballr_merge_audit.csv',index=False)
    pd.DataFrame(coverage).to_csv(ROOT/'reports/worldfootballr_coverage.csv',index=False)
    (ROOT/'reports/worldfootballr_inventory.json').write_text(json.dumps(dict(datasets=inventory,mapping=inspection,scope='published secondary-source archive; no provider access bypass; no model retrained'),indent=2))
    # Keep Understat at shot grain. Without minutes or an assistant ID, do not invent
    # per-90 statistics, assist counts or cross-source player matches.
    shots=pd.read_parquet(out/'understat_shots.parquet')
    shots['goal']=shots.result.eq('Goal').astype(int)
    shots['xG']=pd.to_numeric(shots.xG,errors='coerce')
    summaries=shots.groupby(['source_player_id','season']).agg(player=('player','first'),shots=('shot_id','size'),goals=('goal','sum'),xg=('xG',lambda x:x.sum(min_count=1))).reset_index()
    summaries['coverage_note']='shots-only aggregate; minutes unavailable; partial 2025/26 snapshot'
    summaries.to_parquet(out/'understat_player_shot_totals.parquet',index=False)
    print(pd.DataFrame(coverage).query("league=='La Liga'")[['source','season','category','rows','status']].to_string(index=False))
    print('Exposure mismatches:',sum(x['exposure_mismatch_rows'] for x in audits))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true')
    run(download=parser.parse_args().download)
