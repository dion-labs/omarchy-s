#!/usr/bin/env python3
"""Opt-in host Docker namespace retirement test; creates/removes only owned fixtures."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[2]

def command(*args):return subprocess.check_output(['docker',*args],text=True,timeout=30).strip()

@unittest.skipUnless(os.environ.get('OMARCHY_SCOPE_IMAGE'),'Explicit host lab image required')
class HostScope(unittest.TestCase):
 def test_destroyed_container_scope_proof(self):
  image=os.environ['OMARCHY_SCOPE_IMAGE'];token=secrets.token_hex(16);volume='omarchy-scope-test-'+token;container=None
  engine=command('info','--format','{{.ID}}');command('volume','create',volume)
  def helper(code):
   return command('run','--rm','--network','none','--cap-drop','ALL','-v',volume+':/tmp','-v',str(ROOT)+':/src:ro',image,'python3','-c',code)
  prefix="import importlib.util,json;from pathlib import Path;s=importlib.util.spec_from_file_location('scope','/src/scripts/dependency-lab/portal-scope.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
  try:
   container=command('run','-d','--network','none','--cap-drop','ALL','--label','omarchy.scope='+token,image,'sleep','120')
   info=json.loads(command('inspect',container))[0];self.assertEqual(info['Config']['Labels']['omarchy.scope'],token);self.assertTrue(info['State']['Running'])
   identity=dict(engine_id=engine,container_id=container,scope_token=token)
   helper(prefix+'root=m.f.tx.initialize();Path("/tmp/root-path").write_text(str(root));g=m.f.Fence(root);m.bind(g,'+repr(identity)+');\nwith g.capture_client():pass\n')
   code=prefix+'g=m.f.Fence(Path("/tmp/root-path").read_text());\ntry:m.retire(g,lambda value:dict(identity=value,destroyed=False))\nexcept m.f.a.Refused:print("refused-live")\nelse:raise AssertionError("live scope cleared")\n'
   self.assertEqual(helper(code),'refused-live')
   command('rm','-f',container)
   # Exact ID absence from successful engine enumeration, never a transport error.
   self.assertNotIn(container,command('ps','-aq','--no-trunc').splitlines());self.assertEqual(command('info','--format','{{.ID}}'),engine)
   self.assertEqual(helper(prefix+'g=m.f.Fence(Path("/tmp/root-path").read_text());print(m.retire(g,lambda value:dict(identity='+repr(identity)+',destroyed=True)))'),'1')
   self.assertEqual(command('info','--format','{{.ID}}'),engine)
  finally:
   if container:subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
   command('volume','rm',volume)
 def test_real_capture_crash_and_namespace_destruction(self):
  image=os.environ['OMARCHY_SCOPE_IMAGE'];stage=Path(os.environ['OMARCHY_SCOPE_STAGE']).resolve()
  self.assertTrue((stage/'usr/local/lib/omarchy-dock/portal-wlr').is_file())
  for mode in ('crash','hold'):
   with self.subTest(mode=mode):
    token=secrets.token_hex(16);volume='omarchy-capture-test-'+token;container=None;worker=None
    engine=command('info','--format','{{.ID}}');command('volume','create',volume)
    def helper(code):return command('run','--rm','--network','none','--cap-drop','ALL','-v',volume+':/tmp','-v',str(ROOT)+':/src:ro',image,'python3','-c',code)
    prefix="import importlib.util,json;from pathlib import Path;s=importlib.util.spec_from_file_location('scope','/src/scripts/dependency-lab/portal-scope.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
    try:
     container=command('create','--network','none','--cap-drop','ALL','--label','omarchy.scope='+token,
       '-v',volume+':/tmp','-v',str(ROOT)+':/src:ro','-v',str(stage)+':/stage:ro',
       '-e','OMARCHY_FRONTEND_LAB=1','-e','OMARCHY_PORTAL_LAB_BINARY=/stage/usr/local/lib/omarchy-dock/portal-wlr',image,'sleep','120')
     info=json.loads(command('inspect',container))[0];self.assertEqual(info['Config']['Labels']['omarchy.scope'],token)
     identity=dict(engine_id=engine,container_id=container,scope_token=token)
     helper(prefix+'root=m.f.tx.initialize();Path("/tmp/root-path").write_text(str(root));m.bind(m.f.Fence(root),'+repr(identity)+')')
     command('start',container)
     worker=subprocess.Popen(['docker','exec',container,'python3','/src/scripts/dependency-lab/portal-scope-capture-worker.py',mode],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
     wait="import time,json;from pathlib import Path;p=Path('/tmp/capture-proof');end=time.monotonic()+20\nwhile not p.exists() and time.monotonic()<end:time.sleep(.05)\nprint(p.read_text())"
     proof=json.loads(helper(wait));self.assertEqual(proof['mode'],mode)
     self.assertEqual(len(proof['frames']),3);self.assertGreater(len({f['color'] for f in proof['frames']}),1)
     self.assertTrue(all(f['bytes']==1280*720*4 for f in proof['frames']))
     if mode=='crash':
      out,err=worker.communicate(timeout=5);self.assertEqual(worker.returncode,97,err)
     else:self.assertIsNone(worker.poll())
     # Container remains live after app death, or while capture still holds its lock.
     self.assertTrue(json.loads(command('inspect',container))[0]['State']['Running'])
     code=prefix+'g=m.f.Fence(Path("/tmp/root-path").read_text(),timeout=.05)\ntry:m.retire(g,lambda value:dict(identity=value,destroyed=False))\nexcept RuntimeError:print("refused-live")\nelse:raise AssertionError("live capture scope cleared")'
     self.assertEqual(helper(code),'refused-live')
     self.assertEqual(helper('from pathlib import Path;root=Path(Path("/tmp/root-path").read_text());print((root/'+repr(proof['receipt'])+').exists())'),'True')
     command('rm','-f',container)
     if mode=='hold':
      out,err=worker.communicate(timeout=5);self.assertNotEqual(worker.returncode,0)
     self.assertNotIn(container,command('ps','-aq','--no-trunc').splitlines());self.assertEqual(command('info','--format','{{.ID}}'),engine)
     self.assertEqual(helper(prefix+'g=m.f.Fence(Path("/tmp/root-path").read_text());print(m.retire(g,lambda value:dict(identity='+repr(identity)+',destroyed=True)))'),'1')
     self.assertEqual(helper(prefix+'g=m.f.Fence(Path("/tmp/root-path").read_text())\ntry:\n with g.acquire():pass\nexcept RuntimeError:print("retired")\nelse:raise AssertionError("retired scope reused")'),'retired')
     self.assertEqual(command('info','--format','{{.ID}}'),engine)
     print('real capture interruption verified',mode,flush=True)
    finally:
     if container:subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
     if worker and worker.poll() is None:worker.kill();worker.communicate(timeout=5)
     command('volume','rm',volume)
if __name__=='__main__':unittest.main()
