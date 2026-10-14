#!/usr/bin/env python3
"""Admission refusal and payload-preservation tests on private fixtures."""
import importlib.util
from pathlib import Path
import shutil
import sys
import unittest

HERE=Path(__file__).resolve().parent
def module(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=module('admission','portal-admission.py');f=module('fixtures','test-portal-lifecycle.py')

def idle():
 return dict(fenced=True,complete=True,responsive=True,token='lease',epoch='generation',observed_at=10.0,
             frontend_sessions=[],backend_sessions=[],requests=[],media_nodes=[],unknown_clients=[])

class Lease:
 token='lease';epoch='generation'
 def __init__(self):self.value=idle();self.released=False;self.error=None
 def acquire(self):return self
 def __enter__(self):return self
 def __exit__(self,*args):self.released=True
 def observe(self):
  if self.error:raise self.error
  return dict(self.value)

class Admission(unittest.TestCase):
 def check(self,**changes):
  value=idle();value.update(changes);return m.require_idle(value,'lease','generation',10.0)
 def test_empty_fenced_inventory(self):self.assertTrue(self.check())
 def test_each_active_or_unresolved_category(self):
  for field in ('frontend_sessions','backend_sessions','requests','media_nodes','unknown_clients'):
   with self.subTest(field=field),self.assertRaises(m.Refused):self.check(**{field:['pending']})
 def test_missing_and_malformed_inventory(self):
  for field in idle():
   value=idle();del value[field]
   with self.subTest(field=field),self.assertRaises(m.Refused):m.require_idle(value,'lease','generation',10.)
  for value in (None,{},[],False):
   with self.assertRaises(m.Refused):m.require_idle(value,'lease','generation',10.)
 def test_tracked_only_and_unresponsive_refused(self):
  for field in ('fenced','complete','responsive'):
   for value in (False,None,1,'yes'):
    with self.assertRaises(m.Refused):self.check(**{field:value})
 def test_identity_and_time_drift(self):
  for change in ({'token':'replacement'},{'epoch':'new'},{'observed_at':8.9},{'observed_at':11.},{'observed_at':float('nan')},{'observed_at':float('inf')},{'observed_at':True}):
   with self.assertRaises(m.Refused):self.check(**change)
 def test_invalid_empty_collections(self):
  for value in (None,{},(),False,0,''):
   with self.assertRaises(m.Refused):self.check(requests=value)

@unittest.skipUnless(sys.platform=='linux','Linux transaction metadata required')
class Integration(unittest.TestCase):
 def fixture(self):
  root=f.tx.initialize();stage=f.f.make_stage();self.addCleanup(shutil.rmtree,root,True);self.addCleanup(shutil.rmtree,stage,True)
  f.f.seed(root);hooks=f.FakeService(root);before=f.f.state(root);f.tx.prepare(root,stage)
  return root,hooks,before,Lease()
 def run_update(self,root,hooks,lease,**kw):return m.run(root,hooks,lease,clock=lambda:10.,**kw)
 def test_refusal_preserves_payload_and_does_not_stop(self):
  for field in ('frontend_sessions','backend_sessions','requests','media_nodes','unknown_clients'):
   root,hooks,before,lease=self.fixture();lease.value[field]=['unresolved']
   with self.assertRaises(m.Refused):self.run_update(root,hooks,lease)
   self.assertEqual(f.f.state(root),before);self.assertEqual(hooks.load()['events'],[]);self.assertTrue(lease.released)
 def test_probe_timeout_releases_without_mutation(self):
  root,hooks,before,lease=self.fixture();lease.error=TimeoutError('probe deadline')
  with self.assertRaises(m.Refused):self.run_update(root,hooks,lease)
  self.assertTrue(lease.released);self.assertEqual(f.f.state(root),before);self.assertEqual(hooks.load()['events'],[])
 def test_race_after_stop_refuses_before_payload_write(self):
  root,hooks,before,lease=self.fixture();stop=hooks.quiesce
  def raced():
   result=stop();lease.value['requests']=['late'];return result
  hooks.quiesce=raced
  with self.assertRaises(m.Refused):self.run_update(root,hooks,lease)
  self.assertEqual(f.f.state(root),before);self.assertTrue(lease.released)
  # Explicit reconciliation and fresh fence are required for recovery.
  hooks.quiesce=stop;fresh=Lease();self.run_update(root,hooks,fresh,recover=True)
  self.assertEqual(f.f.state(root),before);self.assertTrue(fresh.released)
 def test_success_and_recovery_require_new_inventory(self):
  root,hooks,before,lease=self.fixture();self.run_update(root,hooks,lease);updated=f.f.state(root)
  fresh=Lease();fresh.value['complete']=False
  with self.assertRaises(m.Refused):self.run_update(root,hooks,fresh,recover=True)
  self.assertEqual(f.f.state(root),updated);self.assertTrue(fresh.released)
  self.run_update(root,hooks,Lease(),recover=True);self.assertEqual(f.f.state(root),before)
 def test_fence_loss_during_stop_refused(self):
  root,hooks,before,lease=self.fixture();stop=hooks.quiesce
  def lost():
   result=stop();lease.value['epoch']='replacement';return result
  hooks.quiesce=lost
  with self.assertRaises(m.Refused):self.run_update(root,hooks,lease)
  self.assertEqual(f.f.state(root),before);self.assertTrue(lease.released)
 def test_hook_failure_releases_fence(self):
  root,hooks,before,lease=self.fixture();hooks.fail='quiesce-raise'
  with self.assertRaises(RuntimeError):self.run_update(root,hooks,lease)
  self.assertTrue(lease.released);self.assertEqual(f.f.state(root),before)

if __name__=='__main__':unittest.main()
