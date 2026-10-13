#!/usr/bin/env python3
import hashlib,tempfile,unittest
from pathlib import Path
from pipeline import checked,sha
class InputGuards(unittest.TestCase):
 def test_changed_derived_input(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'input';p.write_bytes(b'original');h=sha(p);checked(p,h);p.write_bytes(b'changed')
   with self.assertRaises(ValueError):checked(p,h)
 def test_missing_input(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):checked(Path(d)/'absent',hashlib.sha256(b'').hexdigest())
if __name__=='__main__':unittest.main()
