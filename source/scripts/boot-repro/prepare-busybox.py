#!/usr/bin/env python3
"""Verify Ubuntu BusyBox sources and reconstruct its static configuration offline."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from toolchain import ROOT,resolve
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archives',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--toolchain-receipt',type=Path);a=p.parse_args()
lock=json.loads((ROOT/'packaging/busybox-source.lock.json').read_text())
for entry in lock['packages']:
 if hashlib.new(entry['algorithm'],(a.archives/entry['filename']).read_bytes()).hexdigest()!=entry['digest']:raise ValueError('Source archive mismatch: '+entry['filename'])
if hashlib.sha256((ROOT/'build/boot-repro/prepare-busybox.sh').read_bytes()).hexdigest()!=lock['recipe_sha256']:raise ValueError('Recipe changed')
image,_=resolve(json.loads((ROOT/'packaging/boot-inputs.lock.json').read_text())['image_id'],a.toolchain_receipt)
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
cmd=['docker','run','--rm','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','4','--memory','2g']
for entry in lock['packages']:cmd+=['-v',str((a.archives/entry['filename']).resolve())+':/inputs/'+entry['filename']+':ro']
cmd+=['-v',str(ROOT/'build/boot-repro/prepare-busybox.sh')+':/recipe:ro','-v',str(out)+':/output',image,'bash','/recipe']
subprocess.run(cmd,check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,key in [('static.config','expected_static_config_sha256'),('applets.txt','expected_applets_sha256')]:
 if sha(out/name)!=lock[key]:raise ValueError('Configuration or applet mismatch: '+name)
report={'source_version':lock['source_version'],'signature_status':lock['signature_status'],'image_id':image,'static_config_matches_package':True,'device_contacted':False,'binary_reproduction_claimed':False,'outputs':{n:sha(out/n) for n in ['static.config','rules','control','copyright','changelog','patch-series','applets.txt','busybox-rebuilt','applied-source.tar']}}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
