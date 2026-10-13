import copy
import io
import tarfile
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


def load(name):
    s = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

stage = load('stage-dock-services')
check = load('check-dock-dependencies')

class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.file = self.root/'build/arch-arm/dock/helper.py'
        self.file.parent.mkdir(parents=True); self.file.write_text('value = 1\n')
        self.item = {'source': 'build/arch-arm/dock/helper.py', 'target': stage.PREFIX+'helper.py',
                     'sha256': hashlib.sha256(self.file.read_bytes()).hexdigest(), 'mode':'0644'}
        self.spec = {'schema':1,'name':'fixture','files':[self.item]}
        self.lock = {'schema':1,'packages':{'python':'3.14.7-1'}}
    def run_stage(self, name='out'):
        return stage.stage(self.root, self.root/name, self.spec, self.lock)
    def test_identical_and_private_exclusion(self):
        (self.file.parent/'allowed-inputs.json').write_text('private fixture')
        self.assertEqual(self.run_stage('one'), self.run_stage('two'))
        self.assertFalse(list((self.root/'one').rglob('allowed-inputs.json')))
    def test_source_drift(self):
        self.file.write_text('value = 2')
        with self.assertRaises(ValueError): self.run_stage()
        self.assertFalse((self.root/'out').exists())
    def test_duplicate(self):
        self.spec['files'].append(copy.copy(self.item))
        with self.assertRaises(ValueError): self.run_stage()
    def test_traversal(self):
        self.item['target'] = stage.PREFIX+'../private'
        with self.assertRaises(ValueError): self.run_stage()
    def test_symlink_parent(self):
        self.file.parent.rename(self.file.parent.with_name('real'))
        self.file.parent.symlink_to('real')
        with self.assertRaises(ValueError): self.run_stage()
    def test_private_target(self):
        self.item['target'] = stage.PREFIX+'allowed-inputs.json'
        with self.assertRaises(ValueError): self.run_stage()
    def test_shell_collision(self):
        self.item['target'] = stage.PREFIX+'omarchy-shell/file'
        with self.assertRaises(ValueError): self.run_stage()
    def test_existing_output(self):
        self.run_stage()
        with self.assertRaises(ValueError): self.run_stage()
    def test_pin_drift_and_missing(self):
        self.assertTrue(check.compare(self.lock,'python 3.14.7-1')['package_versions_match'])
        self.assertEqual(check.compare(self.lock,'python other')['changed'],['python'])
        self.assertEqual(check.compare(self.lock,'')['missing'],['python'])
        self.assertFalse(check.compare(self.lock,'python 3.14.7-1')['runtime_ready'])
    def test_external_pin_and_corruption(self):
        archive = self.root/'fixture.tar'
        with tarfile.open(archive, 'w') as t:
            item = tarfile.TarInfo('usr/lib/example.so'); item.size = 3
            t.addfile(item, io.BytesIO(b'abc'))
        lock = {'external_files': [{'path':'/usr/lib/example.so', 'sha256':hashlib.sha256(b'abc').hexdigest()}]}
        self.assertTrue(check.compare_external(lock, archive)['saved_external_inputs_match'])
        lock['external_files'][0]['sha256'] = 'wrong'
        self.assertFalse(check.compare_external(lock, archive)['saved_external_inputs_match'])
    def test_external_symlink_rejected(self):
        archive = self.root/'fixture.tar'
        with tarfile.open(archive, 'w') as t:
            item = tarfile.TarInfo('usr/lib/example.so'); item.type = tarfile.SYMTYPE; item.linkname = '/private'
            t.addfile(item)
        lock = {'external_files': [{'path':'/usr/lib/example.so', 'sha256':'unused'}]}
        self.assertFalse(check.compare_external(lock, archive)['saved_external_inputs_match'])
    def test_duplicate_inventory(self):
        with self.assertRaises(ValueError): check.compare(self.lock,'python a\npython b')

if __name__ == '__main__': unittest.main()
