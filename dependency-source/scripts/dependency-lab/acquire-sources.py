#!/usr/bin/env python3
"""Acquire hash-pinned dependency inputs; use --cache-root for offline copying."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]

def checked_path(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or relative.as_posix() != name:
        raise ValueError('Unsafe path')
    root = root.resolve()
    path = root / name
    if any(root.joinpath(*relative.parts[:i]).is_symlink() for i in range(1, len(relative.parts) + 1)):
        raise ValueError('Symlink path')
    return path

def verify(path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Input hash mismatch: ' + path.name)

def acquire(root, cache=None):
    lock = json.loads((root/'packaging/dependency-sources.lock.json').read_text())
    for item in lock['archives'] + lock['git_archives']:
        dest = checked_path(root, item['path'])
        if dest.exists():
            verify(dest, item['sha256'])
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='dependency-acquisition-') as tmp:
            temporary = Path(tmp)/'input'
            if cache:
                source = checked_path(cache, item['path'])
                verify(source, item['sha256'])
                shutil.copyfile(source, temporary)
            elif 'url' in item:
                with urllib.request.urlopen(item['url'], timeout=120) as response, temporary.open('wb') as out:
                    shutil.copyfileobj(response, out)
            else:
                repo = Path(tmp)/'repo'
                subprocess.run(['git', 'init', '--bare', str(repo)], check=True, stdout=subprocess.DEVNULL)
                subprocess.run(['git', '-C', str(repo), 'fetch', '--depth=1', item['repository'], item['commit']], check=True)
                subprocess.run(['git', '-C', str(repo), 'archive', '--format=tar', '--output='+str(temporary), item['commit']], check=True)
            verify(temporary, item['sha256'])
            with dest.open('xb') as output, temporary.open('rb') as source:
                shutil.copyfileobj(source, output)
    return len(lock['archives']) + len(lock['git_archives'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-root', type=Path)
    args = parser.parse_args()
    print(json.dumps({'verified_inputs': acquire(ROOT, args.cache_root)}))
