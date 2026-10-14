#!/usr/bin/env python3
"""Read-only Linux payload inventory and offline adoption rehearsal planner."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ownership', HERE / 'portal-ownership.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
OWNER = 'var/lib/omarchy-s/owners/omarchy-portal.json'
FILES = sorted(policy.TARGETS) + [OWNER]
PARENTS = sorted({'.'} | {str(p) for name in FILES for p in Path(name).parents if str(p) != '.'}, key=lambda p: (p.count('/'), p))
LIMIT = 64 * 1024 * 1024
ATTR_LIMIT = 256 * 1024
FIELDS = {'dev', 'ino', 'mode', 'uid', 'gid', 'nlink', 'size', 'atime_ns', 'mtime_ns', 'ctime_ns'}
GATES = ['trusted-source-and-runtime-evidence', 'fresh-device-identity-and-filesystem-health',
         'running-process-identity-if-present', 'external-ownership-registry-review',
         'durable-baseline-and-journal',
         'private-root-adoption-crash-rehearsal', 'exclusive-revalidation-before-commit']


def metadata(st):
    return {k: getattr(st, 'st_' + k) for k in FIELDS}


def directory(st):
    # Directory atime is irrelevant; no directory entries are enumerated.
    return {k: v for k, v in metadata(st).items() if k != 'atime_ns'}


def open_root(root):
    path = Path(root)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Explicit absolute root without traversal required')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_file(parent, name):
    try:
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > LIMIT:
        raise ValueError('Expected bounded singly linked regular file')
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOATIME, dir_fd=parent)
    try:
        if metadata(os.fstat(fd)) != metadata(before):
            raise ValueError('File changed while opening')
        digest = hashlib.sha256()
        total = 0
        while True:
            data = os.read(fd, min(1024 * 1024, LIMIT + 1 - total))
            if not data:
                break
            total += len(data)
            if total > LIMIT:
                raise ValueError('File grew beyond bound')
            digest.update(data)
        attrs = {}
        attr_size = 0
        for key in sorted(os.listxattr(fd)):
            value = os.getxattr(fd, key)
            attr_size += len(key.encode()) + len(value)
            if attr_size > ATTR_LIMIT:
                raise ValueError('Extended attributes exceed bound')
            attrs[key] = base64.b64encode(value).decode()
        if total != before.st_size or metadata(os.fstat(fd)) != metadata(before) or metadata(os.stat(name, dir_fd=parent, follow_symlinks=False)) != metadata(before):
            raise ValueError('File changed during observation')
        return dict(metadata(before), sha256=digest.hexdigest(), xattrs=attrs)
    finally:
        os.close(fd)


def scan(fd):
    handles = {'.': os.dup(fd)}
    parents = {'.': directory(os.fstat(fd))}
    try:
        for name in PARENTS:
            if name == '.':
                continue
            p = Path(name)
            parent = str(p.parent)
            if parent not in handles:
                parents[name] = None
                continue
            try:
                child = os.open(p.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=handles[parent])
            except FileNotFoundError:
                parents[name] = None
                continue
            handles[name] = child
            parents[name] = directory(os.fstat(child))
        files = {name: read_file(handles[str(Path(name).parent)], Path(name).name)
                 if str(Path(name).parent) in handles else None for name in FILES}
        for name, handle in handles.items():
            if directory(os.fstat(handle)) != parents[name]:
                raise ValueError('Parent changed during observation')
        return {'parents': parents, 'files': files}
    finally:
        for handle in handles.values():
            os.close(handle)


def collect(root):
    if sys.platform != 'linux':
        raise ValueError('Linux O_NOATIME inventory required; no atime-writing fallback')
    fd = open_root(root)
    try:
        first = scan(fd)
        if scan(fd) != first:
            raise ValueError('Inventory changed between observations')
        check = open_root(root)
        try:
            if directory(os.fstat(check)) != first['parents']['.']:
                raise ValueError('Root pathname changed')
        finally:
            os.close(check)
    finally:
        os.close(fd)
    return dict(schema=1, kind='read-only-portal-inventory', observation_id=secrets.token_hex(16), **first)


def validate(value):
    if type(value) is not dict or set(value) != {'schema', 'kind', 'observation_id', 'parents', 'files'} or value['schema'] != 1 or value['kind'] != 'read-only-portal-inventory':
        raise ValueError('Unsupported inventory')
    if not isinstance(value['observation_id'], str) or not re.fullmatch('[0-9a-f]{32}', value['observation_id']):
        raise ValueError('Invalid observation ID')
    for group, names, fields in [('parents', PARENTS, FIELDS - {'atime_ns'}), ('files', FILES, FIELDS | {'sha256', 'xattrs'})]:
        if type(value[group]) is not dict or set(value[group]) != set(names):
            raise ValueError('Incomplete inventory')
        for name, row in value[group].items():
            if row is None:
                continue
            if type(row) is not dict or set(row) != fields or any(type(row[k]) is not int for k in fields & FIELDS):
                raise ValueError('Invalid metadata')
            if row['dev'] < 0 or row['ino'] <= 0 or row['size'] < 0 or row['nlink'] < 1 or row['uid'] < 0 or row['gid'] < 0:
                raise ValueError('Invalid metadata values')
            if group == 'parents':
                if not stat.S_ISDIR(row['mode']):
                    raise ValueError('Non-directory parent')
            else:
                if not stat.S_ISREG(row['mode']) or row['nlink'] != 1 or row['size'] > LIMIT or not isinstance(row['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', row['sha256']):
                    raise ValueError('Invalid regular file')
                if type(row['xattrs']) is not dict or any(not isinstance(k, str) or not isinstance(v, str) for k, v in row['xattrs'].items()):
                    raise ValueError('Invalid xattrs')
                if sum(len(k.encode()) + len(base64.b64decode(v, validate=True)) for k, v in row['xattrs'].items()) > ATTR_LIMIT:
                    raise ValueError('Oversized xattrs')
    if value['parents']['.'] is None:
        raise ValueError('Missing root')
    for group in ('parents', 'files'):
        for name, row in value[group].items():
            if name != '.' and row is not None and value['parents'][str(Path(name).parent)] is None:
                raise ValueError('Impossible ancestry')


def plan(observed, receipt, baseline=None):
    validate(observed)
    expected = policy.ownership(receipt)
    if baseline is not None:
        validate(baseline)
        if any(baseline[k] != observed[k] for k in ('parents', 'files')):
            raise ValueError('Baseline drift; refuse adoption')
    if observed['files'][OWNER] is not None:
        raise ValueError('Existing sidecar; explicit reconciliation required')
    dev = observed['parents']['.']['dev']
    for group in ('parents', 'files'):
        if any(row is not None and row['dev'] != dev for row in observed[group].values()):
            raise ValueError('Cross-filesystem adoption needs separate review')
    for name, identity in expected.items():
        row = observed['files'][name]
        if row is None or {'sha256': row['sha256'], 'mode': format(stat.S_IMODE(row['mode']), '04o')} != identity:
            raise ValueError('Missing or mixed payload: ' + name)
    return {'schema': 1, 'kind': 'offline-adoption-rehearsal-plan', 'commit_authorized': False,
            'inventory_sha256': policy.digest(observed), 'stage_receipt_sha256': policy.digest(receipt),
            'baseline_sha256': policy.digest(baseline), 'payload_mutations': [], 'activation': 'none',
            'proposed_owner_receipt': OWNER, 'required_missing_parents': [p for p in PARENTS if observed['parents'][p] is None],
            'remaining_gates': GATES, 'ownership_conflicts': 'external ownership registries not inspected',
            'entries': [{'target': name, **expected[name], 'action': 'preserve'} for name in sorted(expected)]}


def load(path):
    with open(path, 'rb') as f:
        raw = f.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('JSON input exceeds bound')
    return json.loads(raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inventory = commands.add_parser('inventory')
    inventory.add_argument('--root', required=True)
    planner = commands.add_parser('plan')
    planner.add_argument('--inventory', required=True)
    planner.add_argument('--stage-receipt', required=True)
    planner.add_argument('--baseline')
    args = parser.parse_args()
    result = collect(args.root) if args.command == 'inventory' else plan(load(args.inventory), load(args.stage_receipt), load(args.baseline) if args.baseline else None)
    print(json.dumps(result, indent=2, sort_keys=True))
