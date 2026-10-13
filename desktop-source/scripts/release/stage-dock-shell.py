#!/usr/bin/env python3
"""Build and stage the pinned shell privately. Never install or contact a device."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(value):
    p = PurePosixPath(value)
    if not value or p.is_absolute() or any(x in ('', '.', '..') for x in value.split('/')) or '\\' in value:
        raise ValueError('Invalid relative payload path')
    return p


def stage_payload(payload, output, spec):
    """Verify complete builder output before copying into a new, isolated root."""
    payload, output = Path(payload), Path(output)
    if payload.is_symlink() or not payload.is_dir():
        raise ValueError('Payload must be a regular directory')
    if output.exists() or output.is_symlink():
        raise ValueError('Output must not exist')
    prefix = spec['prefix']
    if prefix != '/usr/local/lib/omarchy-dock/omarchy-shell':
        raise ValueError('Unexpected ownership prefix')
    files = {}
    for p in payload.rglob('*'):
        if p.is_symlink():
            raise ValueError('Symlinks are not allowed in payload')
        if p.is_dir():
            continue
        if not stat.S_ISREG(p.stat().st_mode):
            raise ValueError('Nonregular payload file')
        key = p.relative_to(payload).as_posix()
        relative(key)
        if p.stat().st_mode & 0o7000:
            raise ValueError('Special permission bits are not allowed')
        files[key] = p
    manifest = json.loads(files['source-manifest.json'].read_text())
    if manifest['upstream'] != spec['upstream_commit']:
        raise ValueError('Upstream pin mismatch')
    expected = manifest['files']
    for key in expected:
        relative(key)
    if set(files) != set(expected) | {'source-manifest.json'}:
        raise ValueError('Manifest does not exactly cover payload')
    for key, sha in expected.items():
        if digest(files[key]) != sha:
            raise ValueError('Payload hash mismatch')
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.shell-stage-', dir=output.parent))
    try:
        records = []
        for key, source in sorted(files.items()):
            destination = prefix + '/' + key
            target = temp / 'rootfs' / destination.lstrip('/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            mode = stat.S_IMODE(source.stat().st_mode)
            target.chmod(mode)
            os.utime(target, (0, 0))
            records.append({'path': destination, 'sha256': digest(target), 'mode': format(mode, '04o')})
        receipt = {'schema': 1, 'package': spec, 'files': records,
                   'limits': 'Staged files only; no dependencies installed, no live install, no release clearance.'}
        (temp / 'ownership.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        # Refuse an output created while the build was running.
        if output.exists() or output.is_symlink():
            raise ValueError('Output appeared during staging')
        temp.rename(output)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output must not exist')
    spec = json.loads((ROOT / 'packaging/dock-shell.json').read_text())
    with tempfile.TemporaryDirectory(prefix='omarchy-shell-build-') as work:
        payload = Path(work) / 'payload'
        subprocess.run(['python3', str(ROOT / 'scripts/dock-lab/prepare-omarchy-shell.py'),
                        '--upstream', str(args.upstream.resolve()), '--output', str(payload)], check=True,
                       stdout=subprocess.DEVNULL)
        receipt = stage_payload(payload, args.output, spec)
    print(json.dumps({'status': 'staged-only', 'files': len(receipt['files']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
