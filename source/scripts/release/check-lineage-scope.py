#!/usr/bin/env python3
"""Validate lineage evidence; optional offline replay never contacts a device/network."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
ROOT = Path(__file__).resolve().parents[2]
def sha(data):
    return hashlib.sha256(data).hexdigest()
def check(root, evidence=None):
    candidate = json.loads((root / 'packaging/dts-authored-candidate.json').read_text())
    lock = json.loads((root / 'packaging/dtbh-build.lock.json').read_text())
    history = json.loads((root / 'packaging/vendor-dts-history.json').read_text())
    expected = {'artifacts/header-provenance/vendor-source.tar.gz',
                'build/boot-repro/build-dtbh.sh', 'scripts/boot-repro/pack-dtbh.py',
                'packaging/dtbh-profile.json'}
    if set(lock['files']) != expected or set(lock['sources']) != {'vendor'}:
        raise ValueError('Independent DTBH input boundary mismatch')
    for path in expected - {'artifacts/header-provenance/vendor-source.tar.gz'}:
        if sha((root / path).read_bytes()) != lock['files'][path]:
            raise ValueError('Independent DTBH source hash mismatch')
    if candidate['publication_cleared'] is not False:
        raise ValueError('Evidence cannot assert clearance')
    if candidate['introduced_target_sha256'] != history['introduced_sha256']:
        raise ValueError('DTS target identity mismatch')
    paths = [r['path'] for r in candidate['files']]
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate candidate path')
    for path in paths:
        if PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts or '\\' in path:
            raise ValueError('Unsafe candidate path')
    for edge in candidate['includes']:
        if edge['from'] not in paths or edge['to'] not in paths:
            raise ValueError('Candidate include missing')
    board_rows = [r for r in candidate['files'] if r['path'] == candidate['board']]
    if len(board_rows) != 1 or board_rows[0]['sha256'] != candidate['candidate_board_sha256']:
        raise ValueError('Candidate board identity mismatch')
    if evidence:
        for row in candidate['files']:
            if sha((evidence / 'candidate' / row['path']).read_bytes()) != row['sha256']:
                raise ValueError('Candidate input hash mismatch')
    return {'dtbh_inputs': len(expected), 'dtbtool_patch_inputs': 0,
            'candidate_files': len(paths), 'generated_inputs_unresolved': len(candidate['generated_inputs']),
            'local_replay': evidence is not None, 'publication_cleared': False}
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-evidence', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(ROOT, args.local_evidence), indent=2))
if __name__ == '__main__':
    main()
