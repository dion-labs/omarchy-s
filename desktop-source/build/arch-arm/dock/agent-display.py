#!/usr/bin/env python3
"""Explicit, idle-only graphical app handoff. Default is read-only planning."""
import argparse,fcntl,json,os,signal,subprocess,time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from continuity_state import main_agents,describe

def processes():
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   if (p/'comm').read_text().strip()!='ChatGPT':continue
   stat=(p/'stat').read_text().split(') ',1)[1].split()
   if stat[0]=='Z':continue
   if p.stat().st_uid!=1000:raise RuntimeError('Unexpected application owner')
   result.append((int(stat[19]),int(p.name)))
  except (FileNotFoundError,ProcessLookupError):pass
 return sorted(result)

def target_env(target):
 phosh=subprocess.check_output(['pgrep','-x','phosh'],text=True).split()
 if len(phosh)!=1:raise RuntimeError('Expected one handset session')
 source=dict(x.split('=',1) for x in (Path('/proc')/phosh[0]/'environ').read_text().split('\0') if '=' in x)
 env={k:source[k] for k in ('DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR')}
 env.update(HOME='/home/omarchy',XDG_CONFIG_HOME='/home/omarchy/.config',XDG_CACHE_HOME='/home/omarchy/.cache',XDG_SESSION_TYPE='wayland',GDK_BACKEND='wayland',GSK_RENDERER='cairo')
 socket=Path(env['XDG_RUNTIME_DIR'])/'wayland-0'
 if target=='desktop':
  r=Path(Path('/run/omarchy-dock-session').read_text().strip())
  if r.parent!=Path('/var/tmp') or not r.name.startswith('hyprland-headless-dock-'):raise RuntimeError('Unexpected desktop path')
  compositors=subprocess.check_output(['pgrep','-x','Hyprland'],text=True).split()
  if len(compositors)!=1:raise RuntimeError('Expected one external compositor')
  inside=Path('/proc')/compositors[0]/'root/trial'
  actual=r.stat();live=inside.stat()
  if (actual.st_dev,actual.st_ino)!=(live.st_dev,live.st_ino):raise RuntimeError('Stale desktop session pointer')
  if json.loads(Path('/run/omarchy-dock.json').read_text())['event']!='running':raise RuntimeError('Dock not running')
  if not json.loads((r/'ready.json').read_text())['ready']:raise RuntimeError('Desktop not ready')
  candidates=[x for x in (r/'run').glob('wayland-*') if x.is_socket() and x.name!='wayland-dock']
  if len(candidates)!=1:raise RuntimeError('Ambiguous desktop socket')
  socket=candidates[0]
 if not socket.is_socket() or socket.stat().st_uid!=1000:raise RuntimeError('Display socket unavailable')
 env['WAYLAND_DISPLAY']=str(socket)
 return env

def launch_app(env):
 logpath=Path('/home/omarchy/.local/state/omarchy-agent-display.log');logpath.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(logpath,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600);os.fchown(fd,1000,1000)
 with os.fdopen(fd,'a') as log:
  process=subprocess.Popen(['runuser','-u','omarchy','--','env']+[k+'='+v for k,v in env.items()]+['/usr/local/bin/chatgpt-phone'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 return process.pid

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('target',choices=['phone','desktop','status']);p.add_argument('--apply',action='store_true');p.add_argument('--expect-pid',type=int);p.add_argument('--expect-start',type=int);p.add_argument('--confirm-idle',action='store_true');a=p.parse_args()
 if os.geteuid()!=0:raise SystemExit('Run through sudo')
 if a.target=='status':
  phone_env=target_env('phone');phone=phone_env['WAYLAND_DISPLAY']
  try:desktop_env=target_env('desktop');desktop=desktop_env['WAYLAND_DISPLAY']
  except (OSError,RuntimeError,ValueError,subprocess.SubprocessError):desktop_env=None;desktop=None
  agents=main_agents()
  # Some running Electron processes expose empty cmdline/environ. Verify actual
  # toplevel presence instead of guessing location from stale handoff records.
  if len(agents)==1 and agents[0]['display'].startswith('/missing/'):
   def visible(env):
    if env is None:return False
    return subprocess.run(['runuser','-u','omarchy','--','env']+[k+'='+v for k,v in env.items()]+['/usr/local/lib/omarchy-phone/wlrctl','window','find','app_id:chatgpt'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2).returncode==0
   locations=[path for env,path in ((phone_env,phone),(desktop_env,desktop)) if visible(env)]
   if len(locations)==1:agents[0]['display']=locations[0]
   elif not locations:
    try:
     observation=json.loads(Path('/run/omarchy-agent-recovery.json').read_text())
     if observation.get('agent_identity')==[agents[0]['start'],agents[0]['pid']] and observation.get('event') in ('waiting_for_exit','needs_attention'):
      agents[0]['display']=observation['display']
    except (OSError,ValueError,KeyError):pass
  print(json.dumps(describe(agents,phone,desktop)));return
 env=target_env(a.target);agents=main_agents()
 if len(agents)!=1:raise RuntimeError('Expected exactly one normal agent; no application was stopped')
 main_pid=agents[0]['pid'];main_start=agents[0]['start']
 plan={'target':a.target,'current_pid':main_pid,'current_start':main_start,'display':env['WAYLAND_DISPLAY'],'profile':'existing phone profile; no copies','requires_idle_app':True,'applied':False}
 if not a.apply:print(json.dumps(plan));return
 if not a.confirm_idle:raise RuntimeError('Confirm the agent is idle and drafts are saved before moving')
 if a.expect_start!=main_start:raise RuntimeError('Agent identity changed; inspect again')
 if a.expect_pid is None or main_pid!=a.expect_pid:raise RuntimeError('App changed; inspect plan again')
 # Only one explicit transition can run at a time; never force-kill a stuck app.
 with open('/run/omarchy-agent-display.lock','w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  current=main_agents()
  if len(current)!=1 or (current[0]['pid'],current[0]['start'])!=(a.expect_pid,a.expect_start):raise RuntimeError('App changed before handoff')
  env=target_env(a.target) # Recheck after taking the transition lock.
  if len(main_agents(include_isolated=True))!=1:raise RuntimeError('Another agent instance is open; close the disposable instance first')
  os.kill(main_pid,signal.SIGTERM)
  end=time.monotonic()+20
  while processes():
   if time.monotonic()>end:raise RuntimeError('App did not exit cleanly; no second instance started')
   time.sleep(.25)
  # The cable may disappear while waiting for the idle app to exit.
  try:env=target_env(a.target)
  except (OSError,RuntimeError,subprocess.SubprocessError):
   if a.target!='desktop':raise
   env=target_env('phone')
   plan.update(target='phone',fallback_reason='desktop unavailable after clean app exit')
  plan['display']=env['WAYLAND_DISPLAY']
  # Preserve the original user's home, keyring bus and browser sandbox wrapper.
  launcher_pid=launch_app(env)
  plan.update(applied=True,launcher_pid=launcher_pid)
  Path('/run/omarchy-agent-display.json').write_text(json.dumps(plan)+'\n')
  if plan['target']=='desktop':
   with open('/run/omarchy-agent-recovery.log','a') as log:
    subprocess.Popen(['python3','/usr/local/lib/omarchy-dock/agent-recovery.py','--display',env['WAYLAND_DISPLAY'],'--launcher-pid',str(launcher_pid)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
  print(json.dumps(plan))
if __name__=='__main__':main()
