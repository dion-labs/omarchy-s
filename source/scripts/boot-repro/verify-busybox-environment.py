#!/usr/bin/env python3
"""Verify the dated Ubuntu snapshot indexes and exact BusyBox build package set."""
import argparse,hashlib,json,lzma,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def fields(s):return dict(l.split(': ',1) for l in s.splitlines() if ': ' in l and not l.startswith(' '))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archives',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 r=a.archives.resolve();lock=json.loads((ROOT/'packaging/busybox-env-archives.lock.json').read_text());wanted=json.loads((ROOT/'packaging/busybox-ubuntu-build.json').read_text())['installed_build_dependencies'];found={}
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 image=json.loads((ROOT/'packaging/boot-inputs.lock.json').read_text())['image_id']
 for pocket in ['noble','noble-updates','noble-security']:
  cmd=['docker','run','--rm','--network','none','--cap-drop','ALL','-v',str(r)+':/e:ro',image,'gpgv','--homedir','/tmp','--status-fd','1','--keyring','/usr/share/keyrings/ubuntu-archive-keyring.gpg','/e/'+pocket+'-InRelease']
  v=subprocess.run(cmd,capture_output=True,text=True);(out/(pocket+'-gpg.txt')).write_text(v.stdout+v.stderr)
  if v.returncode or '[GNUPG:] VALIDSIG F6ECB3762474EDA9D21B7022871920D1991BC93C ' not in v.stdout:raise ValueError('Signature failure')
  s=(r/(pocket+'-InRelease')).read_text();h,n=re.search(r'^ ([a-f0-9]{64}) +(\d+) +main/binary-arm64/Packages.xz$',s,re.M).groups();data=(r/(pocket+'-main-Packages.xz')).read_bytes()
  if hashlib.sha256(data).hexdigest()!=h or len(data)!=int(n):raise ValueError('Index mismatch')
  for block in lzma.decompress(data).decode().split('\n\n'):
   d=fields(block)
   if d.get('Package') in wanted and wanted[d['Package']]==d.get('Version'):found[d['Package']]=d
 if len(lock['packages'])!=len(wanted) or {e['name']:e['version'] for e in lock['packages']}!=wanted:raise ValueError('Wrong package selection')
 for e in lock['packages']:
  d=found[e['name']]
  if d['SHA256']!=e['digest'] or Path(d['Filename']).name!=e['filename']:raise ValueError('Package index pin mismatch')
  data=(r/'packages'/e['filename']).read_bytes()
  if hashlib.sha256(data).hexdigest()!=d['SHA256'] or len(data)!=int(d['Size']):raise ValueError('Package bytes mismatch')
 report={'snapshot':lock['snapshot'],'signed_indexes':3,'verified_packages':len(wanted),'historical_snapshot_not_freshness_check':True,'device_contacted':False}
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
