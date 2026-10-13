#!/usr/bin/env python3
"""Check the dock source inventory and scoped license grants without activation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def check(root):
    plan=json.loads((root/'packaging/dock-source-export.allowlist.json').read_text())
    ledger=json.loads((root/'packaging/dock-source-attribution.json').read_text())
    selected={r['path']:r for r in plan['files']}
    rows={r['path']:r for r in ledger['files']}
    if len(selected)!=len(plan['files']) or len(rows)!=len(ledger['files']):raise ValueError('Duplicate path')
    if set(rows)|{'packaging/dock-source-attribution.json'}!=set(selected):raise ValueError('Coverage mismatch')
    for path,record in selected.items():
        if Path(path).is_absolute() or '..' in Path(path).parts or any(x in Path(path).parts for x in ('artifacts','backups','local-evidence','.git')) or path.endswith('allowed-inputs.json'):raise ValueError('Private or unsafe path')
        f=root/path
        if f.is_symlink() or hashlib.sha256(f.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Source hash mismatch: '+path)
    for path,row in rows.items():
        if row['sha256']!=selected[path]['sha256']:raise ValueError('Ledger hash mismatch')
        inherited=row['classification']=='verified-upstream-MIT'
        if row['classification'] not in ('verified-upstream-MIT','local-expression','mixed-upstream-adaptation'):raise ValueError('Unreviewed classification')
        if row.get('original_license')!=(None if inherited else 'MIT'):raise ValueError('Invalid original grant')
        if not inherited and row.get('original_copyright')!='Copyright (c) 2026 DionLabs':raise ValueError('Invalid holder')
        if not row.get('review_basis'):raise ValueError('Missing review basis')
        if row['classification']!='local-expression' and not row.get('upstream_evidence'):raise ValueError('Missing upstream evidence')
    services=json.loads((root/'packaging/dock-services.json').read_text())
    for row in services['files']:
        if row['source'] not in selected or row['sha256']!=selected[row['source']]['sha256']:raise ValueError('Service pin mismatch')
    return {'files':len(selected),'service_sources':len(services['files']),'inherited_files':sum(r['classification']=='verified-upstream-MIT' for r in rows.values()),'mixed_files':sum(r['classification']=='mixed-upstream-adaptation' for r in rows.values()),'runtime_tested':False}
if __name__=='__main__':print(json.dumps(check(ROOT),indent=2))
