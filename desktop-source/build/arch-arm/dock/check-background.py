#!/usr/bin/env python3
"""Exercise pinned static palettes and restore the user's selected theme/workspace."""
import json,os,subprocess,time
from pathlib import Path
assert os.geteuid()==1000 and os.environ['HOME']=='/trial/home'
base=['quickshell','ipc','-p','/trial/omarchy-shell/shell','call']
def ipc(*args):return subprocess.check_output(base+list(args),text=True,timeout=5).strip()
output=Path('/trial/background-check.json');output.write_text('{"pending":true}\n')
selected=Path.home()/'.local/state/omarchy/current/theme.name'
original=selected.read_text().strip() if selected.exists() else 'tokyo-night'
assert original in ('tokyo-night','catppuccin','gruvbox','catppuccin-latte')
result={};errors=[]
try:
 assert ipc('shell','enablePlugin','omarchy.background','{}')=='ok'
 for name in ('tokyo-night','catppuccin','gruvbox','catppuccin-latte'):
  subprocess.run(['python3','/trial/theme-set.py',name],check=True,capture_output=True,text=True,timeout=20)
  expected='/trial/omarchy-shell/themes/'+name+'/background.webp'
  deadline=time.monotonic()+8;status={}
  while time.monotonic()<deadline:
   try:status=json.loads(ipc('background','status'))
   except (subprocess.SubprocessError,ValueError):status={}
   if status.get('ready') and status.get('path')==expected:break
   time.sleep(.1)
  assert status.get('ready') and status.get('path')==expected,status
  result[name]=status
except Exception as error:errors.append(str(error))
finally:
 try:subprocess.run(['python3','/trial/theme-set.py',original],check=True,capture_output=True,text=True,timeout=20)
 except Exception as error:errors.append('Restore: '+str(error))
 output.write_text(json.dumps({'pending':False,'palettes':result,'restored_theme':original if not errors else None,'errors':errors})+'\n')
assert len(result)==4 and not errors,errors
