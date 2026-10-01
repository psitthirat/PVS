"""Check the proposed public file set, without changing the Git index.

Reads tracked and non-ignored untracked files. Checks known private paths,
respondent identifiers in CSV headers, notebook outputs and credential formats.
This is a bounded file check, not a guarantee of arbitrary secret detection.
"""
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BLOCKED_COLUMNS={'id_response','id_collector','ip_address','email','fname','lname','start','end'}
SECRET_PATTERNS=[re.compile(p) for p in [r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{40,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']]


def main():
    raw=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT)
    names=sorted(set(p.decode() for p in raw.split(b'\0') if p))
    errors=[];manifest=[]
    for name in names:
        path=ROOT/name
        if not path.exists():
            errors.append(f'Tracked file missing: {name}');continue
        if path.is_symlink():errors.append(f'Symlink in public set: {name}')
        if (name.startswith(('output/','archive/','.venv/')) or
            name.startswith('data/') and name!='data/README.md' or
            name.startswith('site/') and path.suffix.lower() in {'.doc','.docx','.pdf'} or
            path.suffix.lower() in {'.pkl','.pickle','.xlsx'} or path.name.startswith('.env')):
            errors.append(f'Private/working file in public set: {name}')
        content=path.read_bytes()
        if path.suffix=='.csv':
            with path.open(encoding='utf-8-sig',newline='') as stream:header=next(csv.reader(stream),[])
            if BLOCKED_COLUMNS.intersection(c.lower().strip() for c in header):
                errors.append(f'Respondent identifiers in CSV header: {name}')
        if path.suffix=='.ipynb':
            cells=json.loads(content)['cells']
            if any(c.get('outputs') or c.get('execution_count') is not None or c.get('attachments') for c in cells):errors.append(f'Saved notebook data: {name}')
        if path.suffix.lower() in {'.py','.md','.json','.csv','.js','.html','.yml','.yaml','.txt','.cff','.toml'}:
            text=content.decode('utf-8-sig')
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):errors.append(f'Credential pattern: {name}')
        manifest.append({'path':name,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    if errors:raise ValueError('\n'.join(errors))
    # Locally this is a private review aid. CI only checks, without writing it.
    evidence=ROOT/'output/precommit_review_20261001'
    if evidence.is_dir():
        (evidence/'public-file-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(f'Public file check passed: {len(manifest)} files; no private input/output paths, respondent CSV identifiers, saved notebook results or known credential patterns. Git index unchanged.')

if __name__=='__main__':main()
