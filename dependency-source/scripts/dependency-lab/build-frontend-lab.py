#!/usr/bin/env python3
"""Build a private ARM64 session lab from a reconstructed base and pinned packages."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
LOCK=ROOT/'packaging/portal-frontend-lab.lock.json'

def verify(lock,cache):
    result=[];seen=set()
    for row in lock['packages']:
        name=row['filename']
        if not name or Path(name).name!=name or '\\' in name or name in seen:raise ValueError('Unsafe/duplicate package name')
        seen.add(name);p=cache/name
        if p.is_symlink() or not p.is_file():raise ValueError('Missing or linked package: '+name)
        if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Package hash mismatch: '+name)
        result.append(p)
    if not result:raise ValueError('Empty package set')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-receipt',type=Path,required=True);parser.add_argument('--packages',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    lock=json.loads(LOCK.read_bytes());receipt=json.loads(args.base_receipt.read_bytes());image=receipt['image_id']
    if receipt.get('toolchain')!='arch' or receipt.get('inputs',{}).get('lock_sha256')!=lock['base_lock_sha256']:
        raise ValueError('Expected package-reconstructed Arch builder receipt')
    if not re.fullmatch('sha256:[0-9a-f]{64}',image):raise ValueError('Expected immutable base image ID')
    info=json.loads(subprocess.check_output(['docker','image','inspect',image]))[0]
    if info['Architecture']!='arm64' or info['Id']!=image:raise ValueError('Wrong base image')
    files=verify(lock,args.packages)
    if args.output.exists():raise ValueError('Output must be new')
    args.output.mkdir(parents=True);out=args.output.resolve()
    for p in files:shutil.copyfile(p,out/p.name)
    tag='omarchy-s-frontend-base:'+image[7:19]
    subprocess.run(['docker','tag',image,tag],check=True)
    dockerfile='FROM '+tag+'\nCOPY *.pkg.tar.xz /lab-packages/\n'
    dockerfile+='RUN for p in /lab-packages/*.pkg.tar.xz; do tar -xJf "$p" -C / --exclude=".BUILDINFO" --exclude=".PKGINFO" --exclude=".MTREE" --exclude=".INSTALL"; done\n'
    dockerfile+='RUN glib-compile-schemas --strict /usr/share/glib-2.0/schemas\n'
    (out/'Dockerfile').write_text(dockerfile)
    subprocess.run(['docker','build','--platform','linux/arm64','--network','none','--iidfile',str(out/'image-id.txt'),str(out)],check=True)
    built=(out/'image-id.txt').read_text().strip()
    built_info=json.loads(subprocess.check_output(['docker','image','inspect',built]))[0]
    result={'schema':1,'image_id':built_info['Id'],'base_image_id':image,'package_count':len(files),
            'lock_sha256':hashlib.sha256(LOCK.read_bytes()).hexdigest(),'dockerfile_sha256':hashlib.sha256(dockerfile.encode()).hexdigest(),
            'scope':'private headless frontend lab; generated images/packages are not release assets'}
    (out/'frontend-lab.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
