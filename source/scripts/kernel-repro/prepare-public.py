#!/usr/bin/env python3
"""Reconstruct all added kernel sources from public archives and explicit patches."""
import argparse,hashlib,io,json,subprocess,tarfile,tempfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[2]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def safe(name):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or not name or '\\' in name:raise ValueError('Unsafe source path')
 return name
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archives',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Output must be new')
 lock=json.loads((ROOT/'packaging/kernel-sources.lock.json').read_text())
 for entry in lock['packages']:
  if digest(a.archives/entry['filename'])!=entry['digest']:raise ValueError('Archive changed: '+entry['name'])
 manifest=json.loads((ROOT/'build/kernel-repro/additions.json').read_text())
 with tarfile.open(a.archives/'upstream-port.tar.gz') as t:
  port={m.name.split('/',1)[1]:t.extractfile(m).read() for m in t if m.isfile()}
 with tarfile.open(a.archives/'upstream-linux.tar.gz') as t:
  found=[m for m in t if m.name.endswith('/drivers/gpu/drm/sysfb/simpledrm.c')];assert len(found)==1
  boot=t.extractfile(found[0]).read().replace(b'simpledrm',b'exynos_bootfb').replace(b'#define DRIVER_NAME\t"exynos_bootfb"',b'#define DRIVER_NAME\t"exynos"').replace(b'DRM driver for simple-framebuffer platform devices',b'DRM driver for the framebuffer an Exynos bootloader leaves running')
 with tempfile.TemporaryDirectory() as temp:
  work=Path(temp)
  for name,entry in manifest.items():
   safe(name);data=boot if entry['source'].startswith('generated-from-linux:') else port[entry['source']]
   if entry['normalize_crlf']:data=data.replace(b'\r\n',b'\n')
   if hashlib.sha256(data).hexdigest()!=entry['source_sha256']:raise ValueError('Source mismatch: '+name)
   dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
   if 'patch' in entry:
    patch=ROOT/safe(entry['patch'])
    if digest(patch)!=entry['patch_sha256']:raise ValueError('Patch changed: '+name)
    subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(patch)],cwd=work,check=True,stdout=subprocess.DEVNULL)
   if digest(dest)!=entry['result_sha256']:raise ValueError('Result mismatch: '+name)
  a.output.mkdir(parents=True)
  with tarfile.open(a.output/'additions.tar','w',format=tarfile.GNU_FORMAT) as t:
   for name,entry in sorted(manifest.items()):
    data=(work/name).read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=entry['mode'];info.mtime=1727740800;t.addfile(info,io.BytesIO(data))
 report={'sources':lock,'additions':manifest,'additions_tar_sha256':digest(a.output/'additions.tar')}
 (a.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'sources':len(manifest),'additions_sha256':report['additions_tar_sha256']}))
if __name__=='__main__':main()
