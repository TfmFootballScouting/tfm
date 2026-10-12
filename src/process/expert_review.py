"""Analyze human ratings only; no demonstration ratings substituted."""
import pandas as pd


def analyze(ratings, method_key):
    needed={'expert_alias','brief_id','packet','player_id','tactical_fit_1_to_5','shortlist_yes_no','confidence_1_to_5','rationale'}
    if not needed <= set(ratings):
        raise ValueError('Incomplete expert rating schema')
    if ratings.empty or ratings[list(needed)].isna().all().all():
        return {'status':'pending_human_ratings','ratings':0},pd.DataFrame()
    complete=ratings.dropna(subset=['expert_alias','tactical_fit_1_to_5','shortlist_yes_no','rationale']).copy()
    if complete.empty:
        return {'status':'pending_human_ratings','ratings':0},pd.DataFrame()
    if len(complete)!=len(ratings):
        raise ValueError('Incomplete rating rows: finish or explicitly remove unrated rows')
    for field in ['tactical_fit_1_to_5','confidence_1_to_5']:
        complete[field]=pd.to_numeric(complete[field],errors='raise')
        if not complete[field].isin([1,2,3,4,5]).all():
            raise ValueError('Ratings must be integer 1 through 5')
    if complete.duplicated(['expert_alias','brief_id','packet','player_id']).any():
        raise ValueError('Duplicate expert/player rating')
    if not complete.shortlist_yes_no.isin(['yes','no']).all():
        raise ValueError('Use yes/no shortlist judgments')
    if method_key.duplicated(['brief_id','packet']).any():
        raise ValueError('Ambiguous blinding key')
    joined=complete.merge(method_key,on=['brief_id','packet'],validate='many_to_one',how='left')
    if joined.method.isna().any():raise ValueError('Unknown packet')
    joined['shortlisted']=joined.shortlist_yes_no.eq('yes')
    summaries=joined.groupby(['expert_alias','brief_id','method']).agg(mean_fit=('tactical_fit_1_to_5','mean'),
        precision_at_reviewed_k=('shortlisted','mean'),reviewed_k=('player_id','size')).reset_index()
    paired=summaries.pivot(index=['expert_alias','brief_id'],columns='method',values='mean_fit').dropna()
    report={'status':'human_ratings_analyzed','ratings':len(joined),'experts':joined.expert_alias.nunique(),
            'paired_expert_briefs':len(paired),'warning':'Subjective tactical relevance; not causal transfer success. Do not count player rows as independent experts.'}
    if {'style_affinity','random_eligible'} <= set(paired):
        report['mean_paired_fit_difference']=float((paired.style_affinity-paired.random_eligible).mean())
    return report,summaries
