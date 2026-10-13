#!/usr/bin/env python3
"""Persistent fake-service contract tests. Never starts a portal or system service."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent

def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE/file)
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value

m = module('lifecycle', 'portal-lifecycle.py')
f = module('fixtures', 'test-portal-transaction.py')
r = module('retention', 'portal-retention.py')
tx = m.tx


class FakeService:
    """Atomic hook model persisted across coordinator deaths, not a real process."""
    def __init__(self, root, fail=None):
        self.root = root;self.path = root/'.fake-service.json';self.fail = fail
        if not self.path.exists():
            self.save({'running': self.disk(), 'events': []})
    def disk(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:return {n:tx.identity(tx.snapshot(fd,n)[1]) for n in tx.TARGETS[:-1]}
        finally:os.close(fd)
    def load(self):return json.loads(self.path.read_bytes())
    def save(self, value):
        draft=self.path.with_suffix('.tmp');draft.write_bytes(tx.encoded(value));os.replace(draft,self.path)
    def event(self, name, value=None):
        data=self.load();data['events'].append(name)
        if name=='quiesce' and self.fail!='quiesce':data['running']=None
        if name=='start' and self.fail!='start':data['running']=value
        self.save(data)
        if self.fail==name+'-raise':raise RuntimeError('injected hook exception')
        return self.fail!=name
    def quiesce(self):return self.event('quiesce')
    def stopped(self):return self.event('stopped') and self.load()['running'] is None
    def start(self, identity):
        assert self.load()['running'] is None, 'start while already running'
        assert self.disk()==identity, 'start with wrong file identity'
        return self.event('start',identity)
    def healthy(self, identity):
        return self.event('healthy') and self.load()['running']==identity and self.disk()==identity


@unittest.skipUnless(sys.platform=='linux','Linux transaction filesystem required')
class Lifecycle(unittest.TestCase):
    def fixture(self, seed=True):
        root=tx.initialize();stage=f.make_stage()
        self.addCleanup(shutil.rmtree,root,True);self.addCleanup(shutil.rmtree,stage,True)
        if seed:f.seed(root)
        service=FakeService(root);before=f.state(root);tx.prepare(root,stage)
        return root,stage,service,before
    def journal(self,root):return json.loads((root/tx.TX/'journal.json').read_bytes())
    def test_success_and_double_recovery(self):
        root,stage,h,before=self.fixture();j=m.apply(root,h)
        self.assertEqual(j['lifecycle']['phase'],'committed')
        self.assertEqual(h.load()['events'],['healthy','quiesce','stopped','start','healthy'])
        self.assertTrue(h.healthy(m.expected(j,'new')))
        for _ in range(2):
            j=m.recover(root,h);self.assertEqual(f.state(root),before)
            self.assertTrue(h.healthy(m.expected(j,'old')))
        self.assertEqual(r.finalize(root)['disposition'],'rolled-back')
    def test_stop_failures_preserve_payload(self):
        for fail in ('quiesce','stopped','quiesce-raise'):
            root,stage,h,before=self.fixture();h.fail=fail
            with self.assertRaises(RuntimeError):m.apply(root,h)
            self.assertEqual(f.state(root),before)
            h.fail=None;m.recover(root,h);self.assertEqual(f.state(root),before)
    def test_new_service_failures_leave_old_receipt(self):
        for fail in ('start','start-raise'):
            root,stage,h,before=self.fixture();h.fail=fail
            with self.assertRaises(RuntimeError):m.apply(root,h)
            self.assertEqual(f.state(root)[tx.OWNER],before[tx.OWNER])
            with self.assertRaises(ValueError):r.finalize(root)
            h.fail=None;m.recover(root,h);self.assertEqual(f.state(root),before)
    def test_new_health_failure_and_strict_boolean(self):
        for result in (False,1,None):
            root,stage,h,before=self.fixture();healthy=h.healthy;calls=[]
            def check(identity):
                calls.append(1)
                return healthy(identity) if len(calls)==1 else result
            with patch.object(h,'healthy',side_effect=check):
                with self.assertRaises(RuntimeError):m.apply(root,h)
            self.assertEqual(f.state(root)[tx.OWNER],before[tx.OWNER]);m.recover(root,h)
            self.assertEqual(f.state(root),before)
    def test_old_service_failure_prevents_finalization(self):
        for fail in ('start','healthy','stopped'):
            root,stage,h,before=self.fixture();m.apply(root,h);h.fail=fail
            with self.assertRaises(RuntimeError):m.recover(root,h)
            with self.assertRaises(ValueError):r.finalize(root)
            h.fail=None;m.recover(root,h);self.assertEqual(f.state(root),before);r.finalize(root)
    def test_existing_unhealthy_and_first_install_refused(self):
        root,stage,h,before=self.fixture();h.fail='healthy'
        with self.assertRaises(RuntimeError):m.apply(root,h)
        self.assertNotIn('lifecycle',self.journal(root));self.assertEqual(f.state(root),before)
        root,stage,h,before=self.fixture(False)
        with self.assertRaises(ValueError):m.apply(root,h)
        self.assertEqual(h.load()['events'],[]);self.assertEqual(f.state(root),before)
    def test_no_low_level_bypass_or_repeat_apply(self):
        root,stage,h,before=self.fixture();m.apply(root,h)
        with self.assertRaises(ValueError):tx.recover(root)
        with self.assertRaises(ValueError):tx.apply(root,lambda:True)
        with self.assertRaises(ValueError):m.apply(root,h)
        m.recover(root,h)
    def test_drift_blocks_hooks_and_mutating_health_refused(self):
        root,stage,h,before=self.fixture();m.apply(root,h)
        (root/tx.TARGETS[0]).write_bytes(b'external');events=h.load()['events']
        with self.assertRaises(RuntimeError):m.recover(root,h)
        self.assertEqual(h.load()['events'],events)
        root,stage,h,before=self.fixture();m.apply(root,h);healthy=h.healthy
        def mutate(identity):
            result=healthy(identity);(root/tx.TARGETS[0]).write_bytes(b'external');return result
        with patch.object(h,'healthy',side_effect=mutate):
            with self.assertRaises(RuntimeError):m.recover(root,h)
        self.assertEqual(self.journal(root)['lifecycle']['phase'],'starting-old')
    def test_lock_covers_hooks_and_unrelated_state(self):
        root,stage,h,before=self.fixture();unrelated=root/'other-session';unrelated.write_bytes(b'untouched')
        stop=h.quiesce
        def guarded():
            with self.assertRaises(BlockingIOError):tx.recover(root)
            return stop()
        with patch.object(h,'quiesce',side_effect=guarded):m.apply(root,h)
        self.assertEqual(unrelated.read_bytes(),b'untouched')
    def test_process_exit_every_boundary(self):
        code='''import importlib.util,os,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('t',sys.argv[1]);t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
count=0
def die(label):
 global count
 count+=1
 if count==int(sys.argv[4]):os._exit(75)
t.m.checkpoint=die;t.tx.checkpoint=die
root=Path(sys.argv[2]);h=t.FakeService(root)
getattr(t.m,sys.argv[3])(root,h)
'''
        total=0
        for operation in ('apply','recover'):
            root,stage,h,before=self.fixture()
            if operation=='recover':m.apply(root,h)
            labels=[]
            with patch.object(m,'checkpoint',side_effect=labels.append),patch.object(tx,'checkpoint',side_effect=labels.append):getattr(m,operation)(root,h)
            for index,label in enumerate(labels,1):
                with self.subTest(operation=operation,label=label,index=index):
                    root,stage,h,before=self.fixture()
                    if operation=='recover':m.apply(root,h)
                    result=subprocess.run([sys.executable,'-c',code,str(Path(__file__).resolve()),str(root),operation,str(index)],capture_output=True)
                    self.assertEqual(result.returncode,75,result.stderr)
                    if 'lifecycle' not in self.journal(root):
                        # Death during first intent write: no side-effecting hook ran.
                        self.assertEqual(h.load()['running'],h.disk());tx.recover(root)
                    else:
                        m.recover(root,h);m.recover(root,h)
                    self.assertEqual(f.state(root),before)
                    self.assertEqual(h.load()['running'],h.disk())
                    r.finalize(root);total+=1
            print('lifecycle crash boundaries',operation,len(labels),flush=True)
        print('lifecycle abrupt exits verified',total,flush=True)

if __name__=='__main__':unittest.main()
