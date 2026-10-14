#!/usr/bin/env python3
"""Cross-process cooperative fence and coordinator-death checks, private roots only."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
HERE=Path(__file__).resolve().parent

def module(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=module('fence','portal-fence.py');f=module('fixtures','test-portal-lifecycle.py')

@unittest.skipUnless(sys.platform=='linux','Linux flock and metadata required')
class Fences(unittest.TestCase):
 def fixture(self):
  root=f.tx.initialize();stage=f.f.make_stage();self.addCleanup(shutil.rmtree,root,True);self.addCleanup(shutil.rmtree,stage,True)
  f.f.seed(root);hooks=f.FakeService(root);before=f.f.state(root);f.tx.prepare(root,stage)
  return root,hooks,before,m.Fence(root,timeout=.08)
 def child(self,root,code):
  prefix='import sys,os,time;sys.path.insert(0,'+repr(str(HERE))+');exec('+repr("import importlib.util\ndef load(n,p):\n s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m\n")+');'
  prefix+='m=load("fence",'+repr(str(HERE/'portal-fence.py'))+');f=load("fixtures",'+repr(str(HERE/'test-portal-lifecycle.py'))+');root=f.Path('+repr(str(root))+');g=m.Fence(root,timeout=.08);\n'
  return subprocess.Popen([sys.executable,'-c',prefix+code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 def test_client_blocks_update_with_deadline(self):
  root,h,before,g=self.fixture()
  with g.client():
   start=time.monotonic()
   with self.assertRaises(m.a.Refused):m.a.run(root,h,g)
   self.assertLess(time.monotonic()-start,1)
  self.assertEqual(f.f.state(root),before);self.assertEqual(h.load()['events'],[])
 def test_update_blocks_cross_process_client(self):
  root,h,before,g=self.fixture()
  with g.acquire():
   p=self.child(root,'with g.client(): print("entered")\n');out,err=p.communicate(timeout=3)
   self.assertNotEqual(p.returncode,0);self.assertNotIn('entered',out)
  with g.client():pass
 def test_parallel_clients_and_dead_client_release(self):
  root,h,before,g=self.fixture()
  p=self.child(root,'with g.client():\n print("ready",flush=True)\n time.sleep(10)\n')
  try:
   self.assertEqual(p.stdout.readline().strip(),'ready')
   with g.client():pass
   with self.assertRaises(m.a.Refused):
    with g.acquire():pass
  finally:p.kill();p.communicate(timeout=3)
  with g.acquire():pass
 def test_update_and_explicit_rollback(self):
  root,h,before,g=self.fixture();m.a.run(root,h,g);m.a.run(root,h,g,recover=True)
  self.assertEqual(f.f.state(root),before)
  with g.client():pass
 def test_exception_retains_marker_until_reconciled(self):
  root,h,before,g=self.fixture();h.fail='quiesce-raise'
  with self.assertRaises(RuntimeError):m.a.run(root,h,g)
  with self.assertRaises(m.a.Refused):
   with g.client():pass
  h.fail=None;g.reconcile(h);self.assertEqual(f.f.state(root),before)
  with g.client():pass
 def test_expired_and_replaced_lease(self):
  root,h,before,g=self.fixture()
  with g.acquire() as lease:self.assertTrue(lease.observe()['complete'])
  with self.assertRaises(m.a.Refused):lease.observe()
  with self.assertRaises(m.a.Refused):
   with g.acquire() as lease:
    os.rename(root/m.LOCK,root/'old-lock');(root/m.LOCK).touch(mode=0o600);lease.observe()
 def test_symlink_lock_refused(self):
  root,h,before,g=self.fixture();(root/m.LOCK).symlink_to('/dev/null')
  with self.assertRaises(OSError):
   with g.client():pass
 def test_invalid_deadline(self):
  for value in (True,0,3,float('inf'),float('nan')):
   with self.assertRaises(ValueError):m.Fence('/unused',value)
 def test_coordinator_crash_boundaries(self):
  cases=[('fence','fence-durable'),('fence','before-clear'),('life','service:quiesced'),('life','service:stopped'),('life','service:started'),('life','service:healthy')]
  for owner,label in cases:
   with self.subTest(label=label):
    root,h,before,g=self.fixture()
    code='target=m if '+repr(owner)+'=="fence" else m.a.lifecycle\ntarget.checkpoint=lambda label: os._exit(91) if label=='+repr(label)+' else None\nm.a.run(root,f.FakeService(root),g)\n'
    p=self.child(root,code);out,err=p.communicate(timeout=5);self.assertEqual(p.returncode,91,err)
    with self.assertRaises(m.a.Refused):
     with g.client():pass
    with self.assertRaises(m.a.Refused):
     with g.acquire():pass
    g.reconcile(h);self.assertEqual(f.f.state(root),before)
    with g.client():pass
  print('admission coordinator exits verified',len(cases),flush=True)
 def test_reconciliation_crash_stays_closed(self):
  root,h,before,g=self.fixture()
  with self.assertRaises(RuntimeError):
   with g.acquire():raise RuntimeError('interrupted')
  p=self.child(root,'m.checkpoint=lambda label: os._exit(92) if label=="reconciled-before-clear" else None\ng.reconcile(f.FakeService(root))\n');out,err=p.communicate(timeout=5);self.assertEqual(p.returncode,92,err)
  with self.assertRaises(m.a.Refused):
   with g.client():pass
  g.reconcile(h)
  with g.client():pass
  print('admission reconciliation exits verified 1',flush=True)

if __name__=='__main__':unittest.main()
