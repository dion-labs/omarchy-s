#!/usr/bin/env python3
"""Host-only Linux and Docker capture acceptance from an exact exported source tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import secrets
import stat
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
CASES=[('scripts/release/test-private-builds.py',4),('scripts/toolchain-lab/test-inputs.py',6),('scripts/toolchain-lab/test-weston-headers.py',3)]
CASES += [('scripts/dependency-lab/test-'+name+'.py',count) for name,count in [
 ('native-usb',3),('acquire-sources',2),('stage-portal',6),('portal-ownership',7),('portal-transaction',18),
 ('portal-retention',11),('portal-lifecycle',10),('portal-child',9),('portal-session',8),('frontend-lab-inputs',4),
 ('portal-frontend',12),('portal-admission',12),('portal-fence',19),('portal-scope',5),('acceptance',6)]]
HOST=('scripts/dependency-lab/test-portal-scope-host.py',2)
PIN='e3c43847acc34cd113f101087de3c113e7ae821c933515b0c55b2c92cbb7eb3b'

def sha(data):return hashlib.sha256(data).hexdigest()
def verify_tree(root,manifest,digest):
 for entry in root.rglob('*'):
  if entry.is_symlink():raise ValueError('Source symlink')
 raw=manifest.read_bytes()
 if sha(raw)!=digest:raise ValueError('Manifest hash differs')
 rows=json.loads(raw)['files'];names=set()
 for row in rows:
  name=row['path'];p=PurePosixPath(name)
  if not name or p.is_absolute() or '..' in p.parts or '\\' in name or name in names:raise ValueError('Unsafe/duplicate source member')
  names.add(name);file=root/name
  if file.is_symlink() or not file.is_file() or stat.S_IMODE(file.stat().st_mode)!=0o644 or sha(file.read_bytes())!=row['sha256']:raise ValueError('Source identity differs: '+name)
 actual=set()
 for p in root.rglob('*'):
  if p.is_symlink():raise ValueError('Source symlink')
  if p.is_file():actual.add(p.relative_to(root).as_posix())
 if actual!=names:raise ValueError('Source membership differs')
 return len(names)

def validate_result(value,count):
 keys={'tests','failures','errors','skips','expected_failures','unexpected_successes'}
 if type(value) is not dict or set(value)!=keys or any(type(v) is not int or v<0 for v in value.values()):raise ValueError('Invalid test result')
 if value['tests']!=count or any(value[k] for k in keys-{'tests'}):raise ValueError('Incomplete or failed test acceptance')
 return value

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--manifest-sha256',required=True)
 p.add_argument('--builder-receipt',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 out=args.output.resolve();stage=args.stage.resolve()
 if out.exists() or out==ROOT or ROOT in out.parents or out==stage or stage in out.parents:raise ValueError('Output must be new and outside source/stage')
 out.mkdir(parents=True);report={'schema':1,'status':'running','cases':[],'phone_contacted':False,'production_updater_enabled':False,
   'limits':['headless software capture, not phone GPU/wlr','trusted Docker engine and cooperating private clients','not global portal interception or production activation']}
 def save():
  draft=out/'acceptance.tmp';draft.write_text(json.dumps(report,indent=2)+'\n');draft.replace(out/'acceptance.json')
 save();started=time.monotonic();container='omarchy-acceptance-'+secrets.token_hex(12)
 try:
  report['source_files']=verify_tree(ROOT,args.manifest,args.manifest_sha256);report['manifest_sha256']=args.manifest_sha256
  receipt=json.loads(args.builder_receipt.read_bytes());image=receipt['image_id']
  if not re.fullmatch('sha256:[0-9a-f]{64}',image):raise ValueError('Immutable image required')
  lock=ROOT/'packaging/portal-frontend-lab.lock.json'
  if receipt['lock_sha256']!=sha(lock.read_bytes()):raise ValueError('Builder lock differs')
  info=json.loads(subprocess.check_output(['docker','image','inspect',image],timeout=30))[0]
  if info['Id']!=image or info['Architecture']!='arm64':raise ValueError('Wrong image')
  binary=stage/'usr/local/lib/omarchy-dock/portal-wlr'
  if binary.is_symlink() or sha(binary.read_bytes())!=PIN:raise ValueError('Portal binary differs')
  report['runtime']={'image_id':image,'builder_receipt_sha256':sha(args.builder_receipt.read_bytes()),'frontend_lock_sha256':sha(lock.read_bytes()),'portal_sha256':PIN}
  save()
  commands=[[name,count,'linux'] for name,count in CASES]+[[*HOST,'host']]
  code='import subprocess\n'
  for i,(name,count) in enumerate(CASES):code+='subprocess.run(["python3","/src/scripts/dependency-lab/acceptance-case.py",'+repr('/src/'+name)+','+repr('/evidence/case-'+str(i)+'.json')+'],check=True)\n'
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMARCHY_SCOPE_IMAGE=image,OMARCHY_SCOPE_STAGE=str(stage))
  with (out/'linux.log').open('w') as log:
   subprocess.run(['docker','run','--rm','--name',container,'--network','none','--platform','linux/arm64','--cap-drop','ALL','--cap-add','CHOWN','--cap-add','FOWNER','--cap-add','DAC_OVERRIDE',
    '-v',str(ROOT)+':/src:ro','-v',str(stage)+':/stage:ro','-v',str(out)+':/evidence','-e','PYTHONDONTWRITEBYTECODE=1','-e','OMARCHY_FRONTEND_LAB=1',
    '-e','OMARCHY_PORTAL_LAB_BINARY=/stage/usr/local/lib/omarchy-dock/portal-wlr',image,'python3','-c',code],stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
  with (out/'host.log').open('w') as log:
   subprocess.run([sys.executable,str(ROOT/'scripts/dependency-lab/acceptance-case.py'),str(ROOT/HOST[0]),str(out/('case-'+str(len(CASES))+'.json'))],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
  for i,(name,count,platform) in enumerate(commands):
   result=validate_result(json.loads((out/('case-'+str(i)+'.json')).read_bytes()),count)
   report['cases'].append(dict(file=name,platform=platform,**result))
  verify_tree(ROOT,args.manifest,args.manifest_sha256)
  if sha(binary.read_bytes())!=PIN:raise ValueError('Portal changed during tests')
  report.update(status='passed',tests=sum(x['tests'] for x in report['cases']),linux_tests=sum(c for _,c in CASES),host_tests=HOST[1])
 except BaseException as error:
  report.update(status='failed',error_type=type(error).__name__,error=str(error));raise
 finally:
  # This name is generated by this invocation; never touch unrelated containers.
  try:subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
  except Exception as error:report.update(status='failed',cleanup_error=str(error))
  report['case_artifacts']={p.name:sha(p.read_bytes()) for p in out.glob('case-*.json')}
  report['elapsed_seconds']=round(time.monotonic()-started,3)
  report['logs']={p.name:sha(p.read_bytes()) for p in out.glob('*.log')}
  save()
 if report['status']!='passed':raise RuntimeError('Acceptance failed; inspect receipt')
 print(json.dumps({'status':report['status'],'tests':report['tests'],'receipt':str(out/'acceptance.json')}))
if __name__=='__main__':main()
