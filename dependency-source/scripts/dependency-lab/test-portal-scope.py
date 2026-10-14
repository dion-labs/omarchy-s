#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
def load(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('scope','portal-scope.py');base=load('fixtures','test-portal-fence.py')
@unittest.skipUnless(sys.platform=='linux','Private Linux roots required')
class Scope(unittest.TestCase):
 fixture=base.Fences.fixture
 child=base.Fences.child
 def value(self):return dict(engine_id='test-engine',container_id='a'*64,scope_token='b'*32)
 def proof(self,value):return dict(identity=value,destroyed=True)
 def setup_scope(self):
  root,h,before,g=self.fixture();m.bind(g,self.value())
  with g.capture_client():pass
  (root/(m.f.CAPTURE_PREFIX+'draft-'+'c'*32)).write_bytes(b'partial');(root/(m.f.CAPTURE_PREFIX+'draft-'+'c'*32)).chmod(0o600)
  return root,g
 def test_bind_must_precede_capture(self):
  root,h,before,g=self.fixture()
  with g.capture_client():pass
  with self.assertRaises(m.f.a.Refused):m.bind(g,self.value())
 def test_unproven_or_changed_scope_retains_evidence(self):
  root,g=self.setup_scope();names=list(root.glob(m.f.CAPTURE_PREFIX+'*'))
  for proof in ({'identity':self.value(),'destroyed':False},{'identity':self.value(),'destroyed':1},{'identity':{},'destroyed':True}):
   with self.assertRaises(m.f.a.Refused):m.retire(g,lambda value:proof)
   self.assertTrue(all(p.exists() for p in names))
 def test_terminal_retirement_removes_only_capture_artifacts(self):
  root,g=self.setup_scope();self.assertEqual(m.retire(g,self.proof),2);self.assertEqual(m.retire(g,self.proof),0)
  self.assertTrue((root/m.SCOPE).exists());self.assertTrue((root/m.f.RETIRED).exists())
  (root/m.f.DIRTY).write_bytes(b'pending');(root/m.f.DIRTY).chmod(0o600)
  with self.assertRaisesRegex(RuntimeError,'Private scope retired'):g.reconcile(base.f.FakeService(root))
  with self.assertRaises(RuntimeError):
   with g.capture_client():pass
  with self.assertRaises(RuntimeError):
   with g.acquire():pass
 def test_unsafe_artifact_refused(self):
  root,g=self.setup_scope();p=root/(m.f.CAPTURE_PREFIX+'d'*32);p.symlink_to('/dev/null')
  with self.assertRaises(OSError):m.retire(g,self.proof)
  self.assertTrue(p.is_symlink())
 def test_retirement_crashes_are_repeatable(self):
  for label in ('scope-before-clear','scope-cleared-one'):
   root,g=self.setup_scope();code='scope=load("scope",'+repr(str(HERE/'portal-scope.py'))+')\nscope.checkpoint=lambda label: os._exit(95) if label=='+repr(label)+' else None\nscope.retire(g,lambda value:dict(identity=value,destroyed=True))\n'
   p=self.child(root,code);out,err=p.communicate(timeout=4);self.assertEqual(p.returncode,95,err)
   m.retire(g,self.proof);self.assertFalse(list(root.glob(m.f.CAPTURE_PREFIX+'*')))
  print('scope retirement exits verified 2',flush=True)
if __name__=='__main__':unittest.main()
