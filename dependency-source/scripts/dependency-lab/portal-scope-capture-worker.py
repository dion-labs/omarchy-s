#!/usr/bin/env python3
"""Disposable real-capture worker; deliberately leaves unresolved evidence on exit."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent

def load(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 if len(sys.argv)!=2 or sys.argv[1] not in ('crash','hold'):raise ValueError('Expected crash or hold')
 frontend=load('frontend','test-portal-frontend.py');scope=load('scope','portal-scope.py')
 frontend.Frontend.setUpClass();test=frontend.Frontend();test.setUp()
 root=Path('/tmp/root-path').read_text();gate=scope.f.Fence(root)
 with gate.capture_client() as receipt:
  session=test.create();node=test.start(session);frames=test.capture(session,node)
  # Deliberately omit identity recording, exercising whole-scope recovery.
  proof={'frames':frames,'receipt':receipt.name,'mode':sys.argv[1],'pid':os.getpid()}
  path=Path('/tmp/capture-proof');draft=path.with_suffix('.tmp')
  with draft.open('w') as stream:json.dump(proof,stream);stream.flush();os.fsync(stream.fileno())
  os.replace(draft,path)
  if sys.argv[1]=='crash':os._exit(97)
  # Host destroys this registered disposable container while capture is active.
  time.sleep(45)
  raise TimeoutError('Host did not interrupt the capture')

if __name__=='__main__':main()
