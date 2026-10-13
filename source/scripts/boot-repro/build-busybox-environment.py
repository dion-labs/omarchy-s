#!/usr/bin/env python3
"""Build an isolated Ubuntu BusyBox environment from exact recorded package versions."""
import argparse,hashlib,json,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 lock=json.loads((ROOT/'packaging/busybox-env-archives.lock.json').read_text());record=json.loads((ROOT/'packaging/busybox-ubuntu-build.json').read_text());wanted=record['installed_build_dependencies']
 if {e['name']:e['version'] for e in lock['packages']}!=wanted:raise ValueError('Package set differs from buildinfo')
 for e in lock['packages']:
  if sha(a.packages/e['filename'])!=e['digest']:raise ValueError('Package mismatch: '+e['name'])
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 with tempfile.TemporaryDirectory(prefix='busybox-env-') as temp:
  context=Path(temp);(context/'packages').mkdir()
  for e in lock['packages']:shutil.copyfile(a.packages/e['filename'],context/'packages'/e['filename'])
  recipe=ROOT/'build/boot-repro/BusyBox-Ubuntu.Dockerfile';shutil.copyfile(recipe,context/'Dockerfile')
  with (out/'build.log').open('w') as log:subprocess.run(['docker','build','--platform','linux/arm64','--network','none','--pull=false','--iidfile',str(out/'image-id'),str(context)],stdout=log,stderr=subprocess.STDOUT,check=True)
 image=(out/'image-id').read_text().strip()
 data=subprocess.check_output(['docker','run','--rm','--network','none',image,'dpkg-query','-W','-f=${db:Status-Abbrev}\t${binary:Package}\t${Version}\n']).decode();(out/'installed-packages.tsv').write_text(data)
 actual={k.split(':')[0]:v for status,k,v in (l.split('\t',2) for l in data.splitlines()) if status.startswith('ii')}
 mismatch={k:{'expected':v,'actual':actual.get(k)} for k,v in wanted.items() if actual.get(k)!=v}
 report={'image_id':image,'lock_sha256':sha(ROOT/'packaging/busybox-env-archives.lock.json'),'recipe_sha256':sha(recipe),'recorded_packages':len(wanted),'mismatches':mismatch,'extra_base_packages':{k:v for k,v in actual.items() if k not in wanted},'device_contacted':False}
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 if mismatch:raise ValueError('Recorded environment mismatch')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
