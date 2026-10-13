import importlib.util,json,tempfile,hashlib,unittest,io,tarfile,subprocess,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('prepare',Path(__file__).with_name('prepare-context.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Checks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);(self.root/'p.deb').write_bytes(b'package');self.item={'filename':'p.deb','algorithm':'sha256','digest':hashlib.sha256(b'package').hexdigest()};self.lock={'packages':[self.item]}
 def test_embedded_identity(self):
  archive=self.root/'fake.pkg.tar.xz'
  with tarfile.open(archive,'w:xz') as t:
   data=b'pkgname = different\npkgver = 1-1\n';info=tarfile.TarInfo('.PKGINFO');info.size=len(data);t.addfile(info,io.BytesIO(data))
  lock={'packages':[{'filename':archive.name,'algorithm':'sha256','digest':hashlib.sha256(archive.read_bytes()).hexdigest(),'name':'expected','version':'1-1'}]}
  p=self.root/'lock.json';p.write_text(json.dumps(lock));output=self.root/'root.tar'
  r=subprocess.run([sys.executable,str(Path(__file__).with_name('assemble-arch.py')),str(p),str(self.root),str(output)],capture_output=True)
  self.assertNotEqual(r.returncode,0);self.assertIn(b'identity mismatch',r.stderr);self.assertFalse(output.exists())
 def test_good(self):self.assertEqual(m.verify_packages(self.lock,self.root),[self.root/'p.deb'])
 def test_tampered(self):
  (self.root/'p.deb').write_bytes(b'other')
  with self.assertRaises(ValueError):m.verify_packages(self.lock,self.root)
 def test_paths(self):
  for name in ('../p','/tmp/p','a/b','..','a\\b'):
   with self.assertRaises(ValueError):m.validate_name(name)
 def test_duplicate(self):
  self.lock['supplemental']=[self.item]
  with self.assertRaises(ValueError):m.verify_packages(self.lock,self.root)
 def test_symlink(self):
  (self.root/'p.deb').unlink();(self.root/'p.deb').symlink_to('/tmp/missing')
  with self.assertRaises(ValueError):m.verify_packages(self.lock,self.root)
if __name__=='__main__':unittest.main()
