"""Generate blinded real-data shortlist pairs; ratings remain genuinely blank."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.app.trained import load_trained_service
from src.config import ROOT


def main():
    service=load_trained_service('core')
    season='2023-2024'
    rec=service.for_season(season)
    rng=np.random.default_rng(20261012)
    public=ROOT/'docs/expert_review'
    private=ROOT/'data/expert_review/private'
    public.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
    packets=[];key=[];forms=[]
    for index,style in enumerate(service.supported_styles):
        eligible=rec.players[rec.players.pos_main.isin(['DF','MF','FW'])]
        ranked=rec.recommend(style_key=style,season=season,top_n=5)
        baseline=eligible.sample(n=5,random_state=20261012+index)
        methods=[('style_affinity',ranked),('random_eligible',baseline)]
        rng.shuffle(methods)
        case=f'brief-{index+1:02d}'
        for letter,(method,players) in zip(['A','B'],methods):
            key.append(dict(brief_id=case,packet=letter,method=method))
            for rank,(_,player) in enumerate(players.iterrows(),1):
                packets.append(dict(brief_id=case,style=style,season=season,packet=letter,rank=rank,
                    player_id=player.entity_id,player=player.player,position=player.pos_main,club=player.team,
                    minutes=player.minutes,age=player.age))
                forms.append(dict(expert_alias='',brief_id=case,packet=letter,player_id=player.entity_id,
                    tactical_fit_1_to_5='',shortlist_yes_no='',confidence_1_to_5='',rationale=''))
    pd.DataFrame(packets).to_csv(public/'blinded_shortlists.csv',index=False)
    pd.DataFrame(forms).to_csv(public/'rating_template.csv',index=False)
    pd.DataFrame(key).to_csv(private/'method_key.csv',index=False)
    metadata={'season':season,'seed':20261012,'ratings_collected':False,'comparison':'Expert-weighted affinity versus eligible random baseline; no transfer prediction',
              'dataset':service.info['gallery_dataset_version'],
              'packet_sha256':hashlib.sha256((public/'blinded_shortlists.csv').read_bytes()).hexdigest()}
    (public/'packet_manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
if __name__=='__main__':main()
