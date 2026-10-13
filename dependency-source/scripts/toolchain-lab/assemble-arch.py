#!/usr/bin/env python3
"""Assemble a package-only root tar without extracting archives onto the host."""
import hashlib,io,json,sys,tarfile
from pathlib import Path,PurePosixPath
lock=json.loads(Path(sys.argv[1]).read_text());cache=Path(sys.argv[2]);out=Path(sys.argv[3])
if out.exists():raise SystemExit('Output must be new')
files={}
for package in lock['packages']:
 p=cache/package['filename'];data=p.read_bytes()
 assert hashlib.new(package['algorithm'],data).hexdigest()==package['digest'],p.name
 with tarfile.open(fileobj=io.BytesIO(data)) as source:
  info=source.extractfile('.PKGINFO').read().decode()
  fields=dict(line.split(' = ',1) for line in info.splitlines() if ' = ' in line)
  if fields.get('pkgname')!=package['name'] or fields.get('pkgver')!=package['version']:
   raise ValueError('Package identity mismatch: '+package['name'])
  for member in source:
   name=member.name.removeprefix('./').rstrip('/')
   if not name or name.startswith('.') or name in ('dev','proc','sys'):continue
   assert not name.startswith('/') and '..' not in PurePosixPath(name).parts,name
   if not (member.isdir() or member.isfile() or member.issym() or member.islnk()):continue
   member.name=name;member.uid=member.gid=0;member.uname=member.gname='root';member.mtime=1727740800;member.pax_headers={}
   content=source.extractfile(member).read() if member.isfile() else None
   files[name]=(member,content)
# No package post-install scripts are executed. Provide a deterministic root user.
for name,content in [('etc/passwd',b'root:x:0:0:root:/root:/bin/bash\n'),('etc/group',b'root:x:0:\n')]:
 member=tarfile.TarInfo(name);member.size=len(content);member.mode=0o644;member.mtime=1727740800;files[name]=(member,content)
with tarfile.open(out,'w',format=tarfile.GNU_FORMAT) as target:
 for name,(member,data) in sorted(files.items()):target.addfile(member,io.BytesIO(data) if data is not None else None)
print(json.dumps({'files':len(files),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
