"""Compare frozen Spanish and newly trained European models on identical pools."""
import json
import pandas as pd
from src.config import ROOT
from src.models.collected import EXPERIMENTS,cohorts,evaluate_pair
from src.models.recommend import PlayerRecommender
from src.data.provenance import sha256


def main():
    folder=ROOT/'reports/five_league_pipeline'
    pipeline=json.loads((folder/'pipeline.json').read_text())
    old=json.loads((ROOT/'reports/enrichment/pipeline.json').read_text())
    rows=[]
    for name,spec in EXPERIMENTS.items():
        item=pipeline['outputs']['offensive_gallery' if name=='offensive' else 'core_gallery']
        parts=cohorts(pd.read_parquet(ROOT/item['path']),spec['split'])
        info=old['new_model_experiments'][name]
        assert sha256(ROOT/info['model_path'])==info['model_sha256']
        rec=PlayerRecommender.load(ROOT/info['model_path'])
        held,details=evaluate_pair(rec,parts['validation'],parts['holdout'],'holdout_same_pool')
        held.to_csv(folder/f'{name}_original_same_pool.csv',index=False)
        selected=held[held.method.eq(info['selected_method'])].iloc[0]
        new_details=pd.read_csv(folder/f'{name}_queries.csv')
        new_method=pipeline['experiments'][name]['selected_method']
        a=details[details.method.eq(info['selected_method'])][['entity_id','reciprocal_rank']]
        b=new_details[new_details.phase.eq('holdout')&new_details.method.eq(new_method)][['entity_id','reciprocal_rank']]
        paired=a.merge(b,on='entity_id',validate='one_to_one',suffixes=('_original','_trained'))
        assert len(paired)==len(a)==len(b)
        import numpy as np
        difference=(paired.reciprocal_rank_trained-paired.reciprocal_rank_original).to_numpy()
        rng=np.random.default_rng(42)
        samples=difference[rng.integers(0,len(difference),(500,len(difference)))].mean(axis=1)
        lo,hi=np.quantile(samples,[.025,.975])
        rows.append(dict(model=name,queries=len(paired),candidates=int(selected.candidate_count),
            original_method=info['selected_method'],trained_method=new_method,
            original_mrr=float(selected.mrr),trained_mrr=float(paired.reciprocal_rank_trained.mean()),
            trained_minus_original_mrr=float(difference.mean()),paired_ci_low=float(lo),paired_ci_high=float(hi),
            interpretation='same holdout people/pool; methods selected on their respective validation; no holdout tuning'))
    result=pd.DataFrame(rows);result.to_csv(folder/'matched_pool_comparison.csv',index=False)
    print(result.to_string(index=False))

if __name__=='__main__':main()
