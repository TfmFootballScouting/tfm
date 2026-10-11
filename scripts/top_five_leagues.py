"""Expand retained, checksum-pinned FBref archives to the five top leagues."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.preprocessing.collected import normalize_fbref, aggregate_player_seasons, data_dictionary
from scripts.worldfootballr_archive import ensure_snapshot, read_rds
from src.app.collected import load_collected_service
from src.models.collected import evaluate_pair

LEAGUES = ['La Liga', 'Premier League', 'Bundesliga', 'Serie A', 'Ligue 1']
KEYS = ['source_player_id', 'league', 'season', 'team']
MAPPINGS = {
    'shooting': {'Sh_Standard': 'sh', 'SoT_Standard': 'sot'},
    'defense': {'Int': 'int', 'TklW_Tackles': 'tklw'},
    'misc': {'Crs': 'crs', 'Fls': 'fls', 'Fld': 'fld'},
    'passing': {'Cmp_Total': 'passes_completed', 'Att_Total': 'passes_attempted', 'KP': 'key_passes'},
    'possession': {'Touches_Touches': 'touches', 'Succ_Take': 'successful_take_ons'},
}


def select_rows(frame):
    selected = frame[frame.Comp.isin(LEAGUES) & pd.to_numeric(frame.Season_End_Year).between(2021, 2026)].copy()
    selected['source_player_id'] = selected.Url.str.extract(r'/players/([^/]+)', expand=False)
    selected['team'] = selected.Squad
    selected['league'] = selected.Comp
    selected['season'] = selected.Season_End_Year.map(lambda year: f'{int(year)-1}-{int(year)}')
    if selected[KEYS].isna().any().any() or selected.duplicated(KEYS).any():
        raise ValueError('Missing or conflicting source/league/club/season identity')
    return selected


def align_category(standard, auxiliary, columns):
    joined = standard[KEYS+['Min_Playing']].merge(auxiliary[KEYS+['Mins_Per_90']+list(columns)],
                                                on=KEYS, how='left', validate='one_to_one', indicator=True)
    diff = (pd.to_numeric(joined.Min_Playing, errors='coerce')/90 - pd.to_numeric(joined.Mins_Per_90, errors='coerce')).abs()
    compatible = joined._merge.eq('both') & diff.le(.061)
    joined['category_key_matched'] = joined._merge.eq('both')
    joined['category_exposure_compatible'] = compatible
    for column in columns: joined[column] = pd.to_numeric(joined[column], errors='coerce').where(compatible)
    return joined, joined[KEYS+list(columns)].rename(columns=columns)


def dominant_league_gallery(frame):
    """One source identity per season; keep the highest-minutes league, never blend competitions."""
    return frame.sort_values(['season', 'entity_id', 'minutes', 'league'], ascending=[True, True, False, True])\
        .drop_duplicates(['entity_id', 'season']).sort_values(['season', 'league', 'player_id']).reset_index(drop=True)


def main(download=False):
    destination = ROOT/'reports/top_five_leagues'
    destination.mkdir(exist_ok=True)
    records = [r for r in json.loads((ROOT/'reports/worldfootballr_sources.json').read_text()) if r['original_source']=='fbref']
    tables = {r['category']: select_rows(read_rds(ensure_snapshot(r, download=download))[0]) for r in records}
    standard = tables['standard']
    fields = ['Player','Nation','Pos','Age','Born','Min_Playing','MP_Playing','Gls','Ast','xG_Expected','xAG_Expected']
    base = standard[KEYS+fields].rename(columns={'Player':'player','Nation':'nation','Pos':'pos','Age':'age',
        'Born':'birth_year','Min_Playing':'minutes','MP_Playing':'mp','Gls':'gls','Ast':'ast','xG_Expected':'xg','xAG_Expected':'xag'})
    coverage = []
    for category, columns in MAPPINGS.items():
        aligned, packet = align_category(standard, tables[category], columns)
        base = base.merge(packet, on=KEYS, how='left', validate='one_to_one')
        for league in LEAGUES:
            for start in range(2020, 2026):
                season = f'{start}-{start+1}'
                source = tables[category].query('league == @league and season == @season')
                group = aligned.query('league == @league and season == @season')
                coverage.append(dict(source='fbref_worldfootballr', league=league, season=season, category=category,
                    raw_stints=len(source), standard_stints=len(group), matched=int(group.category_key_matched.sum()),
                    compatible=int(group.category_exposure_compatible.sum()),
                    status='partial' if start==2025 else ('observed_with_missing_or_misaligned' if not group.category_exposure_compatible.all() else 'observed_snapshot')))
    for league in LEAGUES:
        for start in range(2020, 2026):
            rows = standard[standard.league.eq(league) & standard.season.eq(f'{start}-{start+1}')]
            coverage.append(dict(source='fbref_worldfootballr',league=league,season=f'{start}-{start+1}',category='standard',
                raw_stints=len(rows),standard_stints=len(rows),matched=len(rows),compatible=len(rows),status='partial' if start==2025 else 'observed_snapshot'))
    base['source'] = 'fbref_worldfootballr'
    base['provenance_status'] = 'published_secondary_archive'
    base['period_status'] = np.where(base.season.eq('2025-2026'), 'partial_September_2025', 'historical_season_label_completeness_not_guaranteed')
    clubs, issues, removed = normalize_fbref(base)
    seasons = aggregate_player_seasons(clubs)
    dominant = dominant_league_gallery(seasons)
    # Eligibility follows existing measured-feature contracts, not category presence alone.
    outputs = dict(player_club_seasons=clubs, player_seasons=seasons,
        core_gallery=dominant[dominant.tactical_proxy_candidate & ~dominant.partial_season].copy(),
        offensive_gallery=dominant[dominant.baseline_candidate & ~dominant.partial_season].copy())
    output_manifest = {}
    for name, frame in outputs.items():
        path = ROOT/f'data/processed/real/top_five_{name}.parquet'
        frame.to_parquet(path, index=False)
        output_manifest[name] = dict(path=str(path.relative_to(ROOT)),sha256=sha256(path),rows=len(frame))
    pd.DataFrame(coverage).to_csv(destination/'coverage.csv',index=False)
    pd.DataFrame(issues).to_csv(destination/'cleaning.csv',index=False)
    data_dictionary(outputs).to_csv(destination/'dictionary.csv',index=False)
    availability = []
    metrics = []
    for name in ['core','offensive']:
        gallery = outputs[f'{name}_gallery']
        model = load_collected_service(name).model
        for (league,season), group in gallery.groupby(['league','season']):
            availability.append(dict(model=name,league=league,season=season,players=len(group),
                                     offered=len(group)>=10,advanced_variables_missing=int(group[model.artifacts.feature_cols].isna().sum().sum())))
        previous_season, future_season = ('2022-2023','2023-2024') if name=='core' else ('2023-2024','2024-2025')
        for league in LEAGUES:
            previous=gallery[gallery.league.eq(league)&gallery.season.eq(previous_season)]
            future=gallery[gallery.league.eq(league)&gallery.season.eq(future_season)]
            summary, _ = evaluate_pair(model,previous,future,'external_league_profile_retrieval')
            metrics.append(summary.assign(model=name,league=league,selected_method=summary.method.eq(model.neighbor_method)))
    pd.DataFrame(availability).to_csv(destination/'availability.csv',index=False)
    pd.concat(metrics,ignore_index=True).to_csv(destination/'evaluation.csv',index=False)
    version = sha256(ROOT/output_manifest['player_seasons']['path'])
    report=dict(created_at=datetime.now(timezone.utc).isoformat(),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        code_sha256={name:sha256(ROOT/name) for name in ['scripts/top_five_leagues.py','src/app/leagues.py','src/app/presentation.py','src/app/streamlit_app.py','src/app/scenarios.py','src/app/scenario_ui.py']},
        dataset_version=version,leagues=LEAGUES,outputs=output_manifest,raw_sources=records,exact_duplicates_removed=removed,
        cross_league_person_seasons=int(seasons.duplicated(['entity_id','season'],keep=False).sum()),
        dominant_league_rule='highest observed minutes; ties league name ascending; choose before feature eligibility; no cross-league summation',
        model_training='existing frozen La Liga models, no refit; extra leagues evaluated on same-player next-season retrieval proxy',
        budget_coverage='Existing supported provisional links only; unmatched foreign identities remain unknown',
        season_2025_2026='partial archive, never offered',
        source_rights='Same retained secondary archives and existing model-use policy; no new provider collection or licensing claim',
        report_sha256={path.name:sha256(path) for path in destination.glob('*.csv')})
    (destination/'manifest.json').write_text(json.dumps(report,indent=2))
    print(pd.DataFrame(availability).to_string(index=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true',help='Restore missing pinned FBref archives only; checksum mismatch stops')
    main(download=parser.parse_args().download)
