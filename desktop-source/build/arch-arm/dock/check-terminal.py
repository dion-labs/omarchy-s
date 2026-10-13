#!/usr/bin/env python3
"""Open Terminal through the actual dock broker; leave it available to the user."""
import json,os,subprocess,time
from pathlib import Path
assert os.geteuid()==1000 and os.environ['HOME']=='/trial/home'
output=Path('/trial/terminal-check.json');output.write_text('{"pending":true}\n')
result={}
try:
 before=json.loads(subprocess.check_output(['hyprctl','clients','-j'],text=True,timeout=3))
 assert not any(w.get('class')=='omarchy-s-terminal' for w in before),'Terminal already in use'
 subprocess.run(['python3','/trial/app-launch.py','terminal'],check=True,timeout=8)
 for _ in range(60):
  clients=json.loads(subprocess.check_output(['hyprctl','clients','-j'],text=True,timeout=3))
  terminal=[w for w in clients if w.get('class')=='omarchy-s-terminal']
  if terminal:break
  time.sleep(.2)
 result={'pending':False,'terminal_mapped':bool(terminal)}
except Exception as error:result={'pending':False,'error':str(error)}
finally:output.write_text(json.dumps(result)+'\n')
