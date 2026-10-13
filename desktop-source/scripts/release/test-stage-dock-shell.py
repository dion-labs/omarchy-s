#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('stage', Path(__file__).with_name('stage-dock-shell.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class StagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.payload = self.root / 'payload'
        self.payload.mkdir()
        self.file = self.payload / 'launcher'
        self.file.write_text('fixture\n')
        self.file.chmod(0o755)
        self.manifest = {'upstream': 'pin', 'files': {'launcher': hashlib.sha256(self.file.read_bytes()).hexdigest()}}
        self.spec = {'prefix': '/usr/local/lib/omarchy-dock/omarchy-shell', 'upstream_commit': 'pin'}
        self.save()
    def save(self):
        (self.payload / 'source-manifest.json').write_text(json.dumps(self.manifest))
    def stage(self, name='out'):
        return module.stage_payload(self.payload, self.root / name, self.spec)
    def test_deterministic_and_private_sibling_excluded(self):
        (self.root / 'private.json').write_text('not a package input')
        self.assertEqual(self.stage('one'), self.stage('two'))
        a, b = self.root/'one', self.root/'two'
        for p in a.rglob('*'):
            if p.is_file():
                other = b/p.relative_to(a)
                self.assertEqual(p.read_bytes(), other.read_bytes())
                self.assertEqual(p.stat().st_mode, other.stat().st_mode)
        self.assertFalse(any(p.name == 'private.json' for p in a.rglob('*')))
    def test_modified_payload(self):
        self.file.write_text('changed')
        with self.assertRaises(ValueError): self.stage()
        self.assertFalse((self.root/'out').exists())
    def test_unlisted_file(self):
        (self.payload/'extra').write_text('extra')
        with self.assertRaises(ValueError): self.stage()
    def test_symlink(self):
        (self.payload/'link').symlink_to(self.file)
        with self.assertRaises(ValueError): self.stage()
    def test_traversal(self):
        self.manifest['files']['../outside'] = 'hash'; self.save()
        with self.assertRaises(ValueError): self.stage()
    def test_pin(self):
        self.manifest['upstream'] = 'wrong'; self.save()
        with self.assertRaises(ValueError): self.stage()
    def test_existing_target_preserved(self):
        self.stage()
        before = (self.root/'out/ownership.json').read_bytes()
        with self.assertRaises(ValueError): self.stage()
        self.assertEqual(before, (self.root/'out/ownership.json').read_bytes())
    def test_special_permissions(self):
        self.file.chmod(0o4755)
        with self.assertRaises(ValueError): self.stage()

if __name__ == '__main__': unittest.main()
