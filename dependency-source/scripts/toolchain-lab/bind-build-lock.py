#!/usr/bin/env python3
"""Bind locally rebuilt toolchain receipts to a new candidate dependency lock."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--base-lock',type=Path,default=ROOT/'packaging/header-provenance-builds.lock.json',help='Source recipe lock; defaults to package-derived Weston headers')
p.add_argument('--arch-receipt',type=Path,required=True);p.add_argument('--mesa-receipt',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise SystemExit('Output must not exist; never overwrite known-good locks')
receipts={}
for name,path in [('arch',a.arch_receipt),('mesa',a.mesa_receipt)]:
 r=json.loads(path.read_text());assert r['toolchain']==name
 lock=ROOT/'packaging/toolchains'/(name+'-archives.lock.json')
 recipe=ROOT/'build/toolchains'/(name+'.Dockerfile')
 assert r['inputs']['lock_sha256']==hashlib.sha256(lock.read_bytes()).hexdigest(),'Archive lock changed'
 assert r['inputs']['dockerfile_sha256']==hashlib.sha256(recipe.read_bytes()).hexdigest(),'Recipe changed'
 info=json.loads(subprocess.check_output(['docker','image','inspect',r['image_id']]))[0]
 assert info['Id']==r['image_id'] and info['Architecture']=='arm64'
 receipts[name]=r
candidate=json.loads(a.base_lock.read_text())
for name,spec in candidate['components'].items():
 receipt=receipts['mesa' if name=='mesa' else 'arch'];spec['image_id']=receipt['image_id'];spec['reconstruction_inputs']=receipt['inputs']
candidate['scope']='Candidate bound to locally rebuilt package-only toolchains; no device activation'
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(candidate,indent=2)+'\n')
print(a.output)
