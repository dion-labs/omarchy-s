#!/usr/bin/env python3
"""Verify the prepared regulatory database against certificates in pinned Linux."""
import argparse,hashlib,json,re,subprocess,tarfile,tempfile
from pathlib import Path
from toolchain import resolve
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kernel-archive',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--toolchain-receipt',type=Path);a=p.parse_args()
 if a.output.exists():raise ValueError('Output must be new')
 kernel=next(x for x in json.loads((ROOT/'packaging/kernel-sources.lock.json').read_text())['packages'] if x['name']=='linux')
 if hashlib.sha256(a.kernel_archive.read_bytes()).hexdigest()!=kernel['digest']:raise ValueError('Kernel archive changed')
 lock=json.loads((ROOT/'packaging/boot-inputs.lock.json').read_text());certs={};image_id,toolchain=resolve(lock['image_id'],a.toolchain_receipt)
 with tarfile.open(a.kernel_archive) as t:
  for m in t:
   for name in ('wens','sforshee'):
    if m.name.endswith('/net/wireless/certs/'+name+'.hex'):
     certs[name]=bytes(int(x,16) for x in re.findall(rb'0x([0-9a-fA-F]{2})',t.extractfile(m).read()))
 if set(certs)!={'wens','sforshee'}:raise ValueError('Missing kernel certificates')
 with tempfile.TemporaryDirectory() as temp:
  work=Path(temp)
  for name,data in certs.items():(work/(name+'.der')).write_bytes(data)
  for name in ('regulatory.db','regulatory.db.p7s'):
   data=(a.prepared/'firmware'/name).read_bytes()
   if hashlib.sha256(data).hexdigest()!=lock['firmware'][name]['sha256']:raise ValueError('Regdb input changed')
   (work/name).write_bytes(data)
  script='set -eu; for n in wens sforshee; do openssl x509 -inform DER -in /work/$n.der -out /work/$n.pem; done; cat /work/wens.pem /work/sforshee.pem > /work/trust.pem; openssl cms -verify -binary -inform DER -in /work/regulatory.db.p7s -content /work/regulatory.db -CAfile /work/trust.pem -no-CApath -no-CAstore -purpose any -out /dev/null'
  result=subprocess.run(['docker','run','--rm','--network','none','--cap-drop','ALL','-v',str(work)+':/work',image_id,'sh','-ec',script],capture_output=True,text=True,check=True)
 report={'toolchain_image':image_id,'toolchain_receipt':toolchain,'verified':True,'trust_source_commit':'8cd9520d35a6c38db6567e97dd93b1f11f185dc6','certificate_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in certs.items()},'openssl_result':result.stderr.strip(),'scope':'Detached signature and chain against pinned kernel regulatory certificates; not a redistribution/license decision or runtime test.'}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
