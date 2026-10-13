#!/usr/bin/env python3
import importlib.util,hashlib,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('trust',Path(__file__).with_name('verify-busybox-trust.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TrustChecks(unittest.TestCase):
 def test_digest_and_size(self):
  pair=(hashlib.sha256(b'good').hexdigest(),4);m.match(b'good',pair)
  with self.assertRaises(ValueError):m.match(b'evil',pair)
  with self.assertRaises(ValueError):m.match(b'good',(pair[0],5))
 def test_exact_identity(self):
  t='Package: busybox\nVersion: 1\nArchitecture: arm64'
  self.assertEqual(m.one(t,'busybox','1')['Architecture'],'arm64')
  for text in [t+'\n\n'+t,'Package: busybox\nVersion: 2']:
   with self.assertRaises(ValueError):m.one(text,'busybox','1')
 def test_continuations(self):
  text='Checksums-Sha256:\n '+('a'*64)+' 4 foo\n '+('b'*64)+' 5 bar\nNext: end'
  self.assertEqual(m.checks(text,'Checksums-Sha256')['bar'],('b'*64,5))
if __name__=='__main__':unittest.main()
