#!/usr/bin/env python3
"""Recover an exited dock app onto the phone; never terminate an application."""
import argparse,fcntl,json,os,runpy,subprocess,time
from pathlib import Path
from continuity_state import owned_cohort

def decide(display_alive, original_alive, any_app_alive, saw_app, lost_display):
 if not saw_app:return 'waiting_for_app'
 if display_alive and not lost_display:return 'watching' if original_alive else 'closed_by_user'
 if original_alive:return 'waiting_for_exit'
 if any_app_alive:return 'replaced'
 return 'recover'

def watch(display,launcher_pid,helper,status,lock_path,result_path,exit_timeout=30,launch_timeout=40,poll_interval=.5):
 display=Path(display);status=Path(status)
 def publish(event,**extra):
  tmp=status.with_suffix('.tmp');tmp.write_text(json.dumps({'event':event,'display':str(display),'uptime':time.monotonic(),'agent_identity':identity,**extra})+'\n');tmp.replace(status)
 saw=False;lost=False;started=time.monotonic();deadline=None;identity=None;cohort=set()
 while True:
  apps=helper['processes']();original=False;parents={}
  for start,pid in apps:
   try:
    parent=int((Path('/proc')/str(pid)/'stat').read_text().split(') ',1)[1].split()[1])
    parents[pid]=parent
    if identity is None and parent==launcher_pid:identity=(start,pid)
    if (start,pid)==identity:original=True;saw=True
   except OSError:pass
  cohort=owned_cohort(apps,parents,identity,cohort)
  original=any(item in cohort for item in apps)
  try:alive=helper['target_env']('desktop')['WAYLAND_DISPLAY']==str(display)
  except (OSError,RuntimeError,ValueError,subprocess.SubprocessError):alive=False
  if not alive:
   lost=True
   if deadline is None:deadline=time.monotonic()+exit_timeout
  action=decide(alive,original,bool(apps),saw,lost)
  publish(action)
  if action in ('closed_by_user','replaced'):return
  if action=='waiting_for_app' and time.monotonic()-started>launch_timeout:
   publish('launch_not_observed');return
  if action=='waiting_for_exit' and deadline and time.monotonic()>deadline:
   publish('needs_attention',reason='Application remains alive; refused to terminate it');return
  if action=='recover':
   with open(lock_path,'a') as lock:
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:time.sleep(poll_interval);continue
    if helper['processes']():publish('replaced');return
    env=helper['target_env']('phone')
    pid=helper['launch_app'](env)
    Path(result_path).write_text(json.dumps({'target':'phone','display':env['WAYLAND_DISPLAY'],'applied':True,'launcher_pid':pid,'recovered_from':str(display)})+'\n')
    publish('recovered',launcher_pid=pid)
    return
  time.sleep(poll_interval)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--display',required=True);p.add_argument('--launcher-pid',type=int,required=True);a=p.parse_args()
 assert os.geteuid()==0
 display=Path(a.display)
 assert display.parent.parent.parent==Path('/var/tmp') and display.parent.parent.name.startswith('hyprland-headless-dock-')
 helper=runpy.run_path('/usr/local/lib/omarchy-dock/agent-display.py')
 watch(display,a.launcher_pid,helper,Path('/run/omarchy-agent-recovery.json'),'/run/omarchy-agent-display.lock','/run/omarchy-agent-display.json')
if __name__=='__main__':main()
