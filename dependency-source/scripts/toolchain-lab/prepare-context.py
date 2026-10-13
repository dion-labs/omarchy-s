#!/usr/bin/env python3
"""Prepare a fresh toolchain Docker context exclusively from locked archives."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def validate_name(name):
    if not name or Path(name).name!=name or name in ('.','..') or '\\' in name:
        raise ValueError('Unsafe archive filename')
    return name

def verify_packages(lock, cache):
    found=[];seen=set()
    for item in lock['packages']+lock.get('supplemental',[]):
        name=validate_name(item['filename'])
        if name in seen:raise ValueError('Duplicate archive filename')
        seen.add(name);p=cache/name
        if p.is_symlink() or not p.is_file():raise ValueError('Missing or symlink archive: '+name)
        if item['algorithm'] not in ('sha256','sha512'):raise ValueError('Unsupported digest')
        if hashlib.new(item['algorithm'],p.read_bytes()).hexdigest()!=item['digest']:raise ValueError('Archive hash mismatch: '+name)
        found.append(p)
    return found

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('toolchain',choices=['arch','mesa']);p.add_argument('--packages',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise SystemExit('Output must be new')
    lockpath=ROOT/'packaging/toolchains'/ (a.toolchain+'-archives.lock.json')
    lock=json.loads(lockpath.read_text());files=verify_packages(lock,a.packages)
    a.output.mkdir(parents=True)
    if a.toolchain=='arch':
        subprocess.run([sys.executable,str(ROOT/'scripts/toolchain-lab/assemble-arch.py'),str(lockpath),str(a.packages),str(a.output/'rootfs.tar')],check=True)
    else:
        (a.output/'packages').mkdir()
        for source in files:shutil.copyfile(source,a.output/'packages'/source.name)
    shutil.copyfile(ROOT/'build/toolchains'/(a.toolchain+'.Dockerfile'),a.output/'Dockerfile')
    (a.output/'inputs.json').write_text(json.dumps({'lock_sha256':hashlib.sha256(lockpath.read_bytes()).hexdigest(),'dockerfile_sha256':hashlib.sha256((a.output/'Dockerfile').read_bytes()).hexdigest(),'package_count':len(files),'rootfs_sha256':hashlib.sha256((a.output/'rootfs.tar').read_bytes()).hexdigest() if a.toolchain=='arch' else None},indent=2)+'\n')
if __name__=='__main__':main()
