#!/usr/bin/env python3
"""Offline native20 boot pipeline. Fresh outputs; no device, network or publication."""
import argparse,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from toolchain import ROOT,resolve

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(n):return json.loads((ROOT/n).read_text())
def checked(p,d):
 if not p.is_file() or sha(p)!=d:raise ValueError('Missing or changed input: '+str(p))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--busybox-package',required=True,type=Path);p.add_argument('--toolchain-receipt',type=Path);p.add_argument('--preflight',action='store_true');a=p.parse_args()
 locks={k:read(v) for k,v in {'kernel':'packaging/boot-kernel-build.lock.json','dtbh':'packaging/dtbh-build.lock.json','loader':'packaging/public-loader-build.lock.json'}.items()}
 image,receipt=resolve(locks['kernel']['image_id'],a.toolchain_receipt)
 out=a.output.resolve()
 if out.exists():raise ValueError('Output must be new')
 # Rebind historical virtual mount paths to this run's outputs, never old build results.
 aliases={'artifacts/kernel-public-first/additions.tar':out/'additions/additions.tar','local-evidence/boot-provenance-20261012/full-kernel-final/Image':out/'kernel/Image','local-evidence/boot-provenance-20261012/full-kernel-final/exynos9810-star2lte.dtb':out/'kernel/exynos9810-star2lte.dtb','artifacts/header-provenance/third/dt.img':out/'dtbh/dt.img'}
 for n in locks['kernel']['files']:
  if n.startswith('artifacts/boot-provenance/first/'):aliases[n]=out/'boot-inputs'/n.split('artifacts/boot-provenance/first/',1)[1]
 for lock in locks.values():
  for n,d in lock['files'].items():
   if n not in aliases:checked(ROOT/n,d)
 boot=read('packaging/boot-inputs.lock.json');spec=boot['busybox_package']
 if hashlib.new(spec['algorithm'],a.busybox_package.read_bytes()).hexdigest()!=spec['digest']:raise ValueError('BusyBox package mismatch')
 for n,d in boot['files'].items():checked(ROOT/n,d)
 if a.preflight:print(json.dumps({'static_inputs_verified':True,'image_id':image,'derived_inputs':'Must be freshly built and verified before use'}));return
 out.mkdir(parents=True)
 state={'image_id':image,'receipt':receipt,'device_contacted':False,'network':'none in build containers','stages':{},'status':'running'}
 def save():(out/'pipeline.json').write_text(json.dumps(state,indent=2)+'\n')
 def run(name,cmd):
  with (out/(name+'.log')).open('w') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  state['stages'][name]='passed';save()
 def stage(name,lock,recipe):
  target=out/name;target.mkdir()
  cmd=['docker','run','--rm','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','4','--memory','6g']
  mapped={}
  for n,d in lock['files'].items():
   source=aliases.get(n,ROOT/n);checked(source,d);mapped[n]={'source':str(source),'sha256':d};cmd+=['-v',str(source)+':/inputs/'+n+':ro']
  (target/'inputs.json').write_text(json.dumps(mapped,indent=2)+'\n')
  run(name,cmd+['-v',str(target)+':/output',image,'bash','/inputs/'+recipe])
 try:
  save()
  receiptargs=['--toolchain-receipt',str(a.toolchain_receipt.resolve())] if a.toolchain_receipt else []
  run('additions',[sys.executable,'scripts/kernel-repro/prepare-public.py','--archives','artifacts/kernel-source-closure','--output',str(out/'additions')])
  run('boot-inputs',[sys.executable,'scripts/boot-repro/prepare.py','--busybox-package',str(a.busybox_package.resolve()),'--port-archive','artifacts/kernel-source-closure/upstream-port.tar.gz','--output',str(out/'boot-inputs')]+receiptargs)
  stage('dtbh',locks['dtbh'],'build/boot-repro/build-dtbh.sh')
  for n,d in locks['dtbh']['expected'].items():checked(out/'dtbh'/n,d)
  stage('kernel',locks['kernel'],locks['kernel']['recipe'])
  for n,k in [('Image','expected_image_sha256'),('exynos9810-star2lte.dtb','expected_dtb_sha256'),('generated.symvers','expected_symbols_sha256')]:checked(out/'kernel'/n,locks['kernel'][k])
  stage('loader',locks['loader'],'build/boot-repro/build-loader.sh')
  spec=importlib.util.spec_from_file_location('explicit',ROOT/'scripts/boot-repro/explicit-container.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  (out/'loader/boot.img').write_bytes(m.build((out/'loader/uniLoader').read_bytes(),(out/'dtbh/dt.img').read_bytes()))
  for n,d in locks['loader']['expected'].items():checked(out/'loader'/n,d)
  state['status']='passed';state['outputs']={n:sha(out/'loader'/n) for n in locks['loader']['expected']};save()
 except Exception as e:
  state['status']='failed';state['error']=str(e);save();raise
 print(json.dumps(state,indent=2))
if __name__=='__main__':main()
