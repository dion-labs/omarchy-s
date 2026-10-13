#!/usr/bin/env python3
"""Stage the three pinned portal files locally. Never install or activate them."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'usr/local/lib/omarchy-dock/'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def regular(path):
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink input or ancestor')
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Regular input required')
    return path.read_bytes()

def payload(root, binary):
    lock_data = regular(root/'packaging/dock-dependencies.lock.json')
    lock = json.loads(lock_data)
    if lock.get('schema') != 1:
        raise ValueError('Unsupported dependency lock')
    rows = lock['external_files']
    pins = {r['path']: r['sha256'] for r in rows}
    if len(pins) != len(rows):
        raise ValueError('Duplicate dependency path')
    sources = json.loads(regular(root/'packaging/dependency-sources.lock.json'))
    upstream = sources['git_archives'][0]
    builds = json.loads(regular(root/'packaging/header-provenance-builds.lock.json'))
    patch = regular(root/'build/portal-wlr/patch.py')
    if sha(patch) != builds['components']['portal']['inputs']['build/portal-wlr/patch.py']:
        raise ValueError('Patch drift')
    metadata = {'upstream_commit': upstream['commit'], 'version': '0.8.4-omarchy-lifecycle1',
                'binary_sha256': sha(regular(binary)), 'patch_sha256': sha(patch)}
    result = {
        'portal-wlr': (regular(binary), '0755'),
        'portal-LICENSE': (regular(root/'open-source/licenses/dependencies/portal-LICENSE'), '0644'),
        'portal-manifest.json': ((json.dumps(metadata, indent=2)+'\n').encode(), '0644'),
    }
    for name, (data, _) in result.items():
        if sha(data) != pins['/'+PREFIX+name]:
            raise ValueError('Runtime pin mismatch: '+name)
    return result, sha(lock_data)

def stage(root, binary, output):
    root = root.resolve()
    # Resolving the parent also accommodates macOS temporary-directory aliases.
    output = output.parent.resolve()/output.name
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be new')
    files, lock_sha = payload(root, binary)
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.portal-stage-', dir=output.parent))
    try:
        rows = []
        for name, (data, mode) in sorted(files.items()):
            target = PREFIX+name
            dest = work/'rootfs'/target
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            dest.chmod(int(mode, 8))
            os.utime(dest, (0, 0))
            rows.append({'target': target, 'sha256': sha(data), 'mode': mode})
        receipt = {'schema': 1, 'name': 'omarchy-portal', 'activation': 'none',
                   'dependency_lock_sha256': lock_sha, 'files': rows}
        (work/'ownership.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
        (work/'ownership.json').chmod(0o644)
        os.utime(work/'ownership.json', (0, 0))
        if output.exists() or output.is_symlink():
            raise ValueError('Output appeared during staging')
        work.rename(output)
    finally:
        if work.exists():
            shutil.rmtree(work)
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(ROOT, args.binary, args.output), indent=2))
