#!/usr/bin/env python3
import hashlib,importlib.util,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('builder',Path(__file__).with_name('build-frontend-lab.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Inputs(unittest.TestCase):
    def fixture(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);p=root/'package.pkg.tar.xz';p.write_bytes(b'fixture')
        return root,{'packages':[{'filename':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
    def test_exact_and_tampered(self):
        root,lock=self.fixture();self.assertEqual(m.verify(lock,root),[root/'package.pkg.tar.xz'])
        (root/'package.pkg.tar.xz').write_bytes(b'changed')
        with self.assertRaises(ValueError):m.verify(lock,root)
    def test_unsafe_and_duplicate(self):
        root,lock=self.fixture();lock['packages']*=2
        with self.assertRaises(ValueError):m.verify(lock,root)
        lock['packages']=[{'filename':'../outside','sha256':'0'*64}]
        with self.assertRaises(ValueError):m.verify(lock,root)
    def test_missing_and_link(self):
        root,lock=self.fixture();p=root/'package.pkg.tar.xz';p.unlink()
        with self.assertRaises(ValueError):m.verify(lock,root)
        (root/'original').write_bytes(b'fixture');p.symlink_to(root/'original')
        with self.assertRaises(ValueError):m.verify(lock,root)
    def test_empty(self):
        with self.assertRaises(ValueError):m.verify({'packages':[]},Path('/tmp'))
if __name__=='__main__':unittest.main()
