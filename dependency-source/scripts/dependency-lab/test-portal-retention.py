#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

MODULE=Path(__file__).with_name('portal-retention.py').resolve()
s=importlib.util.spec_from_file_location('retention',MODULE);r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
s=importlib.util.spec_from_file_location('fixtures',Path(__file__).with_name('test-portal-transaction.py'));f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
m=r.tx

def observed(root):
    with m.locked(root) as fd:return {n:m.snapshot(fd,n) for n in m.TARGETS}

def variant(stage,label):
    p=stage/'ownership.json';receipt=json.loads(p.read_text())
    for row in receipt['files']:
        dest=stage/'rootfs'/row['target'];data=(label+row['target']).encode();dest.write_bytes(data)
        row['sha256']=m.sha(data)
    p.write_bytes(m.encoded(receipt))

@unittest.skipUnless(sys.platform=='linux','Linux transaction filesystem required')
class Retention(unittest.TestCase):
    def fixture(self,rollback=False):
        root=m.initialize();stage=f.make_stage();f.seed(root)
        self.addCleanup(shutil.rmtree,root,True);self.addCleanup(shutil.rmtree,stage,True)
        m.prepare(root,stage);m.apply(root,lambda:True)
        if rollback:m.recover(root)
        return root,stage
    def test_finalize_retains_then_explicit_prune(self):
        for rollback in (False,True):
            root,stage=self.fixture(rollback);before=observed(root)
            handle=r.finalize(root);self.assertIsNone(r.finalize(root))
            self.assertFalse((root/m.TX).exists());self.assertTrue((root/handle['history']/'0.old').exists())
            self.assertEqual(r.histories(root),[handle]);self.assertEqual(observed(root),before)
            for _ in range(2):self.assertEqual(r.prune(root,handle['history'],handle['close_sha256'])['state'],'pruned')
            self.assertEqual(observed(root),before);self.assertFalse((root/handle['history']).exists())
            self.assertEqual(r.prune_receipts(root)[0]['state'],'pruned')
    def test_repeated_updates_and_failed_update_recovery(self):
        root,stage=self.fixture();first=observed(root);handles=[r.finalize(root)]
        variant(stage,'second');m.prepare(root,stage)
        with self.assertRaises(RuntimeError):m.apply(root,lambda:False)
        m.recover(root);self.assertEqual(observed(root),first);handles.append(r.finalize(root))
        for i in range(4):
            variant(stage,'version-'+str(i));m.prepare(root,stage);m.apply(root,lambda:True);handles.append(r.finalize(root))
        before=observed(root);self.assertEqual(len({h['history'] for h in handles}),6)
        # Cleanup old history is independent of a newly prepared transaction.
        m.prepare(root,stage)
        with m.locked(root) as fd:active=m.snapshot(fd,m.TX+'/journal.json')
        for h in handles:r.prune(root,h['history'],h['close_sha256'])
        with m.locked(root) as fd:self.assertEqual(m.snapshot(fd,m.TX+'/journal.json'),active)
        self.assertEqual(observed(root),before);m.recover(root);r.finalize(root)
    def test_prepared_and_incomplete_refused(self):
        root,stage=self.fixture();m.recover(root);r.finalize(root);m.prepare(root,stage)
        with self.assertRaises(ValueError):r.finalize(root)
        (root/m.TX/'journal.json').unlink()
        with self.assertRaises(ValueError):r.finalize(root)
    def test_drift_and_unknown_entries_preserved(self):
        for kind in ('target','extra','backup'):
            root,stage=self.fixture();before=observed(root)
            if kind=='target':(root/m.TARGETS[0]).write_bytes(b'external')
            if kind=='extra':(root/m.TX/'unknown').write_bytes(b'keep')
            if kind=='backup':(root/m.TX/'0.old').write_bytes(b'bad')
            changed=observed(root)
            with self.assertRaises((ValueError,RuntimeError)):r.finalize(root)
            self.assertTrue((root/m.TX).exists());self.assertEqual(observed(root),changed)
    def test_cleanup_identity_and_unsafe_contents(self):
        for kind in ('digest','extra','link','hardlink','drift'):
            root,stage=self.fixture();h=r.finalize(root);archive=root/h['history'];before=observed(root)
            if kind=='extra':(archive/'unknown').write_bytes(b'keep')
            if kind=='link':(archive/'0.old').unlink();(archive/'0.old').symlink_to('/etc/passwd')
            if kind=='hardlink':os.link(archive/'0.old',root/'other')
            if kind=='drift':(archive/'0.old').write_bytes(b'drift')
            digest='0'*64 if kind=='digest' else h['close_sha256']
            count=len(list(archive.iterdir()))
            with self.assertRaises((ValueError,RuntimeError,OSError)):r.prune(root,h['history'],digest)
            self.assertEqual(len(list(archive.iterdir())),count);self.assertEqual(observed(root),before)
    def test_close_decision_blocks_rollback(self):
        root,stage=self.fixture()
        def stop(label):
            if label=='close.json:directory-fsync':raise RuntimeError('stop')
        with patch.object(r,'checkpoint',side_effect=stop):
            with self.assertRaises(RuntimeError):r.finalize(root)
        with self.assertRaises(ValueError):m.recover(root)
        self.assertIsNotNone(r.finalize(root))
    def test_short_writes_and_sync_failure(self):
        root,stage=self.fixture();original=os.write
        with patch.object(r.os,'write',side_effect=lambda fd,data:original(fd,data[:3])):
            h=r.finalize(root)
            r.prune(root,h['history'],h['close_sha256'])
        root,stage=self.fixture();before=observed(root)
        with patch.object(r.os,'fsync',side_effect=OSError('sync failure')):
            with self.assertRaises(OSError):r.finalize(root)
        self.assertEqual(observed(root),before);h=r.finalize(root);r.prune(root,h['history'],h['close_sha256'])
    def test_resume_cleanup_from_saved_receipt(self):
        root,stage=self.fixture();h=r.finalize(root);before=observed(root)
        def stop(label):
            if label=='prune:unlink-close.json':raise RuntimeError('interrupted')
        with patch.object(r,'checkpoint',side_effect=stop):
            with self.assertRaises(RuntimeError):r.prune(root,h['history'],h['close_sha256'])
        with self.assertRaises(ValueError):r.histories(root)
        saved=r.prune_receipts(root)[0];self.assertEqual(saved['state'],'pruning')
        r.prune(root,saved['history'],saved['close_sha256'])
        self.assertEqual(observed(root),before)
    def test_legacy_journal_can_recover_but_not_finalize(self):
        root,stage=self.fixture();p=root/m.TX/'journal.json';j=json.loads(p.read_bytes())
        del j['transaction_id'];p.write_bytes(m.encoded(j))
        with self.assertRaises(ValueError):r.finalize(root)
        m.recover(root)
        with self.assertRaises(ValueError):r.finalize(root)
    def test_unsafe_names_and_roots(self):
        root,stage=self.fixture()
        for name in ('../other','.portal-history-../other','.portal-transaction'):
            with self.assertRaises(ValueError):r.prune(root,name,'0'*64)
        with self.assertRaises(ValueError):r.finalize(Path('/'))
    def test_process_exit_every_boundary(self):
        code='''import importlib.util,os,sys,json
from pathlib import Path
s=importlib.util.spec_from_file_location('r',sys.argv[1]);r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
count=0
def die(label):
 global count
 count+=1
 if count==int(sys.argv[5]):os._exit(75)
r.checkpoint=die
root=Path(sys.argv[2]);operation=sys.argv[3];handle=json.loads(sys.argv[4])
if operation=='finalize':r.finalize(root)
else:r.prune(root,handle['history'],handle['close_sha256'])
'''
        total=0
        for rollback in (False,True):
            for operation in ('finalize','prune'):
                root,stage=self.fixture(rollback);h=r.finalize(root) if operation=='prune' else None;labels=[]
                with patch.object(r,'checkpoint',side_effect=labels.append):
                    if operation=='finalize':r.finalize(root)
                    else:r.prune(root,h['history'],h['close_sha256'])
                for index,label in enumerate(labels,1):
                    with self.subTest(rollback=rollback,operation=operation,label=label):
                        root,stage=self.fixture(rollback);before=observed(root);h=r.finalize(root) if operation=='prune' else None
                        result=subprocess.run([sys.executable,'-c',code,str(MODULE),str(root),operation,json.dumps(h),str(index)],capture_output=True)
                        self.assertEqual(result.returncode,75,result.stderr)
                        if operation=='finalize':
                            r.finalize(root);h=r.histories(root)[0]
                        r.prune(root,h['history'],h['close_sha256']);r.prune(root,h['history'],h['close_sha256'])
                        self.assertEqual(observed(root),before)
                        self.assertFalse((root/m.TX).exists());self.assertFalse((root/h['history']).exists())
                        m.prepare(root,stage);m.apply(root,lambda:True);m.recover(root)
                        self.assertEqual(observed(root),before);total+=1
                print('retention crash boundaries',rollback,operation,len(labels),flush=True)
        print('retention abrupt exits verified',total,flush=True)

if __name__=='__main__':unittest.main()
