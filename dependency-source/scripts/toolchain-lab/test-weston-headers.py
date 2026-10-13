#!/usr/bin/env python3
import hashlib,importlib.util,io,tarfile,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('headers',Path(__file__).with_name('weston-headers.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Headers(unittest.TestCase):
 def package(self,root,extra=()):
  p=root/'package.tar'
  with tarfile.open(p,'w') as t:
   for name,kind in [('usr/include/libweston-15/a.h','file'),('usr/share/licenses/weston/COPYING','file'),*extra]:
    i=tarfile.TarInfo(name)
    if kind=='link':i.type=tarfile.SYMTYPE;i.linkname='/tmp/outside';t.addfile(i)
    else:i.size=3;t.addfile(i,io.BytesIO(b'abc'))
  return p,hashlib.sha256(p.read_bytes()).hexdigest()
 def test_repeatable_with_license(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p,h=self.package(r);a=m.derive(p,r/'a',h);b=m.derive(p,r/'b',h)
   self.assertEqual(a,b);self.assertEqual((r/'a/licenses/COPYING').read_bytes(),b'abc')
 def test_reject_corruption(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p,h=self.package(r)
   with self.assertRaises(ValueError):m.derive(p,r/'out','0'*64)
 def test_reject_unsafe_or_duplicate(self):
  for name,kind in [('usr/include/libweston-15/../../bad','file'),('usr/include/libweston-15/link','link'),('usr/include/libweston-15/a.h','file'),('usr/share/licenses/weston//escaped','file')]:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    r=Path(d);p,h=self.package(r,[(name,kind)])
    with self.assertRaises(ValueError):m.derive(p,r/'out',h)
if __name__=='__main__':unittest.main()
