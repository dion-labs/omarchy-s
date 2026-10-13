import importlib.util
import tempfile
from pathlib import Path
import unittest

s=importlib.util.spec_from_file_location('rebuild',Path(__file__).with_name('rebuild-private.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class Inputs(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'input').write_text('source')
    def test_path(self):
        self.assertEqual(m.validate_path(self.root,'input'),self.root/'input')
        for name in ('../input','/input','a/../input','./input','a\\input'):
            with self.assertRaises(ValueError):m.validate_path(self.root,name)
    def test_symlink(self):
        (self.root/'link').symlink_to('input')
        with self.assertRaises(ValueError):m.validate_path(self.root,'link')
    def test_changes(self):
        a=m.inventory(self.root);(self.root/'input').write_text('other')
        self.assertNotEqual(a,m.inventory(self.root))
    def test_mode_and_link(self):
        a=m.inventory(self.root);(self.root/'input').chmod(0o755)
        self.assertNotEqual(a,m.inventory(self.root))
        (self.root/'link').symlink_to('input')
        self.assertEqual(m.inventory(self.root)['link'],{'link':'input'})
if __name__=='__main__': unittest.main()
