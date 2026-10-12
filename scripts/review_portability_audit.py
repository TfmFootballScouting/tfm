"""Preserve original archived evidence; generate portable presentation copies."""
import hashlib
import json
import re
from pathlib import Path
from src.config import ROOT

PATTERN=re.compile(r'(?:/workspace/|/home/|/tmp/|(?<![A-Za-z])[A-Za-z]:[\\/])')


def portable(value):
    if isinstance(value,dict):return {k:portable(v) for k,v in value.items()}
    if isinstance(value,list):return [portable(v) for v in value]
    if isinstance(value,str):
        prefix='/workspace/tfm_futbol/'
        if value.startswith(prefix):return value[len(prefix):]
        if PATTERN.search(value):return '[historical machine path omitted; see original hashed record]'
    return value


def main():
    target=ROOT/'reports/teacher_review/portable_archive'
    if target.exists():
        import shutil
        shutil.rmtree(target)
    audit=[]
    for directory in ['models','reports']:
        for source in sorted((ROOT/directory).rglob('*.json')):
            if 'teacher_review' in source.parts:continue
            text=source.read_text(encoding='utf8')
            if not PATTERN.search(text):continue
            original=json.loads(text)
            output=target/source.relative_to(ROOT)
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(portable(original),indent=2)+'\n',encoding='utf8')
            audit.append({'original':str(source.relative_to(ROOT)),'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'presentation_copy':str(output.relative_to(ROOT))})
    path=ROOT/'reports/teacher_review/portability_audit.json'
    path.write_text(json.dumps({'scope':'Tracked-style model/report JSON metadata, excluding review outputs; original records unchanged', 'findings':audit,'count':len(audit),'not_claimed':'Binary archives, arbitrary source logs and native Windows execution are not audited by this metadata sweep'},indent=2)+'\n')
    print('Archived metadata paths:',len(audit))
if __name__=='__main__':main()
