#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
s=importlib.util.spec_from_file_location('runner',Path(__file__).with_name('run-acceptance.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Acceptance(unittest.TestCase):
 def fixture(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);base=Path(temp.name);root=base/'source';root.mkdir();(root/'a').write_bytes(b'original');(root/'a').chmod(0o644)
  manifest=base/'manifest.json';manifest.write_text(json.dumps({'files':[{'path':'a','sha256':m.sha(b'original'),'mode':'0644'}]}))
  return root,manifest,m.sha(manifest.read_bytes())
 def test_exact_manifest_and_wrong_manifest_hash(self):
  root,manifest,digest=self.fixture();self.assertEqual(m.verify_tree(root,manifest,digest),1)
  with self.assertRaises(ValueError):m.verify_tree(root,manifest,'0'*64)
 def test_source_tamper(self):
  root,manifest,digest=self.fixture();(root/'a').write_bytes(b'changed')
  with self.assertRaises(ValueError):m.verify_tree(root,manifest,digest)
 def test_missing_and_extra_source(self):
  for missing in (True,False):
   root,manifest,digest=self.fixture()
   if missing:(root/'a').unlink()
   else:(root/'extra').write_text('extra')
   with self.assertRaises(ValueError):m.verify_tree(root,manifest,digest)
 def test_unsafe_duplicate_manifest(self):
  for names in (['../outside'],['a','a'],['/absolute']):
   root,manifest,digest=self.fixture();manifest.write_text(json.dumps({'files':[{'path':n,'sha256':m.sha(b'original')} for n in names]}))
   with self.assertRaises(ValueError):m.verify_tree(root,manifest,m.sha(manifest.read_bytes()))
 def test_symlink_and_mode_refused(self):
  root,manifest,digest=self.fixture();(root/'a').chmod(0o600)
  with self.assertRaises(ValueError):m.verify_tree(root,manifest,digest)
  (root/'a').unlink();(root/'a').symlink_to(manifest)
  with self.assertRaises(ValueError):m.verify_tree(root,manifest,digest)
 def test_missing_skipped_failed_or_wrong_count_refused(self):
  good=dict(tests=2,failures=0,errors=0,skips=0,expected_failures=0,unexpected_successes=0)
  self.assertEqual(m.validate_result(good,2),good)
  for key in good:
   bad=dict(good);bad[key]=1
   with self.assertRaises(ValueError):m.validate_result(bad,2)
  for bad in ({},None,dict(good,tests=True)):
   with self.assertRaises(ValueError):m.validate_result(bad,2)
if __name__=='__main__':unittest.main()
