#!/usr/bin/env python3
"""Compare a saved package inventory with observed pins. Never install or connect."""
import argparse
import hashlib
import tarfile
import json
from pathlib import Path


def compare(lock, inventory):
    packages = {}
    for line in inventory.splitlines():
        name, version = line.split(' ', 1)
        if name in packages: raise ValueError('Duplicate inventory entry')
        packages[name] = version
    missing = sorted(set(lock['packages']) - packages.keys())
    changed = sorted(name for name, version in lock['packages'].items()
                     if name in packages and packages[name] != version)
    return {'package_versions_match': not missing and not changed,
            'missing': missing, 'changed': changed,
            'external_binaries_verified': False,
            'runtime_ready': False,
            'limits': 'Version comparison only; no binary, configuration or runtime validation.'}


def compare_external(lock, archive_path):
    # Read named regular members only. Never extract a recovery/configuration archive.
    missing, changed = [], []
    with tarfile.open(archive_path) as archive:
        members = {}
        required = {item['path'].lstrip('/') for item in lock['external_files']}
        for member in archive.getmembers():
            if member.name not in required: continue
            if member.name in members:
                raise ValueError('Duplicate checkpoint member')
            members[member.name] = member
        for item in lock['external_files']:
            name = item['path'].lstrip('/')
            member = members.get(name)
            if member is None or not member.isfile():
                missing.append(item['path']); continue
            h = hashlib.sha256()
            with archive.extractfile(member) as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''): h.update(chunk)
            if h.hexdigest() != item['sha256']: changed.append(item['path'])
    return {'saved_external_inputs_match': not missing and not changed,
            'missing_external_inputs': missing, 'changed_external_inputs': changed}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, help='Optional saved integration tar; read only, never extracted')
    args = p.parse_args()
    lock = json.loads((Path(__file__).resolve().parents[2]/'packaging/dock-dependencies.lock.json').read_text())
    report = compare(lock, args.inventory.read_text())
    if args.checkpoint:
        report.update(compare_external(lock, args.checkpoint))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['package_versions_match'] and report.get('saved_external_inputs_match', True) else 1)

if __name__ == '__main__': main()
