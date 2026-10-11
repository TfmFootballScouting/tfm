"""Offline name + context identity trial and explicitly provisional join preview."""
import json
import subprocess
from datetime import datetime, timezone

import pandas as pd

from src.config import ROOT
from src.data.identity import build_crosswalk, code_fingerprint, join_preview, match_identities
from src.data.provenance import sha256
from src.preprocessing.collected import data_dictionary


def run():
    manifest = json.loads((ROOT/'reports/collected_preprocessing.json').read_text())
    tables = {}
    for name in ['collected_player_club_seasons', 'collected_understat_shooters', 'collected_profiles_valuations']:
        item = manifest['outputs'][name]
        path = ROOT / item['path']
        if sha256(path) != item['sha256']:
            raise ValueError(f'Processed dataset changed without provenance update: {name}')
        tables[name] = pd.read_parquet(path)
    mapping_path = ROOT / manifest['inputs']['player_mapping']['path']
    if sha256(mapping_path) != manifest['inputs']['player_mapping']['sha256']:
        raise ValueError('Upstream identity mapping changed without provenance update')
    mapping = pd.read_parquet(mapping_path)
    clubs = tables['collected_player_club_seasons']
    shooters = tables['collected_understat_shooters']
    valuations = tables['collected_profiles_valuations']
    snapshots = []
    for season in sorted(clubs.season.unique()):
        for source, frame in [('understat', shooters), ('transfermarkt', valuations)]:
            snapshot = match_identities(clubs, frame, source, season, mapping)
            snapshots.append(snapshot)
            print(f'{season} {source}: {len(snapshot)} candidate pairs', flush=True)
    trials = pd.concat(snapshots, ignore_index=True)
    crosswalk = build_crosswalk(trials)
    preview = join_preview(clubs, shooters, valuations, crosswalk)
    output_tables = dict(identity_match_trials=trials, identity_crosswalk_proposed=crosswalk,
                         collected_identity_join_preview=preview)
    output = ROOT / 'data/processed/real'
    for name, frame in output_tables.items():
        frame.to_parquet(output / f'{name}.parquet', index=False)
    reports = ROOT / 'reports'
    trials.to_csv(reports/'identity_match_trials.csv', index=False)
    crosswalk.to_csv(reports/'identity_crosswalk_proposed.csv', index=False)
    dictionary = data_dictionary(output_tables)
    descriptions = dict(
        canonical_player_id='Stable FBref-anchored person ID; source IDs are mapped, not renamed',
        season_cutoff='Latest season allowed for identity evidence in this snapshot',
        exact_name='At least one normalized name alias agrees between sources',
        name_similarity='Maximum character/token-sorted similarity across season-bounded name aliases',
        birth_year_agreement='Known source birth-year sets agree; not a full date-of-birth match',
        birth_year_conflict='Known source birth-year sets disagree; proposal blocked',
        profile_conflict='One source reports inconsistent birth years or dates; proposal blocked',
        evidence_score='Heuristic evidence points; not a probability or measured matching accuracy',
        upstream_id_mapping='Pair occurs in the pinned upstream FBref–Transfermarkt ID mapping',
        left_margin='Evidence-score difference from the best competing right identity',
        right_margin='Evidence-score difference from the best competing left identity',
        proposal_status='High-support proposal, unresolved review candidate, or conflicting identity',
        identity_match_status='Provisional or unstable identity link; no manual approval implied',
        unstable_across_cutoffs='Conflicting person assignment observed by this season cutoff',
        club_join_key='Normalized source club with explicit spelling aliases',
        league_join_key='Normalized source league; no cross-league context joins',
        model_eligible='Always false in the unreviewed preview',
        identity_temporal_status='Season-bounded evidence; historical publication dates remain unknown')
    dictionary['description'] = dictionary.field.map(descriptions).fillna(dictionary.description)
    for column in ['name_similarity', 'evidence_score', 'left_margin', 'right_margin']:
        dictionary.loc[dictionary.field.eq(column), 'unit'] = 'ratio [0,1]' if column == 'name_similarity' else 'heuristic points'
    dictionary.to_csv(reports/'identity_resolution_dictionary.csv', index=False)
    coverage = []
    for season, group in preview.groupby('season', sort=True):
        for source in ['understat', 'transfermarkt']:
            coverage.append(dict(season=season, source=source, fbref_club_seasons=len(group),
                joined_club_seasons=int(group[source+'_player_id'].notna().sum()),
                unique_linked_fbref_players=int(group.loc[group[source+'_player_id'].notna(), 'source_player_id'].nunique()),
                approved_links=0))
    coverage = pd.DataFrame(coverage)
    coverage.to_csv(reports/'identity_join_coverage.csv', index=False)
    status = trials.groupby(['right_source', 'season_cutoff', 'proposal_status']).size().rename('pairs').reset_index()
    status.to_csv(reports/'identity_match_status.csv', index=False)
    latest = trials[trials.season_cutoff.eq(trials.season_cutoff.max())]
    code = {name: sha256(ROOT/name) for name in ['src/data/identity.py', 'scripts/identity_resolution.py',
                                              'src/data/matching.py', 'src/data/source_rights.py']}
    version = code_fingerprint(dict(base_dataset_version=manifest['dataset_version'], code=code,
                                   thresholds=dict(fuzzy_name_similarity=.92, minimum_reciprocal_margin=10)))
    result = dict(dataset_version=version, base_dataset_version=manifest['dataset_version'],
        generated_at=datetime.now(timezone.utc).isoformat(),
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        git_source_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain', '--', 'src', 'scripts', 'tests'], cwd=ROOT, text=True).strip()),
        input_manifest_sha256=sha256(ROOT/'reports/collected_preprocessing.json'), code_hashes=code,
        tags={**manifest['tags'], 'dataset_kind': 'real_identity_resolution_trial'},
        parameters=dict(fuzzy_name_similarity=.92, minimum_reciprocal_margin=10,
                        exact_name_points=50, supported_near_name_points=35,
                        club_season_points=20, multiple_overlap_bonus=5,
                        birth_year_points=20, upstream_mapping_points=5),
        canonical_player_id='fbref:<source_player_id>; same across seasons and club transfers',
        score_definition='Heuristic evidence points, not probability or measured matching accuracy',
        latest_cutoff=latest.season_cutoff.max(),
        latest_status_counts=latest.groupby(['right_source', 'proposal_status']).size().to_dict(),
        unstable_proposal_rows=int(crosswalk.unstable_across_cutoffs.sum()), approved_links=0,
        latest_supported_pairs_by_source={source: int(group.proposal_status.eq('high_support_proposal').sum())
                                         for source, group in latest.groupby('right_source')},
        preview_joined_rows={source: int(preview[source+'_player_id'].notna().sum())
                             for source in ['understat', 'transfermarkt']},
        preview_both_sources_rows=int((preview.understat_player_id.notna() & preview.transfermarkt_player_id.notna()).sum()),
        model_retrained=False, source_separated_tables_changed=False,
        outputs={name: dict(rows=len(frame), path=(output/f'{name}.parquet').relative_to(ROOT).as_posix(),
                            sha256=sha256(output/f'{name}.parquet')) for name, frame in output_tables.items()},
        limitations=['Proposals not manually validated; accuracy is unmeasured',
                     'No identity evidence from seasons later than each snapshot cutoff',
                     'Historical publication/profile dates unknown: not strict as-of proof',
                     'No Understat birth dates in the retained extract',
                     'Transfermarkt source-use labels retained; no historical budget eligibility',
                     'Source performance measurements remain separate; no summed cross-provider xG'])
    result['latest_status_counts'] = {f'{source}:{state}': int(count)
                                    for (source, state), count in result['latest_status_counts'].items()}
    (reports/'identity_resolution.json').write_text(json.dumps(result, indent=2)+'\n')
    print(coverage.to_string(index=False))
    print(json.dumps(result['latest_status_counts'], indent=2))
    return result


if __name__ == '__main__':
    run()
