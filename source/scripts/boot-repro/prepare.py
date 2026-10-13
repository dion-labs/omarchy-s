#!/usr/bin/env python3
"""Reconstruct native20 initramfs and firmware inputs without device access."""
import argparse,hashlib,io,json,stat,subprocess,tarfile
from pathlib import Path,PurePosixPath
from toolchain import resolve
ROOT=Path(__file__).resolve().parents[2]
def sha(data,algorithm='sha256'):return hashlib.new(algorithm,data).hexdigest()
def make_cpio(layout,files):
 output=bytearray()
 for e in layout['records']:
  name=e['name'];fields=e['fields'];mode=fields[1]
  if name=='TRAILER!!!' or not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):data=b''
  elif stat.S_ISLNK(mode):data=e['symlink'].encode()+b'\0'
  else:data=files[name]
  if len(data)!=fields[6] or len(name.encode())+1!=fields[11]:raise ValueError('CPIO size mismatch: '+name)
  output+=b'070701'+''.join(f'{v:08X}' for v in fields).encode()+name.encode()+b'\0'
  output+=b'\0'*(-len(output)%4);output+=data;output+=b'\0'*(-len(output)%4)
 output+=b'\0'*layout['trailing_padding'];return bytes(output)
def prepare(package,port,output,receipt=None):
 lock=json.loads((ROOT/'packaging/boot-inputs.lock.json').read_text())
 if output.exists():raise ValueError('Output must be new')
 for n,h in lock['files'].items():
  if sha((ROOT/n).read_bytes())!=h:raise ValueError('Source changed: '+n)
 for p,spec in ((package,lock['busybox_package']),(port,lock['port_archive'])):
  if sha(p.read_bytes(),spec['algorithm'])!=spec['digest']:raise ValueError('Archive changed: '+str(p))
 image_id,toolchain=resolve(lock['image_id'],receipt)
 data=subprocess.check_output(['docker','run','--rm','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','-v',str(package.resolve())+':/package.deb:ro',image_id,'dpkg-deb','--fsys-tarfile','/package.deb'])
 with tarfile.open(fileobj=io.BytesIO(data)) as t:
  package_files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
 with tarfile.open(port) as t:
  port_files={m.name.split('/',1)[1]:t.extractfile(m).read() for m in t if m.isfile()}
 files={'bin/busybox':package_files['usr/bin/busybox'],'extra-probe':port_files['device/mainline-extra-probe'].replace(b'\r\n',b'\n')}
 source=(ROOT/'build/mainline/diagnostic/init').read_text();anchor='mount -t devtmpfs devtmpfs /dev\n'
 if source.count(anchor)!=1:raise ValueError('Init anchor changed')
 files['init']=source.replace(anchor,anchor+'''. /native-root-layout.sh
. /native-transition.sh
if ! try_native_boot; then
    echo 'Native transition cleanup failed; leaving a rescue shell without starting graphics.'
    exec setsid sh -i </dev/console >/dev/console 2>&1
fi
''').encode()
 for name,path in [('native-root-layout.sh','build/arch-arm/native-boot/root-layout.sh'),('native-transition.sh','build/arch-arm/native-boot/transition.sh'),('root-layout.sh','build/mainline/diagnostic/root-layout.sh'),('usb-console.sh','build/mainline/diagnostic/usb-console.sh')]:files[name]=(ROOT/path).read_bytes()
 if {n:sha(b) for n,b in files.items()}!=lock['initramfs_file_hashes']:raise ValueError('Initramfs source mismatch')
 cpio=make_cpio(json.loads((ROOT/'build/boot-repro/cpio-layout.json').read_text()),files)
 if sha(cpio)!=lock['cpio_sha256']:raise ValueError('CPIO differs from native20')
 firmware={}
 for name,spec in lock['firmware'].items():
  if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:raise ValueError('Unsafe firmware path')
  data=port_files[spec['source']]
  if name.endswith('.txt'):data=data.replace(b'\r\n',b'\n')
  if sha(data)!=spec['sha256']:raise ValueError('Firmware mismatch: '+name)
  firmware[name]=data
 output.mkdir(parents=True);(output/'initramfs.cpio').write_bytes(cpio)
 for name,data in firmware.items():
  p=output/'firmware'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 licenses=output/'provenance';licenses.mkdir()
 (licenses/'busybox-copyright').write_bytes(package_files['usr/share/doc/busybox-static/copyright'])
 (licenses/'upstream-firmware-README.md').write_bytes(port_files['firmware/README.md'])
 report={'toolchain_image':image_id,'toolchain_receipt':toolchain,'cpio_sha256':sha(cpio),'files':{n:sha(b) for n,b in files.items()},'firmware':{n:sha(b) for n,b in firmware.items()},'scope':lock['scope']}
 (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--busybox-package',type=Path,required=True);p.add_argument('--port-archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--toolchain-receipt',type=Path);a=p.parse_args();print(json.dumps(prepare(a.busybox_package,a.port_archive,a.output,a.toolchain_receipt)))
