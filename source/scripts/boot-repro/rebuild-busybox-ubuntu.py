#!/usr/bin/env python3
"""Rebuild Ubuntu BusyBox with recorded package versions in a disposable offline container."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--environment',type=Path,required=True);p.add_argument('--sources',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 receipt=json.loads(a.environment.read_text())
 if receipt['mismatches'] or receipt['lock_sha256']!=sha(ROOT/'packaging/busybox-env-archives.lock.json') or receipt['recipe_sha256']!=sha(ROOT/'build/boot-repro/BusyBox-Ubuntu.Dockerfile'):raise ValueError('Environment receipt does not match pins')
 info=json.loads(subprocess.check_output(['docker','image','inspect',receipt['image_id']]))[0]
 if info['Id']!=receipt['image_id'] or info['Architecture']!='arm64':raise ValueError('Wrong environment image')
 lock=json.loads((ROOT/'packaging/busybox-source.lock.json').read_text())
 for e in lock['packages']:
  if sha(a.sources/e['filename'])!=e['digest']:raise ValueError('Source changed')
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 recipe=ROOT/'build/boot-repro/rebuild-busybox-ubuntu.sh'
 command=['docker','run','--rm','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','4','--memory','3g']
 for e in lock['packages']:command+=['-v',str((a.sources/e['filename']).resolve())+':/sources/'+e['filename']+':ro']
 command+=['-v',str(recipe)+':/recipe:ro','-v',str(out)+':/output',receipt['image_id'],'bash','/recipe']
 (out/'inputs.json').write_text(json.dumps({'environment':receipt,'recipe_sha256':sha(recipe),'source_lock_sha256':sha(ROOT/'packaging/busybox-source.lock.json'),'command':command},indent=2)+'\n')
 with (out/'runner.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
 binary=sha(out/'busybox');package=sha(out/'busybox-static_1.36.1-6ubuntu3.1_arm64.deb')
 report={'binary_sha256':binary,'binary_matches':binary=='52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933','package_sha256':package,'package_matches':package=='d96535e0402c011e0ee43449799df2f4504d44b842e4f2b3a6cbc845508eaafc','device_contacted':False}
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 if not report['binary_matches']:raise ValueError('BusyBox binary differs; preserve evidence')
if __name__=='__main__':main()
