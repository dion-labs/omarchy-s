#!/usr/bin/env python3
import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('export',Path(__file__).with_name('export-source.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ExportTests(unittest.TestCase):
 def test_guards_and_repeatability(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'a.py').write_text('print(1)\n');row={'path':'a.py','mode':'0644','sha256':hashlib.sha256((r/'a.py').read_bytes()).hexdigest()};p=r/'plan.json';p.write_text(json.dumps({'scope':'test','files':[row]}))
   a=m.export(r,p,r/'one');b=m.export(r,p,r/'two');self.assertEqual(a['archive_sha256'],b['archive_sha256'])
   with self.assertRaises(ValueError):m.export(r,p,r/'one')
   (r/'a.py').write_text('changed')
   with self.assertRaises(ValueError):m.export(r,p,r/'three')
   self.assertFalse((r/'three').exists())
 def test_forbidden_paths(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d)
   for name in ['../a','/a','backups/a','artifacts/a','local-evidence/a','a\\b']:
    with self.assertRaises(ValueError):m.validate(r,[{'path':name}])
 def test_symlinks(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'real').mkdir();(r/'link').symlink_to(r/'real',target_is_directory=True)
   with self.assertRaises(ValueError):m.validate(r,[{'path':'link/a'}])
if __name__=='__main__':unittest.main()
