"""Offline audit of uploaded history ZIPs. Never modifies previous evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import pandas as pd
from src.config import ROOT
from src.data.source_rights import RESTRICTED

RAW = ROOT / 'data/raw/sources/salimt_uploaded/histories'
OUT = ROOT / 'data/processed/real'

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def season_year(series):
    valid = series.astype('string').str.fullmatch(r'\d{2}/\d{2}').fillna(False)
    # Explicit century mapping; retained early seasons never silently become 2080.
    first = pd.to_numeric(series.where(valid).str[:2], errors='coerce').astype('Int64')
    result = first + first.map(lambda x: 1900 if pd.notna(x) and x >= 80 else 2000).astype('Int64')
    following = pd.to_numeric(series.where(valid).str[3:], errors='coerce').astype('Int64')
    return result.where((first + 1).mod(100).eq(following))

def write_dictionary_and_field_coverage():
    rows=[]
    for name in ['performance_history','transfer_history','spain_transfer_context']:
     f=pd.read_parquet(ROOT/f'data/processed/real/collected_salimt_{name}.parquet')
     definitions={'player_id':'Transfermarkt source player identifier; not a reviewed cross-source canonical ID.', 'season':'Normalized season from season_name; distinct observations per season.', 'season_start_year':'Parsed first year of supported YY/YY consecutive season labels.', 'source_row_number':'Original CSV physical record index + header offset, preserving audit lineage.', 'competition_id':'Source competition ID: ES1 La Liga; ES2 Segunda División.', 'team_id':'Source club ID for this performance stint.', 'minutes_played':'Source reported minutes string; missing remains unknown; no per-90 imputation.', 'transfer_fee':'Source reported fee string; zero is not independently verified as a free transfer.', 'value_at_transfer':'Source reported value string; distinct from the transfer fee.', 'transfer_date':'Source reported transfer date; not independently verified publication timestamp.', 'source_publication_known_at':'Unknown source publication date, retained as null to prevent claimed historical availability.', 'first_observed_at_utc':'First local receipt time in UTC; does not establish historical public availability.', 'ml_use_status':'Provider source-use restriction inherited from existing audit.', 'model_use_eligible':'False: review-only source tables; no model authorization.', 'club_context_direction':'Whether matched historical Spanish club was the origin or destination; not player league proof.', 'original_source':'Underlying provider provenance.'}
     for c in f:
      rows.append({'table':name,'column':c,'dtype':str(f[c].dtype),'missing_rows':int(f[c].isna().sum()),'definition':definitions.get(c,'Unmodified source-reported '+c.replace('_',' ')+'; source strings retained without inferred units or missing-value replacement.')})
    pd.DataFrame(rows).to_csv(ROOT/'reports/salimt_history_dictionary.csv',index=False)
    p=pd.read_parquet(ROOT/'data/processed/real/collected_salimt_performance_history.parquet')
    fields=[c for c in p if c not in ['original_source','ml_use_status','model_use_eligible','source_publication_known_at','first_observed_at_utc']]
    quality=[]
    for (season,cid), f in p.groupby(['season','competition_id']):
     for c in fields: quality.append({'season':season,'competition_id':cid,'category':c,'rows':len(f),'missing_rows':int(f[c].isna().sum())})
    pd.DataFrame(quality).to_csv(ROOT/'reports/salimt_history_field_coverage.csv',index=False)

def run(paths=None):
    previous = json.loads((ROOT / 'reports/salimt_uploaded_audit.json').read_text())
    preserved = {**previous['preserved_input_sha256'], **previous['outputs_sha256']}
    for name in ['reports/salimt_uploaded_audit.json', 'reports/salimt_uploaded_verification.json', 'src/data/salimt_uploaded.py', 'scripts/salimt_uploaded_audit.py']:
        preserved[name] = sha(ROOT / name)
    for name, digest in preserved.items():
        if sha(ROOT / name) != digest: raise ValueError(f'Previous evidence changed: {name}')
    RAW.mkdir(parents=True, exist_ok=True)
    receipt_path = RAW / 'receipt.json'
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {'first_preserved_at_utc': datetime.now(timezone.utc).isoformat(), 'files': {}}
    stats, selected = {}, {}
    specs = {'transfer_history': 'file_00000000ce3c8210bcc48f8533f7e5ce', 'player_performances': 'file_00000000b99081f4a75f5035dbc4446c'}
    for name, file_id in specs.items():
        archive, payload = RAW / (name + '.zip'), RAW / (name + '.txt')
        if paths:
            incoming = Path(paths[name])
            if archive.exists() and sha(archive) != sha(incoming): raise ValueError('Changed archive')
            if incoming.resolve() != archive.resolve(): shutil.copyfile(incoming, archive)
        with zipfile.ZipFile(archive) as z:
            files = [i for i in z.infolist() if not i.is_dir()]
            if len(files) != 1 or files[0].filename != name + '.txt': raise ValueError('Unexpected ZIP members')
            if files[0].file_size > 512 * 1024**2: raise ValueError('Payload too large')
            if not payload.exists():
                with z.open(files[0]) as src, payload.open('wb') as dst: shutil.copyfileobj(src, dst)
        hashes = {'archive_sha256': sha(archive), 'payload_sha256': sha(payload), 'archive_bytes': archive.stat().st_size, 'payload_bytes': payload.stat().st_size, 'file_id': file_id}
        if name in receipt['files'] and receipt['files'][name] != hashes: raise ValueError('Raw checksum mismatch')
        receipt['files'][name] = hashes
        total, invalid, missing, season_formats = 0, 0, {}, {}
        parts = []
        for chunk in pd.read_csv(payload, dtype=str, chunksize=100000):
            total += len(chunk)
            years = season_year(chunk.season_name)
            invalid += int(years.isna().sum())
            for label, count in chunk.loc[years.isna(), 'season_name'].fillna('<missing>').value_counts().items(): season_formats[str(label)] = season_formats.get(str(label), 0) + int(count)
            for col in chunk: missing[col] = missing.get(col, 0) + int(chunk[col].isna().sum())
            mask = years.between(2020, 2025).fillna(False)
            if name == 'player_performances': mask &= chunk.competition_id.isin(['ES1', 'ES2'])
            part = chunk.loc[mask].copy()
            part['source_row_number'] = part.index + 2
            part['season_start_year'] = years.loc[mask]
            part['season'] = part.season_start_year.map(lambda y: f'{y}-{y+1}')
            parts.append(part)
        frame = pd.concat(parts, ignore_index=True)
        raw_columns = [c for c in frame if c not in ['source_row_number', 'season_start_year', 'season']]
        stats[name] = {'global_rows': total, 'unsupported_or_missing_season_rows': invalid, 'unparsed_season_labels': season_formats, 'missing_by_column': missing, 'target_rows': len(frame), 'target_exact_duplicate_rows': int(frame.duplicated(raw_columns).sum())}
        frame['original_source'] = 'Transfermarkt.com'
        frame['ml_use_status'] = RESTRICTED
        frame['model_use_eligible'] = False
        frame['source_publication_known_at'] = pd.NaT
        frame['first_observed_at_utc'] = pd.Timestamp(receipt['first_preserved_at_utc'])
        selected[name] = frame
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    perf = selected['player_performances']
    key = ['player_id', 'season', 'competition_id', 'team_id']
    stats['player_performances']['duplicate_grain_rows'] = int(perf.duplicated(key).sum())
    stats['player_performances']['people'] = int(perf.player_id.nunique())
    stats['player_performances']['multiple_club_player_seasons'] = int(perf.groupby(['player_id', 'season']).team_id.nunique().gt(1).sum())
    profiles = pd.read_parquet(OUT / 'collected_salimt_profiles.parquet')
    for name, frame in selected.items(): stats[name]['orphan_profile_people'] = len(set(frame.player_id.dropna()) - set(profiles.source_player_id))
    # Club-season membership identifies transfers touching a Spanish club; it does not establish a player's performance league.
    clubs = pd.read_parquet(OUT / 'collected_salimt_spain_team_seasons.parquet')
    history = selected['transfer_history']
    contexts = []
    for direction in ['from', 'to']:
        lookup = clubs[['club_id', 'season', 'competition_id']].rename(columns={'club_id': direction + '_team_id'})
        joined = history.merge(lookup, on=[direction + '_team_id', 'season'], how='inner', validate='many_to_many')
        joined['club_context_direction'] = direction
        contexts.append(joined)
    transfers = pd.concat(contexts, ignore_index=True)
    coverage = []
    for year in range(2020, 2026):
        for cid in ['ES1', 'ES2']:
            rows = perf[perf.season_start_year.eq(year) & perf.competition_id.eq(cid)]
            context = transfers[transfers.season_start_year.eq(year) & transfers.competition_id.eq(cid)]
            coverage.append({'season': f'{year}-{year+1}', 'competition_id': cid, 'performance_rows': len(rows), 'players': rows.player_id.nunique(), 'teams': rows.team_id.nunique(), 'minutes_missing': int(rows.minutes_played.isna().sum()), 'transfer_event_rows_touching_club': context.source_row_number.nunique(), 'partial_snapshot': year == 2025})
    outputs = {}
    for name, frame in {'performance_history': perf, 'transfer_history': history, 'spain_transfer_context': transfers}.items():
        path = OUT / f'collected_salimt_{name}.parquet'
        frame.to_parquet(path, index=False); outputs[str(path.relative_to(ROOT))] = sha(path)
    coverage_path = ROOT / 'reports/salimt_history_coverage.csv'
    pd.DataFrame(coverage).to_csv(coverage_path, index=False); outputs[str(coverage_path.relative_to(ROOT))] = sha(coverage_path)
    write_dictionary_and_field_coverage()
    for name in ['salimt_history_dictionary.csv', 'salimt_history_field_coverage.csv']:
        path = ROOT / 'reports' / name
        outputs[str(path.relative_to(ROOT))] = sha(path)
    report = {'status': 'offline_audit_complete_model_integration_pending', 'receipt': receipt, 'statistics': stats, 'coverage': coverage, 'preserved_input_sha256': preserved, 'outputs_sha256': outputs, 'code_sha256': sha(Path(__file__)), 'advanced_features_absent': ['shots', 'shots_on_target', 'crosses', 'interceptions', 'tackles_won', 'fouls_committed', 'fouls_drawn', 'xG', 'xAG'], 'limitations': ['Fees and statistics remain reported strings; missing and zero have not been conflated.', 'Transfer context means a club-season match, not a verified player-league assignment.', 'Exact duplicate rows retained and counted; no unsafe aggregation.', '2025/26 is a partial source snapshot.', 'Original publication dates and provider licence unverified; no model retraining or historical budget eligibility granted.']}
    (ROOT / 'reports/salimt_history_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    for name, digest in preserved.items():
        if sha(ROOT / name) != digest: raise ValueError(f'Previous evidence changed: {name}')
    print(json.dumps({'statistics': stats, 'coverage': coverage}, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--transfers'); parser.add_argument('--performances')
    args = parser.parse_args()
    if bool(args.transfers) != bool(args.performances): parser.error('Supply both ZIPs or neither')
    run({'transfer_history': args.transfers, 'player_performances': args.performances} if args.transfers else None)
