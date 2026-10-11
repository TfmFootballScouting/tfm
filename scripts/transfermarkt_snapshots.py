"""Normalize already preserved league pages and sample two allowed player profiles.
Current pages are explicitly not historical season coverage.
"""
import json
from pathlib import Path
import pandas as pd
from src.config import ROOT
from src.scraping.collect import Client,AccessBlocked
from src.scraping.transfermarkt import market_snapshot,profile
from src.data.source_rights import require_source_use


def run():
    require_source_use('transfermarkt', 'automated collection')
    records=[json.loads(x) for x in (ROOT/'data/raw/provenance.jsonl').read_text().splitlines()]
    pages={}
    for r in records:
        if r.get('category')=='market_values_access_probe' and r.get('http_status')==200:
            pages.setdefault(r['league'],r)
    folder=ROOT/'data/external/transfermarkt';folder.mkdir(parents=True,exist_ok=True)
    frames=[]
    for league,r in pages.items():
        frame=market_snapshot((ROOT/r['path']).read_text())
        frame['source']='transfermarkt';frame['league']=league;frame['snapshot_sha256']=r['sha256']
        frame['retrieved_at']=r['retrieved_at'];frame['requested_season']=r['season']
        # Current roster/value appears despite historical season URLs. Never assign effective historical season.
        frame['season']=None
        frames.append(frame)
    if not frames:
        raise ValueError('No observed Transfermarkt pages')
    combined=pd.concat(frames,ignore_index=True)
    combined.to_csv(folder/'current_market_sample.csv',index=False)
    client=Client();profiles=[];access=[]
    for _,row in combined.groupby('league').head(1).iterrows():
        for category,path in [('profiles',row.profile_path),('historical_valuations',row.profile_path.replace('/profil/','/marktwertverlauf/')),('transfer_history',row.profile_path.replace('/profil/','/transfers/'))]:
            url='https://www.transfermarkt.com'+path
            try:
                html,r=client.get(url,'transfermarkt',category=category,league=row.league,source_player_id=str(row.source_player_id))
                entry=dict(source_player_id=row.source_player_id,league=row.league,category=category,status='raw_collected_unparsed',reason='HTML contains a client-rendered component but no dated history records; no values or fees inferred',snapshot_sha256=r['sha256'])
                if category=='profiles':
                    data=profile(html)
                    profiles.append(dict(source_player_id=row.source_player_id,player=row.player,source='transfermarkt',league=row.league,snapshot_sha256=r['sha256'],retrieved_at=r['retrieved_at'],**data))
                    entry.update(status='sample_parsed',reason='Current profile; not historical season state')
                access.append(entry)
            except (AccessBlocked,ValueError) as exc:
                access.append(dict(source_player_id=row.source_player_id,league=row.league,category=category,status='blocked_or_parse_failed',reason=str(exc)))
    pd.DataFrame(profiles).to_csv(folder/'current_profiles_sample.csv',index=False)
    pd.DataFrame(access).to_csv(ROOT/'reports/transfermarkt_sample_access.csv',index=False)
    coverage=pd.read_csv(ROOT/'reports/source_coverage.csv')
    mask=coverage.source=='transfermarkt'
    coverage.loc[mask,'status']='historical_unverified'
    coverage.loc[mask,'reason']='Current/undated sample pages preserved; no verified historical season coverage. See transfermarkt_sample_access.csv.'
    coverage.to_csv(ROOT/'reports/source_coverage.csv',index=False)
    print('Current market sample rows:',len(combined));print(pd.DataFrame(access).to_string(index=False))


if __name__=='__main__':
    run()
