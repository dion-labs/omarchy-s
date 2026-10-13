#!/usr/bin/env python3
"""Reconstruct a local ARM64 builder and record an immutable image identity."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('toolchain',choices=['arch','mesa']);p.add_argument('--packages',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
subprocess.run([sys.executable,str(ROOT/'scripts/toolchain-lab/prepare-context.py'),a.toolchain,'--packages',str(a.packages),'--output',str(a.output)],check=True)
context=a.output.resolve()
subprocess.run(['docker','build','--platform','linux/arm64','--network','none','--iidfile',str(context/'image-id.txt'),str(context)],check=True)
image=(context/'image-id.txt').read_text().strip()
info=json.loads(subprocess.check_output(['docker','image','inspect',image]))[0]
assert info['Architecture']=='arm64'
receipt={'toolchain':a.toolchain,'image_id':info['Id'],'inputs':json.loads((context/'inputs.json').read_text()),'scope':'package-reconstructed builder, no device access'}
(context/'toolchain.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
