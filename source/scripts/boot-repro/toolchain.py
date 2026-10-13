"""Resolve a checked package-reconstructed ARM64 toolchain receipt."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def resolve(image_id,receipt=None):
 metadata=None
 if receipt:
  metadata=json.loads(Path(receipt).read_text())
  if metadata['toolchain']!='mesa':raise ValueError('Wrong toolchain')
  for key,name in [('lock_sha256','packaging/toolchains/mesa-archives.lock.json'),('dockerfile_sha256','build/toolchains/mesa.Dockerfile')]:
   if metadata['inputs'][key]!=hashlib.sha256((ROOT/name).read_bytes()).hexdigest():raise ValueError('Toolchain reconstruction input changed')
  image_id=metadata['image_id']
 info=json.loads(subprocess.check_output(['docker','image','inspect',image_id]))[0]
 if info['Id']!=image_id or info['Architecture']!='arm64':raise ValueError('Wrong toolchain image or architecture')
 return image_id,metadata
