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
 def test_capture_client_death_keeps_durable_refusal(self):
  root,h,before,g=self.fixture()
  p=self.child(root,'with g.capture_client(): os._exit(93)\n');out,err=p.communicate(timeout=3);self.assertEqual(p.returncode,93,err)
  self.assertTrue(list(root.glob(m.CAPTURE_PREFIX+'*')))
  with self.assertRaises(m.a.Refused):
   with g.acquire():pass
  with self.assertRaises(m.a.Refused):g.reconcile(h)
  self.assertEqual(f.f.state(root),before)
  print('capture client exits verified 1',flush=True)
 def test_capture_probe_requires_strict_confirmation(self):
  root,h,before,g=self.fixture()
  with g.capture_client() as receipt:
   for value in (False,None,1,[]):
    with self.assertRaises(m.a.Refused):receipt.confirm_cleanup(lambda:value)
   receipt.confirm_cleanup(lambda:True)
   with self.assertRaises(m.a.Refused):receipt.confirm_cleanup(lambda:True)
  with g.acquire():pass
 def identity(self):
  return dict(bus_id='a'*32,frontend_owner=':1.2',backend_owner=':1.3',session='/org/freedesktop/portal/desktop/session/1_4/r1',node=42,pipewire_cookie=123)
 def recorded(self,g):
  identity=self.identity()
  with g.capture_client() as receipt:receipt.record_identity(identity);name=receipt.name
  return name,identity
 def proof(self,identity):return dict(identity=identity,frontend_absent=True,backend_absent=True,media_absent=True)
 def test_recorded_capture_recovery(self):
  root,h,before,g=self.fixture();name,identity=self.recorded(g)
  g.reconcile_capture(name,self.proof)
  with g.acquire():pass
  self.assertEqual(f.f.state(root),before)
 def test_identity_drift_and_partial_cleanup_refused(self):
  root,h,before,g=self.fixture();name,identity=self.recorded(g)
  for key in identity:
   changed=dict(identity);changed[key]=43 if key in ('node','pipewire_cookie') else 'changed'
   with self.assertRaises(m.a.Refused):g.reconcile_capture(name,lambda original:self.proof(changed))
  for key in ('frontend_absent','backend_absent','media_absent'):
   for value in (False,None,1):
    proof=self.proof(identity);proof[key]=value
    with self.assertRaises(m.a.Refused):g.reconcile_capture(name,lambda original:proof)
  self.assertTrue((root/name).exists())
 def test_unrecorded_identity_and_bad_path_refused(self):
  root,h,before,g=self.fixture()
  with g.capture_client() as receipt:name=receipt.name
  for path in (name,'../escape',m.CAPTURE_PREFIX+'draft-'+'a'*32):
   with self.assertRaises(m.a.Refused):g.reconcile_capture(path,self.proof)
  self.assertTrue((root/name).exists())
 def test_recording_is_one_time_and_validated(self):
  root,h,before,g=self.fixture()
  with g.capture_client() as receipt:
   with self.assertRaises(m.a.Refused):receipt.record_identity({})
   receipt.record_identity(self.identity())
   with self.assertRaises(m.a.Refused):receipt.record_identity(self.identity())
 def test_recovery_probe_timeout_retains_record(self):
  root,h,before,g=self.fixture();name,identity=self.recorded(g)
  def timeout(identity):raise TimeoutError('deadline')
  with self.assertRaises(TimeoutError):g.reconcile_capture(name,timeout)
  self.assertTrue((root/name).exists())
 def test_capture_recovery_crash_is_repeatable(self):
  root,h,before,g=self.fixture();name,identity=self.recorded(g)
  code='m.checkpoint=lambda label: os._exit(94) if label=="capture-reconciled-before-clear" else None\ng.reconcile_capture('+repr(name)+',lambda identity:dict(identity=identity,frontend_absent=True,backend_absent=True,media_absent=True))\n'
  p=self.child(root,code);out,err=p.communicate(timeout=3);self.assertEqual(p.returncode,94,err)
  self.assertTrue((root/name).exists());g.reconcile_capture(name,self.proof)
  with g.acquire():pass
  print('capture recovery exits verified 1',flush=True)
 def test_identity_recording_crash_boundaries(self):
  for label in ('capture-draft-created','capture-draft-synced','capture-draft-renamed','capture-identity-durable'):
   root,h,before,g=self.fixture()
   code='m.checkpoint=lambda label: os._exit(96) if label=='+repr(label)+' else None\nwith g.capture_client() as receipt: receipt.record_identity('+repr(self.identity())+')\n'
   p=self.child(root,code);out,err=p.communicate(timeout=4);self.assertEqual(p.returncode,96,err)
   self.assertTrue(list(root.glob(m.CAPTURE_PREFIX+'*')))
   with self.assertRaises(m.a.Refused):
    with g.acquire():pass
   self.assertEqual(f.f.state(root),before)
  print('identity recording exits verified 4',flush=True)
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
