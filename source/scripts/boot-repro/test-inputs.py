#!/usr/bin/env python3
import importlib.util,json,stat,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('boot',Path(__file__).with_name('prepare.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Inputs(unittest.TestCase):
 def test_wrong_file_size_rejected(self):
  record={'name':'x','fields':[1,stat.S_IFREG|0o644,0,0,1,0,8,3,1,0,0,2,0]}
  with self.assertRaisesRegex(ValueError,'size mismatch'):m.make_cpio({'records':[record],'trailing_padding':0},{'x':b'bad'})
 def test_special_nodes_are_encoded_not_created(self):
  record={'name':'dev/console','fields':[1,stat.S_IFCHR|0o600,0,0,1,0,0,3,1,5,1,12,0]}
  data=m.make_cpio({'records':[record],'trailing_padding':0},{})
  self.assertTrue(data.startswith(b'070701'));self.assertIn(b'dev/console\0',data)
 def test_bad_package_rejected_before_docker(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);p=root/'bad.deb';p.write_bytes(b'bad')
   with patch.object(m.subprocess,'check_output') as run,self.assertRaisesRegex(ValueError,'Archive changed'):m.prepare(p,root/'missing',root/'out')
   run.assert_not_called();self.assertFalse((root/'out').exists())
 def test_existing_output_preserved(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'sentinel').write_text('keep')
   with self.assertRaisesRegex(ValueError,'Output must be new'):m.prepare(root/'none',root/'none',root)
   self.assertEqual((root/'sentinel').read_text(),'keep')
if __name__=='__main__':unittest.main()
