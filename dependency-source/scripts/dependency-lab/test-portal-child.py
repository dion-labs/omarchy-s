#!/usr/bin/env python3
"""Disposable Linux child tests; no portal daemon or phone access."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent

def module(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

c=module('child','portal-child.py');f=module('fixtures','test-portal-lifecycle.py');m=f.m;tx=m.tx

@unittest.skipUnless(sys.platform=='linux','Linux pidfd and peer credentials required')
class Children(unittest.TestCase):
    def fixture(self):
        root=tx.initialize();stage=f.f.make_stage();f.f.seed(root)
        self.addCleanup(shutil.rmtree,root,True);self.addCleanup(shutil.rmtree,stage,True)
        return root,stage
    def adapter(self,root,mode='normal'):
        h=c.Child(root,timeout=0.6,mode=mode);self.addCleanup(h.close);return h
    def test_real_update_recovery_and_health_identity(self):
        root,stage=self.fixture();h=self.adapter(root);old=c.disk(h.fd);before=f.f.state(root)
        self.assertTrue(h.start(old));self.assertTrue(h.healthy(old));tx.prepare(root,stage)
        j=m.apply(root,h);self.assertTrue(h.healthy(m.expected(j,'new')))
        self.assertFalse(h.healthy(old))
        for _ in range(2):m.recover(root,h);self.assertEqual(f.f.state(root),before);self.assertTrue(h.healthy(old))
        f.r.finalize(root)
    def test_failed_start_modes_bounded_and_recoverable(self):
        for mode in ('no-ready','bad-health','crash','silent'):
            root,stage=self.fixture();h=self.adapter(root);old=c.disk(h.fd);before=f.f.state(root)
            self.assertTrue(h.start(old));tx.prepare(root,stage);h.mode=mode;start=time.monotonic()
            with self.assertRaises(RuntimeError):m.apply(root,h)
            self.assertLess(time.monotonic()-start,4)
            self.assertEqual(f.f.state(root)[tx.OWNER],before[tx.OWNER]);h.mode='normal';m.recover(root,h)
            self.assertTrue(h.healthy(old));self.assertEqual(f.f.state(root),before)
    def test_ignore_term_is_killed_within_bound(self):
        root,stage=self.fixture();h=self.adapter(root,'ignore-term');self.assertTrue(h.start(c.disk(h.fd)))
        start=time.monotonic();labels=[]
        with patch.object(c,'checkpoint',side_effect=labels.append):self.assertTrue(h.quiesce())
        self.assertIn('child:after-kill',labels);self.assertLess(time.monotonic()-start,3);self.assertTrue(h.stopped())
    def test_identity_mismatch_never_signals(self):
        root,stage=self.fixture();h=self.adapter(root);self.assertTrue(h.start(c.disk(h.fd)))
        p=root/c.RECORD;raw=p.read_bytes();value=json.loads(raw);value['start']='wrong';p.write_bytes(tx.encoded(value))
        try:
            with patch.object(c.signal,'pidfd_send_signal',side_effect=AssertionError('must not signal')):
                with self.assertRaises(ValueError):h.quiesce()
        finally:p.write_bytes(raw)
        self.assertTrue(h.healthy(c.disk(h.fd)))
    def test_atomic_identity_replacement_retries_within_start_deadline(self):
        root,stage=self.fixture();h=self.adapter(root);identity=c.disk(h.fd)
        original=c.tx.read_at;armed=[];failures=[]
        def arm(label):
            if label=='child:spawned':armed.append(True)
        def read(fd,name,*args,**kwargs):
            if armed and name==c.RECORD and not failures:
                failures.append(True);raise RuntimeError('Concurrent snapshot change')
            return original(fd,name,*args,**kwargs)
        with patch.object(c,'checkpoint',side_effect=arm),patch.object(c.tx,'read_at',side_effect=read):
            self.assertTrue(h.start(identity))
        self.assertEqual(len(failures),1);self.assertTrue(h.healthy(identity))
    def test_socket_peer_mismatch_fails_health(self):
        root,stage=self.fixture();h=self.adapter(root);identity=c.disk(h.fd)
        self.assertTrue(h.start(identity))
        with patch.object(c.struct,'unpack',return_value=(1,os.geteuid(),os.getegid())):
            self.assertFalse(h.healthy(identity))
        self.assertTrue(h.healthy(identity))
    def test_controller_lock_and_invalid_options(self):
        root,stage=self.fixture();h=self.adapter(root)
        with self.assertRaises(BlockingIOError):c.Child(root)
        for timeout in (0,float('nan'),6):
            with self.assertRaises(ValueError):c.Child(root,timeout=timeout)
        with self.assertRaises(ValueError):c.Child(Path('/'))
    def test_child_exit_and_payload_drift_fail_health(self):
        root,stage=self.fixture();h=self.adapter(root);identity=c.disk(h.fd);self.assertTrue(h.start(identity))
        (root/tx.TARGETS[0]).write_bytes(b'external');self.assertFalse(h.healthy(identity))
        self.assertTrue(h.quiesce());self.assertFalse(h.healthy(identity))
    def test_coordinator_death_and_new_coordinator_recovery(self):
        code='''import importlib.util,sys,os
from pathlib import Path
s=importlib.util.spec_from_file_location('t',sys.argv[1]);t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
root=Path(sys.argv[2]);stage=Path(sys.argv[3]);h=t.c.Child(root,timeout=0.6)
assert h.start(t.c.disk(h.fd));t.tx.prepare(root,stage)
if sys.argv[4]=='recover':t.m.apply(root,h)
count=0
def die(label):
 global count
 count+=1
 if count==int(sys.argv[5]):os._exit(75)
t.c.checkpoint=die;t.m.checkpoint=die
getattr(t.m,sys.argv[4])(root,h)
'''
        total=0
        for operation in ('apply','recover'):
            root,stage=self.fixture();h=c.Child(root,timeout=0.6)
            try:
                self.assertTrue(h.start(c.disk(h.fd)));tx.prepare(root,stage)
                if operation=='recover':m.apply(root,h)
                labels=[]
                with patch.object(c,'checkpoint',side_effect=labels.append),patch.object(m,'checkpoint',side_effect=labels.append):getattr(m,operation)(root,h)
            finally:h.close()
            for index,label in enumerate(labels,1):
                with self.subTest(operation=operation,label=label):
                    root,stage=self.fixture();before=f.f.state(root)
                    result=subprocess.run([sys.executable,'-c',code,str(Path(__file__).resolve()),str(root),str(stage),operation,str(index)],capture_output=True,timeout=10)
                    self.assertEqual(result.returncode,75,result.stderr)
                    h=c.Child(root,timeout=0.6)
                    try:
                        # Prior child is parent-death-bound; recovery may safely see it exiting.
                        m.recover(root,h);m.recover(root,h)
                        self.assertEqual(f.f.state(root),before);self.assertTrue(h.healthy(c.disk(h.fd)))
                        f.r.finalize(root);total+=1
                    finally:h.close()
            print('real child coordinator exits',operation,len(labels),flush=True)
        print('real child coordinator exits verified',total,flush=True)

if __name__=='__main__':unittest.main()
