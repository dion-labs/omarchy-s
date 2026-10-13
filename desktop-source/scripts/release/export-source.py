#!/usr/bin/env python3
"""Stage a hash-locked source-only preview; never publish or traverse private trees."""
import argparse,hashlib,io,json,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[2]
DENIED={'artifacts','backups','local-evidence','.git','__pycache__'}
def validate(root,rows):
 seen=set();checked=[]
 for row in rows:
  name=row['path'];p=PurePosixPath(name)
  if not name or p.is_absolute() or '..' in p.parts or '\\' in name or set(p.parts)&DENIED or name in seen:raise ValueError('Unsafe or duplicate allowlist path')
  seen.add(name);source=root.joinpath(*p.parts)
  if any(root.joinpath(*p.parts[:i]).is_symlink() for i in range(1,len(p.parts)+1)):raise ValueError('Symlink input')
  if not source.is_file():raise ValueError('Missing source: '+name)
  data=source.read_bytes();data.decode('utf-8')
  if b'\0' in data:raise ValueError('Binary source input')
  if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Changed source: '+name)
  if row['mode']!='0644':raise ValueError('Unsupported mode')
  checked.append((name,data))
 return checked
def export(root,allowlist,output):
 if output.exists():raise ValueError('Output must be new')
 plan=json.loads(allowlist.read_text());files=validate(root,plan['files'])
 output.mkdir(parents=True)
 with tarfile.open(output/'source-preview.tar','w',format=tarfile.GNU_FORMAT) as t:
  for name,data in sorted(files):
   target=output/'tree'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(0o644)
   info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0;t.addfile(info,io.BytesIO(data))
 manifest={'scope':plan['scope'],'publication_cleared':False,'allowlist_sha256':hashlib.sha256(allowlist.read_bytes()).hexdigest(),'files':plan['files'],'archive_sha256':hashlib.sha256((output/'source-preview.tar').read_bytes()).hexdigest()}
 (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--allowlist',type=Path,default=ROOT/'packaging/source-export.allowlist.json');p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=export(ROOT,a.allowlist,a.output.resolve());print(json.dumps({'files':len(r['files']),'sha256':r['archive_sha256'],'publication_cleared':False}))
