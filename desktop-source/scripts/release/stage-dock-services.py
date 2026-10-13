#!/usr/bin/env python3
"""Stage allowlisted dock service sources locally; no activation or device access."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PREFIX = '/usr/local/lib/omarchy-dock/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('Unsafe path')
    return PurePosixPath(value)


def regular_source(root, relative):
    path = root
    for part in safe_relative(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Source symlink rejected')
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Source must be regular')
    return path


def stage(root, output, spec, lock):
    root, output = Path(root), Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Output must not exist')
    if spec.get('schema') != 1 or lock.get('schema') != 1:
        raise ValueError('Unsupported manifest schema')
    records, seen = [], set()
    for item in spec['files']:
        source = item['source']
        if not source.startswith('build/arch-arm/dock/'):
            raise ValueError('Source outside public runtime boundary')
        path = regular_source(root, source)
        target = item['target']
        if not target.startswith(PREFIX):
            raise ValueError('Target outside package ownership')
        rel = str(safe_relative(target[1:]))
        if target in seen or target.startswith(PREFIX+'omarchy-shell/') or target.endswith('/allowed-inputs.json'):
            raise ValueError('Conflicting or private destination')
        seen.add(target)
        data = path.read_bytes()
        if sha(data) != item['sha256']:
            raise ValueError('Pinned source changed: '+source)
        mode = int(item['mode'], 8)
        if mode not in (0o644, 0o755):
            raise ValueError('Unsupported mode')
        if path.suffix == '.py':
            compile(data, source, 'exec')  # syntax only; never import runtime
        records.append((rel, data, mode, item))
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.dock-services-', dir=output.parent))
    try:
        for rel, data, mode, _ in records:
            p = work/'rootfs'/rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data); p.chmod(mode); os.utime(p, (0, 0))
        lock_bytes = (json.dumps(lock, indent=2, sort_keys=True)+'\n').encode()
        (work/'dependencies.lock.json').write_bytes(lock_bytes)
        receipt = {'schema': 1, 'name': spec['name'], 'activation': 'none',
                   'dependency_lock_sha256': sha(lock_bytes),
                   'files': [i for _, _, _, i in sorted(records)],
                   'limits': 'Source staging only; external binaries/configuration and runtime checks required.'}
        (work/'ownership.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
        if output.exists() or output.is_symlink():
            raise ValueError('Output appeared while staging')
        work.rename(output)
    finally:
        if work.exists(): shutil.rmtree(work)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    spec = json.loads((ROOT/'packaging/dock-services.json').read_text())
    lock = json.loads((ROOT/'packaging/dock-dependencies.lock.json').read_text())
    receipt = stage(ROOT, args.output, spec, lock)
    print(json.dumps({'status': 'staged-only', 'sources': len(receipt['files'])}))

if __name__ == '__main__': main()
