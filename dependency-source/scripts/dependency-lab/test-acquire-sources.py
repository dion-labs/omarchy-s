import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('acquire', Path(__file__).with_name('acquire-sources.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Acquisition(unittest.TestCase):
    def test_cache_and_existing_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, cache = Path(tmp)/'root', Path(tmp)/'cache'
            (root/'packaging').mkdir(parents=True)
            cache.mkdir()
            (cache/'input').write_bytes(b'pinned')
            item = {'path': 'input', 'sha256': hashlib.sha256(b'pinned').hexdigest(), 'url': 'https://invalid.invalid/never-contact'}
            (root/'packaging/dependency-sources.lock.json').write_text(json.dumps({'archives': [item], 'git_archives': []}))
            self.assertEqual(m.acquire(root, cache), 1)
            self.assertEqual((root/'input').read_bytes(), b'pinned')
            self.assertEqual(m.acquire(root, cache), 1)
            (root/'input').write_bytes(b'drift')
            with self.assertRaises(ValueError): m.acquire(root, cache)
            self.assertEqual((root/'input').read_bytes(), b'drift')
    def test_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('../input', '/input', 'a/../input', 'a\\input', './input'):
                with self.assertRaises(ValueError): m.checked_path(root, name)
            (root/'link').symlink_to('/tmp')
            with self.assertRaises(ValueError): m.checked_path(root, 'link/input')

if __name__ == '__main__': unittest.main()
