#!/usr/bin/env python3
"""Private Linux fixtures only; no phone, service, or target writes by collector."""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('adoption', Path(__file__).with_name('portal-adoption.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Adoption(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory(prefix='adoption-fixture-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        rows = []
        for i, (name, mode) in enumerate(sorted(m.policy.TARGETS.items())):
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            data = ('synthetic-payload-' + str(i)).encode()
            p.write_bytes(data)
            p.chmod(int(mode, 8))
            os.setxattr(p, 'user.test', b'preserved')
            os.utime(p, ns=(1000000000, 2000000000))
            rows.append(dict(target=name, mode=mode, sha256=hashlib.sha256(data).hexdigest()))
        return root, dict(schema=1, name='omarchy-portal', activation='none', files=rows)

    def test_readonly_exact_plan_missing_parents(self):
        root, receipt = self.fixture()
        before = {n: m.metadata((root/n).stat()) for n in m.policy.TARGETS}
        seen = m.collect(root)
        self.assertEqual(before, {n: m.metadata((root/n).stat()) for n in m.policy.TARGETS})
        self.assertFalse((root/'var').exists())
        plan = m.plan(seen, receipt)
        self.assertFalse(plan['commit_authorized'])
        self.assertEqual(plan['payload_mutations'], [])
        self.assertIn('var/lib/omarchy-s/owners', plan['required_missing_parents'])
        self.assertIn('exclusive-revalidation-before-commit', plan['remaining_gates'])
        self.assertEqual(seen['files'][receipt['files'][0]['target']]['xattrs'], {'user.test': 'cHJlc2VydmVk'})

    def test_existing_parents_and_baseline(self):
        root, receipt = self.fixture()
        (root/m.OWNER).parent.mkdir(parents=True)
        a, b = m.collect(root), m.collect(root)
        self.assertNotEqual(a['observation_id'], b['observation_id'])
        self.assertEqual(m.plan(b, receipt, a)['required_missing_parents'], [])

    def test_missing_and_mixed_payload(self):
        for missing in (True, False):
            root, receipt = self.fixture()
            p = root/receipt['files'][0]['target']
            if missing: p.unlink()
            else: p.write_bytes(b'other version')
            with self.assertRaises(ValueError): m.plan(m.collect(root), receipt)

    def test_mode_and_existing_sidecar_conflicts(self):
        root, receipt = self.fixture()
        p = root/receipt['files'][0]['target']
        p.chmod(0o600)
        with self.assertRaises(ValueError): m.plan(m.collect(root), receipt)
        p.chmod(int(receipt['files'][0]['mode'], 8))
        owner = root/m.OWNER
        owner.parent.mkdir(parents=True)
        owner.write_text('{}')
        with self.assertRaises(ValueError): m.plan(m.collect(root), receipt)

    def test_file_symlink_hardlink_fifo_refused(self):
        for kind in ('symlink', 'hardlink', 'fifo'):
            root, receipt = self.fixture()
            p = root/receipt['files'][0]['target']
            if kind == 'hardlink': os.link(p, root/'extra-link')
            else:
                p.unlink()
                if kind == 'symlink': p.symlink_to(root/receipt['files'][1]['target'])
                else: os.mkfifo(p)
            with self.assertRaises((ValueError, OSError)): m.collect(root)

    def test_parent_and_root_symlinks_refused(self):
        root, _ = self.fixture()
        (root/'var').symlink_to(root/'usr', target_is_directory=True)
        with self.assertRaises(OSError): m.collect(root)
        alias = root/'alias'
        alias.symlink_to(root, target_is_directory=True)
        with self.assertRaises(OSError): m.collect(alias)

    def test_bounded_file_and_noatime_permission_failure(self):
        root, _ = self.fixture()
        with patch.object(m, 'LIMIT', 3):
            with self.assertRaises(ValueError): m.collect(root)
        original = os.open
        def fail(path, flags, *args, **kwargs):
            if flags & os.O_NOATIME: raise PermissionError('no ownership capability')
            return original(path, flags, *args, **kwargs)
        with patch.object(m.os, 'open', side_effect=fail):
            with self.assertRaises(PermissionError): m.collect(root)

    def test_change_between_scans_refused(self):
        root, receipt = self.fixture()
        original = m.scan
        def drift(fd):
            result = original(fd)
            (root/receipt['files'][0]['target']).write_bytes(b'changed')
            return result
        with patch.object(m, 'scan', side_effect=drift):
            with self.assertRaises(ValueError): m.collect(root)

    def test_replacement_during_read_refused(self):
        root, receipt = self.fixture()
        p = root/receipt['files'][0]['target']
        original = os.read
        changed = False
        def swap(fd, size):
            nonlocal changed
            data = original(fd, size)
            if not changed:
                changed = True
                p.unlink()
                p.write_bytes(b'replacement')
            return data
        with patch.object(m.os, 'read', side_effect=swap):
            with self.assertRaises(ValueError): m.collect(root)

    def test_baseline_metadata_drift(self):
        root, receipt = self.fixture()
        before = m.collect(root)
        p = root/receipt['files'][0]['target']
        os.setxattr(p, 'user.test', b'changed')
        with self.assertRaises(ValueError): m.plan(m.collect(root), receipt, before)

    def test_incomplete_malformed_and_cross_mount_observations(self):
        root, receipt = self.fixture()
        observed = m.collect(root)
        bad = copy.deepcopy(observed)
        del bad['files'][m.OWNER]
        with self.assertRaises(ValueError): m.plan(bad, receipt)
        for key, value in [('nlink', 2), ('sha256', 'bad'), ('dev', observed['parents']['.']['dev']+1), ('xattrs', {'user.a': '!!!'})]:
            bad = copy.deepcopy(observed)
            bad['files'][receipt['files'][0]['target']][key] = value
            with self.assertRaises(ValueError): m.plan(bad, receipt)
        bad = copy.deepcopy(observed)
        bad['parents']['usr'] = None
        with self.assertRaises(ValueError): m.plan(bad, receipt)

    def test_existing_ownership_policy_not_weakened(self):
        root, receipt = self.fixture()
        observed = m.collect(root)
        identities = {n: {'sha256': row['sha256'], 'mode': format(row['mode'] & 0o7777, '04o')} for n, row in observed['files'].items() if n in m.policy.TARGETS}
        with self.assertRaises(ValueError): m.policy.plan(None, receipt, identities)
        self.assertFalse(m.plan(observed, receipt)['commit_authorized'])


if __name__ == '__main__':
    unittest.main()
