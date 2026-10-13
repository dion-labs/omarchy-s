#!/usr/bin/env python3
"""Verify retained boot license evidence and inventory references; not legal clearance."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
inv=json.loads((ROOT/'packaging/boot-source-inventory.json').read_text())
evidence=json.loads((ROOT/'packaging/boot-license-evidence.json').read_text())
for c in inv['components']:
 if not (ROOT/c['pin']).is_file():raise ValueError('Missing pin: '+c['id'])
 if not c['remaining']:raise ValueError('Missing review disposition')
for e in evidence['records']:
 if hashlib.sha256((ROOT/e['notice']).read_bytes()).hexdigest()!=e['sha256']:raise ValueError('Notice changed: '+e['notice'])
additions=json.loads((ROOT/'packaging/kernel-additions-license-inventory.json').read_text())['files']
expected=json.loads((ROOT/'build/kernel-repro/additions.json').read_text())
if {r['path'] for r in additions}!=set(expected) or len(additions)!=len(expected):raise ValueError('Addition coverage mismatch')
for r in additions:
 e=expected[r['path']]
 if r['sha256']!=e['result_sha256'] or r['source']!=e['source'] or r['patch']!=e.get('patch'):raise ValueError('Addition provenance changed: '+r['path'])
print(json.dumps({'addition_files_verified':len(additions),'components':len(inv['components']),'notices_verified':len(evidence['records']),'publication_cleared':False}))
