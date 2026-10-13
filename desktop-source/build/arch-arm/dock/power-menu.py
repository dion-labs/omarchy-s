#!/usr/bin/env python3
"""Confirm a fixed native action from the host-side desktop broker."""
import json,os,subprocess,sys
from pathlib import Path
from power_actions import ACTIONS,command

def validate(runtime):
 assert os.geteuid()==1000
 assert runtime.parent==Path('/var/tmp') and runtime.name.startswith('hyprland-headless-dock-')
 assert Path('/run/omarchy-dock-session').read_text().strip()==str(runtime)
 assert not (runtime/'stopped.json').exists()
 assert json.loads((runtime/'ready.json').read_text())['ready'] is True
 assert Path('/proc/1/comm').read_text().strip()=='systemd'
 assert Path('/proc/device-tree/model').read_text().strip('\0')=='Samsung Galaxy S9+ (SM-G965F)'

if __name__=='__main__':
 runtime=Path(sys.argv[1]);action=sys.argv[2];planned=command(action);validate(runtime)
 from power_dialog import Gtk,create_dialog
 app=Gtk.Application(application_id='ai.dionlabs.omarchy.PowerMenu')
 def execute():
  validate(runtime)
  if action=='logout':
   pending=runtime/'logout-request.tmp';pending.write_text(json.dumps({'action':'logout'})+'\n');pending.replace(runtime/'logout-request.json')
  else:subprocess.run(planned,check=True,timeout=15)
 def activate(app):create_dialog(app,action,execute).present()
 app.connect('activate',activate);app.run([])
