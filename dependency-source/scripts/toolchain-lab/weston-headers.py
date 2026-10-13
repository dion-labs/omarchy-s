#!/usr/bin/env python3
"""Derive deterministic Weston15 headers from an exact distribution package."""
import argparse,gzip,hashlib,io,json,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[2]
def derive(package, output, expected):
    data=package.read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Package hash mismatch')
    if output.exists():raise ValueError('Output must be new')
    files={};licenses={}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            name=member.name.removeprefix('./')
            if not name.startswith(('usr/include/libweston-15/','usr/share/licenses/weston/')):continue
            if '..' in PurePosixPath(name).parts or member.issym() or member.islnk():raise ValueError('Unsafe header/license member')
            if not member.isfile():continue
            target=files if name.startswith('usr/include/') else licenses
            key=name.removeprefix('usr/include/') if target is files else name.removeprefix('usr/share/licenses/weston/')
            if not key or PurePosixPath(key).is_absolute() or PurePosixPath(key).as_posix()!=key:raise ValueError('Unsafe relative member')
            if key in target:raise ValueError('Duplicate member')
            target[key]=archive.extractfile(member).read()
    if not files or not licenses:raise ValueError('Headers or license missing')
    output.mkdir(parents=True)
    with (output/'headers.tgz').open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as compressed,tarfile.open(fileobj=compressed,mode='w',format=tarfile.GNU_FORMAT) as result:
        for name,data in sorted(files.items()):
            info=tarfile.TarInfo(name);info.mode=0o644;info.size=len(data);info.mtime=1727740800;result.addfile(info,io.BytesIO(data))
    for name,data in licenses.items():
        dest=output/'licenses'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    report={'package_sha256':expected,'headers':{n:hashlib.sha256(d).hexdigest() for n,d in sorted(files.items())},'header_archive_sha256':hashlib.sha256((output/'headers.tgz').read_bytes()).hexdigest()}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    lock=json.loads((ROOT/'packaging/weston-headers.lock.json').read_text());r=derive(a.package,a.output,lock['sha256']);print(json.dumps({'headers':len(r['headers']),'archive_sha256':r['header_archive_sha256']}))
