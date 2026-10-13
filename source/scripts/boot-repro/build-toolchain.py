#!/usr/bin/env python3
"""Prepare/build only the boot pipeline's Mesa ARM64 builder; no phone access."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(root,cache,out):
    if out.exists():raise ValueError('Output must be new')
    lockpath=root/'packaging/toolchains/mesa-archives.lock.json'
    lock=json.loads(lockpath.read_text());files=[];seen=set()
    for item in lock['packages']+lock.get('supplemental',[]):
        name=item['filename']
        if not name or Path(name).name!=name or name in ('.','..') or '\\' in name or name in seen:raise ValueError('Unsafe or duplicate filename')
        seen.add(name);p=cache/name
        if p.is_symlink() or not p.is_file():raise ValueError('Missing or symlink package')
        if item['algorithm'] not in ('sha256','sha512'):raise ValueError('Unsupported digest')
        if hashlib.new(item['algorithm'],p.read_bytes()).hexdigest()!=item['digest']:raise ValueError('Package hash mismatch')
        files.append(p)
    recipe=root/'build/toolchains/mesa.Dockerfile'
    recipe.read_bytes()  # Validate before creating output.
    out.mkdir(parents=True);(out/'packages').mkdir()
    for p in files:shutil.copyfile(p,out/'packages'/p.name)
    shutil.copyfile(recipe,out/'Dockerfile')
    inputs={'lock_sha256':sha(lockpath),'dockerfile_sha256':sha(out/'Dockerfile'),'package_count':len(files),'rootfs_sha256':None}
    (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n');return inputs

def build(out,inputs):
    # No fallback pull: the pinned base must have been acquired explicitly.
    line=next(l for l in (out/'Dockerfile').read_text().splitlines() if l.startswith('FROM '))
    base=line.split()[1]
    info=json.loads(subprocess.check_output(['docker','image','inspect',base]))[0]
    if info['Architecture']!='arm64':raise ValueError('Base must be ARM64')
    subprocess.run(['docker','build','--platform','linux/arm64','--network','none','--pull=false','--iidfile',str(out/'image-id.txt'),str(out)],check=True)
    image=(out/'image-id.txt').read_text().strip()
    info=json.loads(subprocess.check_output(['docker','image','inspect',image]))[0]
    if info['Architecture']!='arm64' or info['Id']!=image:raise ValueError('Built image identity/architecture mismatch')
    receipt={'toolchain':'mesa','image_id':image,'inputs':inputs,'scope':'package-reconstructed boot builder; no device access'}
    (out/'toolchain.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    out=a.output.resolve();inputs=prepare(ROOT,a.packages,out)
    print(json.dumps({'prepared':True,'inputs':inputs} if a.prepare_only else build(out,inputs),indent=2))
if __name__=='__main__':main()
