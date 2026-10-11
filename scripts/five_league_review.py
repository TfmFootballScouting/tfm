"""Private cross-source review and reported-price scenarios, never training input."""
import json
from dataclasses import asdict
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.data.salimt_uploaded import propose_identities, identity_preview
from src.data.source_rights import require_model_data_use
from src.app.budget import load_budget_inputs, candidate_links
from src.app.scenarios import Requirements,TEMPLATES,analyze_scenario
from src.app.trained import load_trained_service


def main():
    output=ROOT/'reports/five_league_pipeline'
    pipeline=json.loads((output/'pipeline.json').read_text())
    fbref=pd.read_parquet(ROOT/pipeline['outputs']['player_seasons']['path'])
    values,_,_=load_budget_inputs()
    uploaded=json.loads((ROOT/'reports/salimt_uploaded_audit.json').read_text())
    profile_path='data/processed/real/collected_salimt_profiles.parquet'
    assert sha256(ROOT/profile_path)==uploaded['outputs_sha256'][profile_path]
    profiles=pd.read_parquet(ROOT/profile_path)
    mapping_path='data/external/worldfootballr/player_mapping.parquet'
    assert sha256(ROOT/mapping_path)==pipeline['preserved_sha256'][mapping_path]
    mapping=pd.read_parquet(ROOT/mapping_path)
    candidates=propose_identities(profiles,fbref,mapping)
    preview=identity_preview(fbref,profiles,candidates)
    candidates['model_use_eligible']=False
    for frame in [preview,candidates]:
        try: require_model_data_use(frame)
        except ValueError: pass
        else: raise ValueError('Provisional review rows unexpectedly admitted to models')
    files={}
    for name,frame in [('candidates',candidates),('preview',preview)]:
        path=ROOT/f'data/processed/real/europe_review_{name}.parquet'
        frame.to_parquet(path,index=False)
        files[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha256(path),rows=len(frame))
    supported=candidates[candidates.supported_review_candidate]
    coverage=[];cases=[];tables={key:[] for key in ['funnel','baselines','sensitivity','shortlist']}
    for model in ['core','offensive']:
        service=load_trained_service(model)
        for season in service.available_seasons:
            rec=service.for_season(season)
            links=candidate_links(rec.players,candidates,fbref)
            from src.app.budget import attach_reported_values
            priced=attach_reported_values(rec.players,links,values,f'{season[5:]}-06-30')
            for league,group in priced.groupby('league'):
                coverage.append(dict(model=model,league=league,season=season,players=len(group),
                    provisional_links=int(group.price_source_player_id.notna().sum()),
                    positive_values=int(group.reported_value_screenable.sum()),historical_budget_eligible=False))
        for season in [service.info['validation_season'],service.info['holdout_season']]:
            rec=service.for_season(season);links=candidate_links(rec.players,candidates,fbref)
            for label,template in TEMPLATES.items():
                if template['style'] not in service.supported_styles:continue
                # All five league pools, one hypothetical vacancy each; source values stay provisional.
                for league in ['La Liga','Premier League','Bundesliga','Serie A','Ligue 1']:
                    req=Requirements('Valencia',season,**template,league=league)
                    result=analyze_scenario(rec,req,links,values)
                    case=f'{model}:{season}:{league}:{req.style}'
                    cases.append(dict(case_id=case,label=label,requirements=asdict(req),returned=len(result['shortlist']),eligible=len(result['eligible'])))
                    for key in tables:tables[key].append(result[key].assign(case_id=case,model=model))
    for key,frames in tables.items():
        filename='scenario_shortlists.csv' if key=='shortlist' else f'scenario_{key}.csv'
        pd.concat(frames,ignore_index=True).to_csv(output/filename,index=False)
    pd.DataFrame(coverage).to_csv(output/'price_coverage.csv',index=False)
    report=dict(dataset_version=pipeline['dataset_version'],outputs=files,proposed_pairs=len(candidates),
        supported_provisional_pairs=len(supported),approved_identity_pairs=0,review_rows=len(preview),
        source_joins='upstream source-ID mapping plus exact normalized name and unambiguous birth-year agreement; no automatic approval',
        historical_budget_eligible=False,model_use_eligible=False,cases=cases,
        code_sha256=sha256(ROOT/'scripts/five_league_review.py'),
        reports_sha256={p.name:sha256(p) for p in output.glob('scenario_*.csv')},price_coverage_sha256=sha256(output/'price_coverage.csv'))
    (output/'review.json').write_text(json.dumps(report,indent=2))
    print(dict(supported_provisional_pairs=len(supported),scenarios=len(cases),total_returned=sum(c['returned'] for c in cases)))

if __name__=='__main__':main()
