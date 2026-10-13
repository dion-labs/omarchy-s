#!/usr/bin/env python3
"""Two clean offline builds from hash-locked local inputs. No device access."""
import argparse, hashlib, json, os, shutil, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def inventory(root):
    result={}
    for p in sorted(root.rglob('*')):
        key=p.relative_to(root).as_posix()
        if p.is_symlink(): result[key]={'link':os.readlink(p)}
        elif p.is_file(): result[key]={'sha256':digest(p),'mode':p.stat().st_mode&0o777}
    return result

def validate_path(root, value):
    if not value or any(part in ('','.','..') for part in value.split('/')) or '\\' in value:
        raise ValueError('Unsafe input path')
    p=root
    for part in value.split('/'):
        p=p/part
        if p.is_symlink(): raise ValueError('Symlink input')
    if not p.is_file(): raise ValueError('Missing input: '+value)
    return p

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('component',choices=['input-seat','aquamarine','portal','mesa'])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--lock',type=Path,default=ROOT/'packaging/header-provenance-builds.lock.json')
    args=p.parse_args()
    lock=json.loads(args.lock.read_text())
    spec=lock['components'][args.component]
    spec_bytes=(json.dumps(spec,indent=2,sort_keys=True)+'\n').encode()
    if args.output.exists(): raise SystemExit('Output must not exist')
    inventory_file=validate_path(ROOT,spec['toolchain_inventory'])
    if digest(inventory_file)!=spec['toolchain_packages_sha256']:
        raise ValueError('Toolchain inventory hash mismatch')
    image=spec['image_id']
    inspected=json.loads(subprocess.check_output(['docker','image','inspect',image]))[0]
    assert inspected['Id']==image and inspected['Architecture']=='arm64'
    args.output.mkdir(parents=True)
    out=args.output.resolve()
    (out/'build-inputs.json').write_bytes(spec_bytes)
    with tempfile.TemporaryDirectory(prefix='omarchy-inputs-') as directory:
        inputs=Path(directory)
        for name,expected in spec['inputs'].items():
            source=validate_path(ROOT,name)
            if digest(source)!=expected: raise ValueError('Input hash mismatch: '+name)
            dest=inputs/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        for trial in ('first','second'):
            target=out/trial;target.mkdir()
            cmd=['docker','run','--rm','--network','none','--cap-drop=ALL',
                 '-e','SOURCE_DATE_EPOCH=1727740800','-e','TZ=UTC','-e','LC_ALL=C','-e','CCACHE_DISABLE=1',
                 '-v',str(inputs)+':/inputs:ro','-v',str(target)+':/out',image,
                 'sh','/inputs/'+spec['recipe']]
            print(args.component+': '+trial,flush=True)
            with (out/(trial+'.log')).open('w') as log:
                subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
        a,b=inventory(out/'first'),inventory(out/'second')
        if not a: raise ValueError('Empty build output')
        result={'component':args.component,'image_id':image,'component_lock_sha256':hashlib.sha256(spec_bytes).hexdigest(),
                'equal_bytes_modes_symlinks':a==b,'outputs':a,
                'differences':sorted(k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)),
                'limits':'Locally identified ARM64 image; consult bound reconstruction inputs for toolchain provenance. No device test or installation.'}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'component':args.component,'matching':a==b,'outputs':len(a)}),flush=True)
        if a!=b: raise SystemExit(1)
if __name__=='__main__': main()
