#!/usr/bin/env python3
"""Pure portal ownership/rollback planner over offline inventories; no file mutation."""
import argparse
import hashlib
import json
from pathlib import Path
import re

PREFIX = 'usr/local/lib/omarchy-dock/'
TARGETS = {PREFIX+'portal-wlr': '0755', PREFIX+'portal-LICENSE': '0644',
           PREFIX+'portal-manifest.json': '0644'}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def identity(value, target):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {'sha256', 'mode'}:
        raise ValueError('Expected regular-file hash/mode identity')
    if not isinstance(value['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', value['sha256']):
        raise ValueError('Invalid content hash')
    if value['mode'] != TARGETS[target]:
        raise ValueError('Unexpected file mode')
    return dict(value)

def ownership(receipt):
    if receipt.get('schema') != 1 or receipt.get('name') != 'omarchy-portal' or receipt.get('activation') != 'none':
        raise ValueError('Unsupported owner receipt')
    result = {}
    for row in receipt['files']:
        if set(row) != {'target', 'sha256', 'mode'}:
            raise ValueError('Unexpected receipt fields')
        name = row['target']
        if name not in TARGETS or name in result:
            raise ValueError('Overlapping or outside ownership')
        result[name] = identity({k: row[k] for k in ('sha256', 'mode')}, name)
    if set(result) != set(TARGETS):
        raise ValueError('Incomplete owner receipt')
    return result

def inventory(observed):
    if not isinstance(observed, dict) or set(observed) != set(TARGETS):
        raise ValueError('Inventory must explicitly cover all three files')
    return {name: identity(value, name) for name, value in observed.items()}

def plan(previous, candidate, observed):
    new = ownership(candidate)
    old = ownership(previous) if previous is not None else dict.fromkeys(TARGETS)
    current = inventory(observed)
    # Existing files cannot be adopted, even when their bytes equal the candidate.
    if current != old:
        raise ValueError('Unowned destination or installed-owner drift')
    entries = [{'target': name, 'before': old[name], 'after': new[name],
                'action': 'unchanged' if old[name] == new[name] else 'create' if old[name] is None else 'replace'}
               for name in sorted(TARGETS)]
    return {'schema': 1, 'owner': 'omarchy-portal', 'kind': 'offline-plan-only',
            'previous_receipt_sha256': digest(previous), 'candidate_receipt_sha256': digest(candidate),
            'entries': entries}

def validate_plan(value):
    if value.get('schema') != 1 or value.get('owner') != 'omarchy-portal' or value.get('kind') != 'offline-plan-only':
        raise ValueError('Unsupported plan')
    names = set()
    for row in value['entries']:
        if set(row) != {'target', 'before', 'after', 'action'}:
            raise ValueError('Unexpected plan fields')
        name = row['target']
        if name not in TARGETS or name in names:
            raise ValueError('Plan ownership mismatch')
        names.add(name)
        before, after = identity(row['before'], name), identity(row['after'], name)
        if after is None:
            raise ValueError('Deletion is unsupported')
        expected = 'unchanged' if before == after else 'create' if before is None else 'replace'
        if row['action'] != expected:
            raise ValueError('Inconsistent action')
    if names != set(TARGETS):
        raise ValueError('Incomplete plan')

def check(value, observed, phase):
    validate_plan(value)
    current = inventory(observed)
    if phase not in ('before-apply', 'before-rollback'):
        raise ValueError('Unsupported phase')
    result = []
    for row in value['entries']:
        state = current[row['target']]
        allowed = (row['before'],) if phase == 'before-apply' else (row['before'], row['after'])
        if state not in allowed:
            raise ValueError('Concurrent drift; refuse entire operation')
        if phase == 'before-rollback' and state != row['before']:
            result.append({'target': row['target'], 'action': 'restore-verified-backup' if row['before'] else 'remove-created-file',
                           'expected_current': row['after'], 'restore': row['before']})
    return list(reversed(result))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--observed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = plan(json.loads(args.previous.read_text()) if args.previous else None,
                  json.loads(args.candidate.read_text()), json.loads(args.observed.read_text()))
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print('Offline plan written; no target files read or changed')
