"""Verify retained reported valuations; never approve unsupported primary evidence."""
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.data.identity import club_key
from src.data.matching import normalize_name
from src.scraping.transfermarkt import profile as parse_primary_profile
from bs4 import BeautifulSoup
from src.data.source_rights import RESTRICTED
from src.app.europe_budget import load_europe_budget_inputs
from scripts.salimt_history_audit import season_year


def main():
    folder=ROOT/'reports/valuation_verification';folder.mkdir(exist_ok=True)
    out=ROOT/'data/processed/real'
    raw=ROOT/'data/raw/sources/salimt_uploaded'
    receipt=json.loads((raw/'receipt.json').read_text())
    history_receipt=json.loads((raw/'histories/receipt.json').read_text())
    inputs={}
    for item in receipt['files'].values():
        path=ROOT/item['path']
        assert sha256(path)==item['sha256'],str(path)
        inputs[str(path.relative_to(ROOT))]=sha256(path)
    history_path=raw/'histories/player_performances.txt'
    assert sha256(history_path)==history_receipt['files']['player_performances']['payload_sha256']
    inputs[str(history_path.relative_to(ROOT))]=sha256(history_path)
    values,candidates,fbref=load_europe_budget_inputs()
    for path in [out/'collected_salimt_values.parquet',out/'collected_salimt_profiles.parquet',out/'europe_review_candidates.parquet']:
        inputs[str(path.relative_to(ROOT))]=sha256(path)
    original=values.copy()
    uploaded=pd.read_csv(raw/'player_market_value.csv',dtype={'player_id':str})
    uploaded['date']=pd.to_datetime(uploaded.date_unix,format='%Y-%m-%d',errors='raise')
    uploaded['amount']=pd.to_numeric(uploaded.value,errors='raise')
    normalized=values[['source_player_id','valuation_date','market_value_eur']].copy()
    normalized.source_player_id=normalized.source_player_id.astype(str)
    compared=uploaded.merge(normalized,left_on=['player_id','date'],right_on=['source_player_id','valuation_date'],how='outer',validate='one_to_one',indicator=True)
    assert compared._merge.eq('both').all()
    assert compared.amount.eq(compared.market_value_eur).all()
    assert uploaded.amount.ge(0).all() and np.isfinite(uploaded.amount).all()
    stamp=pd.Timestamp(receipt['first_preserved_at_utc']).tz_convert('UTC').tz_localize(None)
    assert uploaded.date.le(stamp).all()
    assert not values.duplicated(['source_player_id','valuation_date']).any()
    profiles=pd.read_parquet(out/'collected_salimt_profiles.parquet')
    known_ids=set(profiles.source_player_id.astype(str))
    values['profile_present']=values.source_player_id.astype(str).isin(known_ids)
    values['amount_raw_roundtrip_verified']=True
    values['effective_date_raw_roundtrip_verified']=True
    values['primary_amount_verified']=False
    values['primary_effective_date_verified']=False
    values['currency_verification_status']='EUR_assumed_by_normalizer_not_explicit_in_raw_value_file'
    values['value_kind']='reported_market_assessment_not_transfer_fee'
    values['historical_budget_eligible']=False
    values['model_use_eligible']=False
    values['ml_use_status']=RESTRICTED
    values.to_parquet(out/'valuation_verification_records.parquet',index=False)
    # Corroborate identity with same-season club evidence from all five leagues.
    player_ids=set(candidates.source_player_id.astype(str))
    history=[]
    for chunk in pd.read_csv(history_path,dtype=str,chunksize=100000,
        usecols=['player_id','season_name','competition_id','team_name']):
        years=season_year(chunk.season_name)
        keep=chunk.player_id.isin(player_ids)&years.between(2020,2025).fillna(False)&chunk.competition_id.isin(['ES1','GB1','L1','IT1','FR1'])
        part=chunk.loc[keep].copy()
        part['season']=years.loc[keep].map(lambda y:f'{y}-{y+1}')
        history.append(part)
    history=pd.concat(history,ignore_index=True).drop_duplicates()
    history['club_key']=history.team_name.map(club_key)
    seasons={pid:set(zip(g.season,g.club_key)) for pid,g in history.groupby('player_id')}
    fbclubs={pid:set(zip(g.season,g.team.map(club_key))) for pid,g in fbref.groupby('source_player_id')}
    review=candidates.copy()
    overlaps=[]; comparable=[]
    for row in review.itertuples():
        left=fbclubs.get(row.fbref_id,set());right=seasons.get(str(row.source_player_id),set())
        overlaps.append(sorted(left&right));comparable.append(bool({s for s,c in left}&{s for s,c in right}))
    review['club_season_overlap_count']=[len(v) for v in overlaps]
    review['club_season_overlap_evidence']=[json.dumps(v) for v in overlaps]
    review['club_history_same_season_available']=comparable
    review['verification_status']=np.select([
        ~review.supported_review_candidate,
        review.club_season_overlap_count.gt(0)],['original_identity_evidence_conflict','corroborated_name_birth_year_and_club_season'],default='supported_name_birth_year_club_unresolved')
    review['identity_match_status']='provisional_not_reviewed'
    review['independent_full_dob_verified']=False
    review['primary_profile_verified']=False
    review['uploaded_dob_matches_retained_primary_profile']=False
    review['primary_profile_snapshot_sha256']=pd.NA
    primary_path=ROOT/'data/external/transfermarkt/current_profiles_sample.csv'
    inputs[str(primary_path.relative_to(ROOT))]=sha256(primary_path)
    for row in pd.read_csv(primary_path,dtype={'source_player_id':str}).itertuples():
        snapshot=ROOT/'data/raw/sources/transfermarkt'/f'{row.snapshot_sha256}.html'
        assert sha256(snapshot)==row.snapshot_sha256
        inputs[str(snapshot.relative_to(ROOT))]=row.snapshot_sha256
        html=snapshot.read_text()
        soup=BeautifulSoup(html,'lxml');canonical=soup.find('link',rel='canonical')
        assert canonical and canonical.get('href','').rstrip('/').endswith('/spieler/'+row.source_player_id)
        dob=pd.to_datetime(parse_primary_profile(html).get('date_of_birth'),errors='raise')
        title=soup.title.get_text(' ',strip=True) if soup.title else ''
        assert normalize_name(row.player) in normalize_name(title)
        uploaded_profile=profiles[profiles.source_player_id.astype(str).eq(row.source_player_id)]
        assert len(uploaded_profile)==1
        agrees=(uploaded_profile.date_of_birth.iloc[0]==dob and
                normalize_name(uploaded_profile.player.iloc[0])==normalize_name(row.player))
        mask=review.source_player_id.astype(str).eq(row.source_player_id)
        review.loc[mask,'primary_profile_verified']=agrees
        review.loc[mask,'uploaded_dob_matches_retained_primary_profile']=agrees
        review.loc[mask,'primary_profile_snapshot_sha256']=row.snapshot_sha256
    review['approved_identity']=False
    review['ml_use_status']=RESTRICTED
    review['model_use_eligible']=False
    review.to_parquet(out/'valuation_verification_identities.parquet',index=False)
    review.to_csv(folder/'identity_review_queue.csv',index=False)
    supported=review[review.supported_review_candidate]
    mapped=set(supported.source_player_id.astype(str))
    relevant=values[values.source_player_id.astype(str).isin(mapped)]
    coverage=relevant.assign(year=relevant.valuation_date.dt.year).groupby('year').agg(records=('source_player_id','size'),players=('source_player_id','nunique'),positive=('market_value_eur',lambda s:int(s.gt(0).sum())),zero=('market_value_eur',lambda s:int(s.eq(0).sum())))
    coverage.to_csv(folder/'date_coverage.csv')
    pd.testing.assert_frame_equal(original,pd.read_parquet(out/'collected_salimt_values.parquet'))
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'git_commit':__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'status':'retained_data_verification_complete_primary_verification_unresolved','input_sha256':inputs,'audit_source_sha256':sha256(Path(__file__)),'git_dirty':bool(__import__('subprocess').check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
        'valuation_records':len(values),'positive_records':int(values.market_value_eur.gt(0).sum()),'zero_ambiguous_records':int(values.market_value_eur.eq(0).sum()),
        'records_without_uploaded_profile':int((~values.profile_present).sum()),'raw_amount_and_effective_date_roundtrip_verified':True,
        'currency_explicit_in_raw_value_file':False,'currency_status':'EUR assumed; not independently confirmed',
        'candidate_pairs':len(review),'supported_pairs':len(supported),'identity_status_counts':review.verification_status.value_counts().to_dict(),
        'uploaded_full_dob_corroborated_by_primary_profile':int(review.uploaded_dob_matches_retained_primary_profile.sum()),'fbref_full_dob_independently_verified':0,'primary_profiles_corroborated':int(review.primary_profile_verified.sum()),'approved_identities':0,'primary_verified_valuation_records':0,
        'publication_timestamp_present_records':int(values.source_publication_known_at.notna().sum()),'historical_budget_eligible_records':0,
        'source_kind':'reported market assessment, not transfer fee','model_use_eligible':False,
        'limits':['Source mapping, profile and club history corroboration is secondary evidence; it is not independent primary-profile verification.',
            'FBref supplies birth year, not a verified full date of birth for these pairs.',
            'Club spellings can differ; no exact overlap is unresolved evidence, not automatic rejection.',
            'Raw value CSV has no explicit currency field; prior EUR normalization is an assumption.',
            'Effective valuation dates do not prove original publication time. Receipt in 2026 is not historical availability.',
            'Two retained primary profiles provide current identity corroboration, not primary verification of the 901,429 older valuation amounts or their publication dates. No source access bypass or automatic approval performed.'],
        'outputs':{}}
    for path in [out/'valuation_verification_records.parquet',out/'valuation_verification_identities.parquet',folder/'identity_review_queue.csv',folder/'date_coverage.csv']:
        report['outputs'][str(path.relative_to(ROOT))]={'sha256':sha256(path),'private':path.suffix=='.parquet' or path.name=='identity_review_queue.csv'}
    (folder/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','valuation_records','positive_records','zero_ambiguous_records','supported_pairs','identity_status_counts','primary_profiles_corroborated','approved_identities','currency_status','publication_timestamp_present_records']},indent=2))


if __name__=='__main__':main()
