import copy
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('owner', Path(__file__).with_name('portal-ownership.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def receipt(letter):
    return {'schema': 1, 'name': 'omarchy-portal', 'activation': 'none',
            'files': [{'target': n, 'sha256': letter*64, 'mode': mode} for n, mode in sorted(m.TARGETS.items())]}

class Ownership(unittest.TestCase):
    def test_create_and_partial_rollback(self):
        new = receipt('a');empty = dict.fromkeys(m.TARGETS)
        p = m.plan(None, new, empty)
        self.assertEqual(m.check(p, empty, 'before-apply'), [])
        current = dict(empty);name = sorted(m.TARGETS)[0];current[name] = m.ownership(new)[name]
        rollback = m.check(p, current, 'before-rollback')
        self.assertEqual(len(rollback), 1)
        self.assertEqual(rollback[0]['action'], 'remove-created-file')
        self.assertEqual(m.check(p, empty, 'before-rollback'), [])
    def test_upgrade_all_crash_boundaries(self):
        old, new = receipt('a'), receipt('b')
        before, after = m.ownership(old), m.ownership(new)
        p = m.plan(old, new, before)
        names = sorted(m.TARGETS)
        for completed in range(4):
            current = dict(before)
            for name in names[:completed]:current[name] = after[name]
            rollback = m.check(p, current, 'before-rollback')
            self.assertEqual([r['target'] for r in rollback], list(reversed(names[:completed])))
            self.assertTrue(all(r['action'] == 'restore-verified-backup' for r in rollback))
    def test_noop(self):
        old = receipt('a');state = m.ownership(old)
        p = m.plan(old, old, state)
        self.assertTrue(all(e['action'] == 'unchanged' for e in p['entries']))
        self.assertEqual(m.check(p, state, 'before-rollback'), [])
    def test_unowned_identical_files_refused(self):
        new = receipt('a')
        with self.assertRaises(ValueError):m.plan(None, new, m.ownership(new))
    def test_drift_refused_before_apply_and_rollback(self):
        old, new = receipt('a'), receipt('b');p = m.plan(old, new, m.ownership(old))
        for phase in ('before-apply', 'before-rollback'):
            with self.assertRaises(ValueError):m.check(p, m.ownership(receipt('c')), phase)
        with self.assertRaises(ValueError):m.plan(old, new, m.ownership(new))
    def test_incomplete_duplicate_and_private_target(self):
        for kind in ('missing', 'duplicate', 'private', 'symlink', 'mode'):
            r = receipt('a')
            if kind == 'missing':r['files'].pop()
            if kind == 'duplicate':r['files'].append(copy.deepcopy(r['files'][0]))
            if kind == 'private':r['files'][0]['target'] = m.PREFIX+'allowed-inputs.json'
            if kind == 'symlink':r['files'][0]['link'] = '/etc/passwd'
            if kind == 'mode':r['files'][0]['mode'] = '04755'
            with self.assertRaises(ValueError):m.ownership(r)
    def test_plan_tampering_and_incomplete_observation(self):
        p = m.plan(None, receipt('a'), dict.fromkeys(m.TARGETS))
        p['entries'][0]['action'] = 'replace'
        with self.assertRaises(ValueError):m.check(p, dict.fromkeys(m.TARGETS), 'before-apply')
        with self.assertRaises(ValueError):m.inventory({})

if __name__ == '__main__':unittest.main()
