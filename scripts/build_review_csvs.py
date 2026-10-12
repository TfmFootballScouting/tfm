"""Package real source CSVs for review; no downloads, fabricated data or model fit."""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from scripts.worldfootballr_archive import read_rds
from scripts.four_league_acquisition import archive_frame

LEAGUES = ['La Liga', 'Premier League', 'Bundesliga', 'Serie A', 'Ligue 1']


def main():
    catalog = json.loads((ROOT/'data/raw/sources_manifest.json').read_text(encoding='utf-8'))
    entries = []
    for record in catalog['archives']:
        path = ROOT/record['path']
        if sha256(path) != record['sha256']:
            raise ValueError(f'Original archive checksum mismatch: {record["path"]}')
        frame, reader = archive_frame(path) if record['original_source']=='understat' else read_rds(path)
        if record['original_source']=='fbref':
            selected = frame[frame.Comp.isin(LEAGUES)&pd.to_numeric(frame.Season_End_Year).between(2021,2026)].copy()
            relative = f'data/raw/fbref/{record["category"]}.csv'
            rule = 'Comp in five leagues; Season_End_Year 2021..2026; source columns and values unchanged'
        else:
            selected = frame[pd.to_numeric(frame.season).between(2020,2025)].copy()
            league = record.get('league', 'La Liga')
            relative = f'data/raw/understat/{league.lower().replace(" ","_")}_shots.csv'
            rule = 'Source season 2020..2025; source columns and values unchanged'
        target = ROOT/relative;target.parent.mkdir(parents=True,exist_ok=True)
        selected.to_csv(target,index=False,encoding='utf-8',float_format='%.17g')
        entries.append({'path':relative,'sha256':sha256(target),'rows':len(selected),'columns':list(selected.columns),
            'provider':record['original_source'],'acquisition':'CSV export of retained GitHub release RDS; not a directly downloaded CSV',
            'archive_path':record['path'],'archive_sha256':record['sha256'],'url':record['url'],
            'original_retrieved_at':record['retrieved_at'],'reader':reader,'selection_rule':rule,
            'league':record.get('league','La Liga') if record['original_source']=='understat' else None,
            'rights_status':record.get('rights_status',record.get('license_status'))})
    receipt = json.loads((ROOT/'data/raw/sources/salimt_uploaded/receipt.json').read_text(encoding='utf-8'))
    for name in ['player_profiles','player_market_value','team_details','team_competitions_seasons']:
        original = ROOT/f'data/raw/sources/salimt_uploaded/{name}.csv'
        relative = f'data/raw/transfermarkt/{name}.csv';target=ROOT/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(original,target)
        assert sha256(original)==sha256(target)
        raw=pd.read_csv(target,dtype=str)
        entries.append({'path':relative,'sha256':sha256(target),'rows':len(raw),'columns':list(raw.columns),
            'provider':'transfermarkt','acquisition':'Unmodified user-uploaded CSV; claimed GitHub origin not independently commit-verified',
            'claimed_repository':receipt['claimed_source_repository'],'source_commit_verified':False,
            'original_path':str(original.relative_to(ROOT)),'original_retrieved_at':receipt['first_preserved_at_utc'],
            'rights_status':'No provider model-use permission established; valuation display only, not recommendation fitting'})
    manifest={'schema_version':1,'created_at_utc':datetime.now(timezone.utc).isoformat(),'real_data_only':True,
        'raw_csvs':entries,'notes':['CSV exports are source-preserving target-season subsets, not cleaned or joined observations.',
            'Original RDS bytes and original upload receipts remain locally preserved with their exact checksums.',
            'No provider pages were scraped during packaging; no source-use permission is inferred from GitHub publication.']}
    (ROOT/'data/raw/review_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Prepared',len(entries),'source CSV files')


if __name__=='__main__':main()
