#!/usr/bin/env python3
"""Linux isolated-root tests; no device or service access."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).with_name('portal-transaction.py').resolve()
spec = importlib.util.spec_from_file_location('txn', MODULE)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def make_stage():
    root = Path(tempfile.mkdtemp(prefix='portal-candidate-')).resolve()
    rows = []
    for i, (name, mode) in enumerate(sorted(m.policy.TARGETS.items())):
        dest = root/'rootfs'/name;dest.parent.mkdir(parents=True, exist_ok=True)
        data = ('new-'+str(i)).encode();dest.write_bytes(data);dest.chmod(int(mode, 8))
        rows.append({'target':name, 'sha256':m.sha(data), 'mode':mode})
    receipt = {'schema':1, 'name':'omarchy-portal', 'activation':'none', 'files':rows}
    (root/'ownership.json').write_bytes(m.encoded(receipt))
    return root

def seed(root):
    rows = []
    for i, (name, mode) in enumerate(sorted(m.policy.TARGETS.items())):
        dest = root/name;data = ('old-'+str(i)).encode();dest.write_bytes(data);dest.chmod(int(mode,8))
        os.setxattr(dest, 'user.portal-test', b'preserve')
        os.utime(dest, ns=(1000000000+i,2000000000+i))
        rows.append({'target':name,'sha256':m.sha(data),'mode':mode})
    (root/m.OWNER).write_bytes(m.encoded({'schema':1,'name':'omarchy-portal','activation':'none','files':rows}))
    (root/m.OWNER).chmod(0o644)
    os.setxattr(root/m.OWNER,'user.portal-test',b'owner-receipt')

def state(root):
    with m.locked(root) as fd:return {n:m.snapshot(fd,n) for n in m.TARGETS}

@unittest.skipUnless(sys.platform=='linux', 'Linux fsync/xattr/descriptor tests required')
class Transaction(unittest.TestCase):
    def fixture(self, upgrade=False):
        root=m.initialize();stage=make_stage()
        self.addCleanup(shutil.rmtree,root,True);self.addCleanup(shutil.rmtree,stage,True)
        if upgrade:seed(root)
        return root,stage
    def test_install_upgrade_rollback_metadata(self):
        for upgrade in (False,True):
            root,stage=self.fixture(upgrade);before=state(root)
            m.prepare(root,stage);m.apply(root,lambda:True)
            current=state(root)
            self.assertTrue(all(current[n][0].startswith(b'new-') for n in m.policy.TARGETS))
            for _ in range(2):m.recover(root);self.assertEqual(state(root),before)
    def test_noop_preserves_metadata(self):
        root,stage=self.fixture();m.prepare(root,stage);m.apply(root,lambda:True)
        shutil.rmtree(root/m.TX)  # Laboratory setup only, never an executor operation.
        before=state(root);m.prepare(root,stage);m.apply(root,lambda:True)
        self.assertEqual(state(root),before);m.recover(root);self.assertEqual(state(root),before)
    def test_health_failure_keeps_old_receipt(self):
        root,stage=self.fixture(True);before=state(root);m.prepare(root,stage)
        with self.assertRaises(RuntimeError):m.apply(root,lambda:False)
        self.assertEqual(state(root)[m.OWNER],before[m.OWNER]);m.recover(root);self.assertEqual(state(root),before)
    def test_health_mutation_rejected(self):
        root,stage=self.fixture(True);m.prepare(root,stage)
        def mutate():
            (root/m.TARGETS[0]).write_bytes(b'external');return True
        with self.assertRaises(RuntimeError):m.apply(root,mutate)
        with self.assertRaises(RuntimeError):m.recover(root)
        self.assertEqual(state(root)[m.TARGETS[0]][0],b'external')
    def test_unowned_and_stage_drift(self):
        root,stage=self.fixture();(root/m.TARGETS[0]).write_bytes(b'unowned')
        with self.assertRaises(ValueError):m.prepare(root,stage)
        self.assertFalse((root/m.TX).exists())
        root,stage=self.fixture();(stage/'rootfs'/m.TARGETS[0]).write_bytes(b'drift')
        with self.assertRaises(ValueError):m.prepare(root,stage)
        self.assertFalse((root/m.TX).exists())
    def test_lock_and_root_guards(self):
        root,stage=self.fixture()
        with m.locked(root):
            with self.assertRaises(BlockingIOError):m.prepare(root,stage)
        (root/m.MARKER).unlink()
        with self.assertRaises(ValueError):m.prepare(root,stage)
        with self.assertRaises(ValueError):m.prepare(Path('/'),stage)
    def test_links_and_special_files(self):
        for kind in ('symlink','hardlink','fifo','parent'):
            root,stage=self.fixture();p=root/m.TARGETS[0]
            if kind=='symlink':p.symlink_to('/etc/passwd')
            if kind=='hardlink':
                other=root/'other';other.write_bytes(b'outside');os.link(other,p)
            if kind=='fifo':os.mkfifo(p)
            if kind=='parent':p.parent.rmdir();p.parent.symlink_to(stage)
            with self.assertRaises((ValueError,OSError)):m.prepare(root,stage)
            self.assertFalse((root/m.TX).exists())
    def test_backup_and_current_corruption_refused(self):
        for what in ('backup','current','journal-target'):
            root,stage=self.fixture(True);before=state(root);m.prepare(root,stage)
            if what=='backup':(root/m.TX/'0.old').write_bytes(b'corrupt')
            if what=='current':(root/m.TARGETS[0]).write_bytes(b'external')
            if what=='journal-target':
                p=root/m.TX/'journal.json';j=json.loads(p.read_text());j['entries'][0]['target']='../../etc/passwd';p.write_bytes(m.encoded(j))
            damaged=state(root)
            for op in (lambda:m.apply(root,lambda:True),lambda:m.recover(root)):
                with self.assertRaises((ValueError,RuntimeError)):op()
                self.assertEqual(state(root),damaged)
    def test_partial_apply_requires_recovery(self):
        root,stage=self.fixture(True);before=state(root);m.prepare(root,stage)
        def stop(label):
            if label=='new-0:directory-fsync':raise RuntimeError('interrupt')
        with patch.object(m,'checkpoint',side_effect=stop):
            with self.assertRaises(RuntimeError):m.apply(root,lambda:True)
        with self.assertRaises(ValueError):m.apply(root,lambda:True)
        m.recover(root);self.assertEqual(state(root),before)
    def test_sync_failure_before_rename(self):
        root,stage=self.fixture(True);before=state(root);m.prepare(root,stage)
        with patch.object(m.os,'fsync',side_effect=OSError('sync failure')):
            with self.assertRaises(OSError):m.apply(root,lambda:True)
        self.assertEqual(state(root),before);m.recover(root);self.assertEqual(state(root),before)
    def test_temporary_corruption_refuses_before_mutation(self):
        root,stage=self.fixture(True);before=state(root);m.prepare(root,stage)
        p=(root/m.TARGETS[2]).parent/'.portal-transaction-2.tmp';p.write_bytes(b'unrelated')
        for operation in (lambda:m.apply(root,lambda:True),lambda:m.recover(root)):
            with self.assertRaises(RuntimeError):operation()
            self.assertEqual(state(root),before)
    def test_disk_full_and_metadata_failure(self):
        for call in ('write','setxattr'):
            root,stage=self.fixture(True);before=state(root);m.prepare(root,stage)
            with patch.object(m.os,call,side_effect=OSError('injected I/O failure')):
                with self.assertRaises(OSError):m.apply(root,lambda:True)
            self.assertEqual(state(root),before)
            m.recover(root);self.assertEqual(state(root),before)
    def test_second_prepare_and_wrong_root(self):
        root,stage=self.fixture(True);m.prepare(root,stage)
        with self.assertRaises(ValueError):m.prepare(root,stage)
        other,_=self.fixture(True);shutil.copytree(root/m.TX,other/m.TX)
        with self.assertRaises(ValueError):m.recover(other)

    def test_late_rollback_drift_is_not_marked_successful(self):
        root,stage=self.fixture(True);m.prepare(root,stage);m.apply(root,lambda:True)
        def drift(label):
            if label=='old-0:directory-fsync':(root/m.TARGETS[2]).write_bytes(b'external')
        with patch.object(m,'checkpoint',side_effect=drift):
            with self.assertRaises(RuntimeError):m.recover(root)
        journal=json.loads((root/m.TX/'journal.json').read_text())
        self.assertEqual(journal['state'],'committed-test')
        self.assertEqual(state(root)[m.TARGETS[2]][0],b'external')

    def test_stage_does_not_need_xattrs_but_target_does(self):
        root,stage=self.fixture()
        with patch.object(m.os,'listxattr',side_effect=OSError('unsupported xattrs')):
            receipt,payload=m.candidate(stage)
            self.assertEqual(len(payload),4)
            with self.assertRaises(OSError):m.prepare(root,stage)
        self.assertFalse((root/m.TX).exists())

    def test_short_writes(self):
        root,stage=self.fixture(True);before=state(root);original=os.write
        with patch.object(m.os,'write',side_effect=lambda fd,data:original(fd,data[:2])):
            m.prepare(root,stage);m.apply(root,lambda:True);m.recover(root)
        self.assertEqual(state(root),before)
    @unittest.skipUnless(os.geteuid()==0,'root-owned Linux container for uid/gid preservation')
    def test_different_owner_preserved(self):
        root,stage=self.fixture(True)
        for name in m.TARGETS:os.chown(root/name,1000,1001)
        before=state(root);m.prepare(root,stage);m.apply(root,lambda:True)
        self.assertTrue(all(row[1]['uid']==1000 and row[1]['gid']==1001 for row in state(root).values()))
        m.recover(root);self.assertEqual(state(root),before)
    def test_abrupt_exit_at_every_checkpoint(self):
        program='''import importlib.util,os,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('m',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
count=0
def die(label):
 global count
 count+=1
 if count==int(sys.argv[5]):os._exit(75)
m.checkpoint=die
root=Path(sys.argv[2]);stage=Path(sys.argv[3]);op=sys.argv[4]
if op=='prepare':m.prepare(root,stage)
elif op=='apply':m.apply(root,lambda:True)
else:m.recover(root)
'''
        total=0
        for upgrade in (False,True):
            for operation in ('prepare','apply','recover'):
                root,stage=self.fixture(upgrade);labels=[]
                if operation!='prepare':m.prepare(root,stage)
                if operation=='recover':m.apply(root,lambda:True)
                with patch.object(m,'checkpoint',side_effect=labels.append):
                    if operation=='prepare':m.prepare(root,stage)
                    elif operation=='apply':m.apply(root,lambda:True)
                    else:m.recover(root)
                for index,label in enumerate(labels,1):
                    with self.subTest(upgrade=upgrade,operation=operation,checkpoint=label):
                        root,stage=self.fixture(upgrade);before=state(root)
                        if operation!='prepare':m.prepare(root,stage)
                        if operation=='recover':m.apply(root,lambda:True)
                        result=subprocess.run([sys.executable,'-c',program,str(MODULE),str(root),str(stage),operation,str(index)],capture_output=True)
                        self.assertEqual(result.returncode,75,result.stderr)
                        if (root/m.TX/'journal.json').exists():
                            m.recover(root);m.recover(root)
                        else:
                            with self.assertRaises(ValueError):m.recover(root)
                        self.assertEqual(state(root),before)
                        total+=1
                print('crash boundaries', 'upgrade' if upgrade else 'create',operation,len(labels),flush=True)
        print('abrupt exits verified',total,flush=True)

if __name__=='__main__':unittest.main()
