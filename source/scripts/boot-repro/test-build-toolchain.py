#!/usr/bin/env python3
import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('builder',Path(__file__).with_name('build-toolchain.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class BuilderTests(unittest.TestCase):
 def fixture(self,r):
  (r/'packaging/toolchains').mkdir(parents=True);(r/'build/toolchains').mkdir(parents=True);(r/'cache').mkdir()
  (r/'cache/p.deb').write_bytes(b'fixture');row={'filename':'p.deb','algorithm':'sha256','digest':hashlib.sha256(b'fixture').hexdigest()}
  (r/'packaging/toolchains/mesa-archives.lock.json').write_text(json.dumps({'packages':[row]}));(r/'build/toolchains/mesa.Dockerfile').write_text('FROM example@sha256:fixture\n');return row
 def test_prepare_and_preserve_existing(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);self.fixture(r);v=m.prepare(r,r/'cache',r/'out');self.assertEqual(v['package_count'],1)
   self.assertEqual((r/'out/packages/p.deb').read_bytes(),b'fixture')
   with self.assertRaisesRegex(ValueError,'Output must be new'):m.prepare(r,r/'cache',r/'out')
 def test_corruption_before_output(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);self.fixture(r);(r/'cache/p.deb').write_bytes(b'bad')
   with self.assertRaisesRegex(ValueError,'hash mismatch'):m.prepare(r,r/'cache',r/'out')
   self.assertFalse((r/'out').exists())
 def test_duplicate_and_traversal(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);row=self.fixture(r)
   for rows in [[row,row],[dict(row,filename='../p.deb')]]:
    (r/'packaging/toolchains/mesa-archives.lock.json').write_text(json.dumps({'packages':rows}))
    with self.assertRaisesRegex(ValueError,'filename'):m.prepare(r,r/'cache',r/'out')
 def test_receipt_matches_consumer_contract(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);self.fixture(r);out=r/'out';inputs=m.prepare(r,r/'cache',out)
   def run(cmd,**kwargs):
    self.assertIn('--network',cmd);self.assertIn('--pull=false',cmd);(out/'image-id.txt').write_text('sha256:fixture')
   with patch.object(m.subprocess,'run',side_effect=run),patch.object(m.subprocess,'check_output',return_value=b'[{"Architecture":"arm64","Id":"sha256:fixture"}]'):
    receipt=m.build(out,inputs)
   self.assertEqual(receipt['toolchain'],'mesa');self.assertEqual(receipt['inputs'],inputs)
if __name__=='__main__':unittest.main()
