#!/usr/bin/env python3
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
s=importlib.util.spec_from_file_location('verifier',Path(__file__).with_name('verify-acceptance.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Evidence(unittest.TestCase):
 def fixture(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);base=Path(tmp.name);root=base/'source';root.mkdir();e=base/'evidence';e.mkdir();stage=base/'stage';binary=stage/'usr/local/lib/omarchy-dock/portal-wlr';binary.parent.mkdir(parents=True);binary.write_bytes(b'fixture-binary')
  pin=patch.object(m.runner,'PIN',m.runner.sha(binary.read_bytes()));pin.start();self.addCleanup(pin.stop)
  lock=root/'packaging/portal-frontend-lab.lock.json';lock.parent.mkdir();lock.write_text('{}');lock.chmod(0o644)
  manifest=base/'manifest.json';manifest.write_text(json.dumps({'files':[{'path':str(lock.relative_to(root)),'sha256':m.runner.sha(lock.read_bytes()),'mode':'0644'}]}))
  builder=base/'builder.json';build=dict(image_id='sha256:'+'a'*64,lock_sha256=m.runner.sha(lock.read_bytes()));builder.write_text(json.dumps(build))
  r=dict(schema=2,run_id='b'*32,status='passed',phone_contacted=False,production_updater_enabled=False,elapsed_seconds=1.,source_files=1,manifest_sha256=m.runner.sha(manifest.read_bytes()),cases=[],logs={},case_artifacts={})
  r['runtime']=dict(image_id=build['image_id'],builder_receipt_sha256=m.runner.sha(builder.read_bytes()),frontend_lock_sha256=build['lock_sha256'],portal_sha256=m.runner.PIN)
  for name in ('linux.log','host.log'):(e/name).write_text('test output');r['logs'][name]=m.runner.sha((e/name).read_bytes())
  cases=[(n,c,'linux') for n,c in m.runner.CASES]+[(*m.runner.HOST,'host')]
  for i,(name,count,platform) in enumerate(cases):
   value=dict(tests=count,errors=0,failures=0,skips=0,expected_failures=0,unexpected_successes=0);p=e/('case-'+str(i)+'.json');p.write_text(json.dumps(value));r['case_artifacts'][p.name]=m.runner.sha(p.read_bytes());r['cases'].append(dict(file=name,platform=platform,**value))
  r.update(tests=sum(c for _,c,_ in cases),linux_tests=sum(c for _,c in m.runner.CASES),host_tests=m.runner.HOST[1])
  return root,e,manifest,builder,stage,r
 def check(self,f):
  root,e,manifest,builder,stage,r=f;(e/'acceptance.json').write_text(json.dumps(r));return m.verify(root,e,manifest,m.runner.sha(manifest.read_bytes()),builder,stage,m.runner.sha((e/'acceptance.json').read_bytes()))
 def test_valid_and_comparison_ignores_logs_duration(self):
  f=self.fixture();first=self.check(f);f[-1]['run_id']='c'*32;f[-1]['elapsed_seconds']=2.;(f[1]/'linux.log').write_text('different diagnostics');f[-1]['logs']['linux.log']=m.runner.sha((f[1]/'linux.log').read_bytes());second=self.check(f)
  self.assertTrue(m.compare(first,second)['equivalent'])
 def test_wrong_receipt_hash(self):
  f=self.fixture();self.check(f);root,e,manifest,builder,stage,r=f
  with self.assertRaises(ValueError):m.verify(root,e,manifest,r['manifest_sha256'],builder,stage,'0'*64)
 def test_log_tamper_extra_and_symlink(self):
  for mode in ('tamper','extra','link'):
   f=self.fixture();e=f[1]
   if mode=='tamper':(e/'linux.log').write_text('changed')
   elif mode=='extra':(e/'extra').write_text('unexpected')
   else:(e/'linux.log').unlink();(e/'linux.log').symlink_to(e/'host.log')
   with self.assertRaises(ValueError):self.check(f)
 def test_case_forgery_and_summary_disagreement(self):
  f=self.fixture();p=f[1]/'case-0.json';value=json.loads(p.read_text());value['skips']=1;p.write_text(json.dumps(value));f[-1]['case_artifacts'][p.name]=m.runner.sha(p.read_bytes())
  with self.assertRaises(ValueError):self.check(f)
  f=self.fixture();f[-1]['cases'][0]['tests']+=1
  with self.assertRaises(ValueError):self.check(f)
 def test_status_schema_and_json_duplicates(self):
  for change in ({'status':'running'},{'schema':True},{'cleanup_error':'failure'},{'phone_contacted':True},{'tests':True}):
   f=self.fixture();f[-1].update(change)
   with self.assertRaises(ValueError):self.check(f)
  with self.assertRaises(ValueError):m.parse(b'{"status":"failed","status":"passed"}')
  with self.assertRaises(ValueError):m.parse(b'{"elapsed":NaN}')
 def test_source_and_runtime_drift(self):
  f=self.fixture();(f[0]/'extra').write_text('changed')
  with self.assertRaises(ValueError):self.check(f)
  f=self.fixture();(f[4]/'usr/local/lib/omarchy-dock/portal-wlr').write_bytes(b'changed')
  with self.assertRaises(ValueError):self.check(f)
 def test_same_run_and_different_contract(self):
  first=self.check(self.fixture());second=copy.deepcopy(first)
  with self.assertRaises(ValueError):m.compare(first,second)
  second.update(receipt_sha256='f'*64,run_id='d'*32);second['runtime']['image_id']='sha256:'+'e'*64
  self.assertEqual(m.compare(first,second)['differences'],['runtime'])
 def test_legacy_shape_and_missing_artifacts(self):
  f=self.fixture();f[-1]['schema']=1;del f[-1]['run_id'];self.assertIsNone(self.check(f)['run_id'])
  f=self.fixture();del f[-1]['case_artifacts']['case-0.json']
  with self.assertRaises(ValueError):self.check(f)
if __name__=='__main__':unittest.main()
