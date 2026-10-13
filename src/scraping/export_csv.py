"""Re-export recorded FBref/Understat archives without changing source CSV hashes.

Optional pyreadr/rdata readers are required only for this archive export, not
for the included-CSV pipeline or app. Transfermarkt CSVs were byte-copy uploads.
"""
import json
from pathlib import Path
import tempfile
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.scraping.raw_inputs import ensure_archive


def read_archive(path):
    import pyreadr
    try:
        tables=pyreadr.read_r(str(path))
        if len(tables)!=1:raise ValueError('Expected one R data frame')
        return next(iter(tables.values()))
    except (pyreadr.custom_errors.LibrdataError, UnicodeDecodeError):
        import rdata
        table=rdata.conversion.convert(rdata.parser.parse_file(path),default_encoding='latin1')
        if not isinstance(table,pd.DataFrame):raise ValueError('Expected one R data frame')
        return table


def main():
    catalog=json.loads((ROOT/'data/raw/source_manifest.json').read_text(encoding='utf8'))
    leagues=['La Liga','Premier League','Bundesliga','Serie A','Ligue 1']
    for record in catalog['raw_csvs']:
        if record['provider']=='transfermarkt':
            if sha256(ROOT/record['path'])!=record['sha256']:
                raise ValueError('Uploaded CSV fingerprint mismatch')
            continue
        archive=dict(path=record['archive_path'],sha256=record['archive_sha256'])
        if ensure_archive(archive)!='verified_existing':
            raise FileNotFoundError('Restore recorded archives with python -m src.scraping.raw_inputs --download')
        frame=read_archive(ROOT/archive['path'])
        if record['provider']=='fbref':
            selected=frame[frame.Comp.isin(leagues)&pd.to_numeric(frame.Season_End_Year).between(2021,2026)]
        else:selected=frame[pd.to_numeric(frame.season).between(2020,2025)]
        with tempfile.TemporaryDirectory() as temporary:
            candidate=Path(temporary)/'export.csv'
            selected.to_csv(candidate,index=False,encoding='utf8',float_format='%.17g')
            if sha256(candidate)!=record['sha256']:
                raise ValueError(f'Export differs from recorded raw CSV: {record["path"]}; nothing replaced')
            (ROOT/record['path']).write_bytes(candidate.read_bytes())
        print('Verified source-preserving export:',record['path'])

if __name__=='__main__':main()
