import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('portal', Path(__file__).with_name('stage-portal.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Staging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve();self.root = self.base/'source'
        for name in ('packaging/dock-dependencies.lock.json', 'packaging/dependency-sources.lock.json',
                     'packaging/header-provenance-builds.lock.json', 'build/portal-wlr/patch.py',
                     'open-source/licenses/dependencies/portal-LICENSE'):
            dest = self.root/name;dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(m.ROOT/name, dest)
        self.binary = self.base/'portal';self.binary.write_bytes(b'fixture executable')
        manifest = {'upstream_commit': '34153094662acd713241ca6cbbb20003ef67da5f',
                    'version': '0.8.4-omarchy-lifecycle1',
                    'binary_sha256': hashlib.sha256(self.binary.read_bytes()).hexdigest(),
                    'patch_sha256': '0c33fc36ab1ba2b108b31d94201206de33c821c709c1543308fcb367fc6b4dac'}
        self.expected_manifest = (json.dumps(manifest, indent=2)+'\n').encode()
        p = self.root/'packaging/dock-dependencies.lock.json';lock = json.loads(p.read_text())
        for row in lock['external_files']:
            if row['path'].endswith('/portal-wlr'):row['sha256'] = manifest['binary_sha256']
            if row['path'].endswith('/portal-manifest.json'):row['sha256'] = hashlib.sha256(self.expected_manifest).hexdigest()
        p.write_text(json.dumps(lock))
    def test_repeatability_and_metadata(self):
        a, b = self.base/'a', self.base/'b'
        self.assertEqual(m.stage(self.root, self.binary, a), m.stage(self.root, self.binary, b))
        for p in a.rglob('*'):
            if p.is_file():
                self.assertEqual(p.read_bytes(), (b/p.relative_to(a)).read_bytes())
                self.assertEqual(p.stat().st_mtime, 0)
        self.assertEqual((a/'rootfs'/m.PREFIX/'portal-manifest.json').read_bytes(), self.expected_manifest)
        self.assertEqual((a/'rootfs'/m.PREFIX/'portal-wlr').stat().st_mode & 0o777, 0o755)
    def test_binary_drift(self):
        self.binary.write_bytes(b'changed')
        with self.assertRaises(ValueError):m.stage(self.root, self.binary, self.base/'out')
        self.assertFalse((self.base/'out').exists())
    def test_patch_and_notice_drift(self):
        for name in ('build/portal-wlr/patch.py', 'open-source/licenses/dependencies/portal-LICENSE'):
            p = self.root/name;old = p.read_bytes();p.write_bytes(old+b'\n')
            with self.assertRaises(ValueError):m.stage(self.root, self.binary, self.base/'out')
            p.write_bytes(old)
        self.assertFalse((self.base/'out').exists())
    def test_no_overwrite(self):
        out = self.base/'out';out.mkdir();(out/'kept').write_text('existing')
        with self.assertRaises(ValueError):m.stage(self.root, self.binary, out)
        self.assertEqual((out/'kept').read_text(), 'existing')
    def test_symlink_binary_and_output(self):
        link = self.base/'link';link.symlink_to(self.binary)
        with self.assertRaises(ValueError):m.stage(self.root, link, self.base/'out')
        out = self.base/'out';out.symlink_to(self.base/'missing')
        with self.assertRaises(ValueError):m.stage(self.root, self.binary, out)
        self.assertTrue(out.is_symlink())
    def test_duplicate_lock_entry(self):
        p = self.root/'packaging/dock-dependencies.lock.json';lock = json.loads(p.read_text())
        lock['external_files'].append(lock['external_files'][0]);p.write_text(json.dumps(lock))
        with self.assertRaises(ValueError):m.stage(self.root, self.binary, self.base/'out')

if __name__ == '__main__':unittest.main()
