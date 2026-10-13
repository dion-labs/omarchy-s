#!/usr/bin/env python3
"""USB-owner child: private desktop namespace, retained files, reversible input lease."""
import json,os,secrets,shutil,signal,subprocess,sys,time
from pathlib import Path
assert os.geteuid()==0
source=Path('/usr/local/lib/omarchy-dock')
card=sys.argv[1]
launch_id=sys.argv[2] if len(sys.argv)>2 else secrets.token_hex(16)
assert len(launch_id)==32 and all(c in '0123456789abcdef' for c in launch_id)
assert card in ('card0','card1','card2')
assert 's9p-frame-lab.' in str((Path('/sys/class/drm')/card).resolve())
remote=Path('/var/tmp')/('hyprland-headless-dock-'+str(time.time_ns()))
remote.mkdir(mode=0o700);(remote/'run').mkdir(mode=0o700)
for name in ('gpu_environment.py','power_actions.py','screenshot.py','app_protocol.py','theme-set.py','terminal_theme.py','app-launch.py','input-seat.so','desktop-environment.py','gtk_theme.py','portal_backend.py','shell-menu.py','launchpad.py','input-hotplug.py','input-access.py','desktop-session.py','allowed-inputs.json'):shutil.copy2(source/name,remote/name)
for name in ('profile','lib','omarchy-shell'):shutil.copytree(source/name,remote/name)
home=Path('/home/omarchy/Dock');home.mkdir(mode=0o700,exist_ok=True);os.chown(home,1000,1000)
fonts=home/'.local/share/fonts';fonts.mkdir(parents=True,exist_ok=True)
font=fonts/'omarchy.ttf'
if not font.exists():shutil.copy2(source/'omarchy-shell/fonts/omarchy.ttf',font)
for directory in (home/'.local',home/'.local/share',fonts,font):os.chown(directory,1000,1000)
projects=Path('/home/omarchy/Projects')
assert projects.is_dir() and not projects.is_symlink(), 'Expected existing phone project directory'
for p in [remote,*remote.rglob('*')]:os.chown(p,1000,1000)
node=Path('/dev/dri')/card;os.chown(node,1000,1000);os.chmod(node,0o600)
(remote/'launch.json').write_text(json.dumps({'launch_id':launch_id,'pid':os.getpid()})+'\n')
pointer=Path('/run/omarchy-dock-session')
pointer.with_suffix('.tmp').write_text(str(remote)+'\n')
pointer.with_suffix('.tmp').replace(pointer)
cmd=['timeout','-k','5','0','bwrap','--tmpfs','/','--ro-bind','/usr','/usr','--ro-bind','/etc','/etc','--ro-bind','/opt','/opt','--ro-bind','/sys','/sys','--ro-bind','/var/lib','/var/lib','--symlink','usr/bin','/bin','--symlink','usr/bin','/sbin','--symlink','usr/lib','/lib','--symlink','usr/lib','/lib64','--dir','/var/tmp','--chmod','755','/var','--chmod','1777','/var/tmp','--dev','/dev','--tmpfs','/dev/shm','--chmod','1777','/dev/shm','--dir','/dev/dri','--dev-bind','/dev/dri/renderD128','/dev/dri/renderD128','--dev-bind',str(node),str(node),'--proc','/proc','--tmpfs','/run','--dir','/run/dbus','--ro-bind',str(remote/'run'),'/run/dbus','--tmpfs','/tmp','--chmod','1777','/tmp','--tmpfs','/home','--chmod','755','/home','--dir','/home/omarchy','--chmod','755','/home/omarchy','--tmpfs','/root','--bind',str(remote),'/trial','--bind',str(home),'/trial/home','--bind',str(projects),str(projects),'--unshare-pid','--die-with-parent','--','/usr/sbin/runuser','-u','omarchy','--','env','HOME=/trial/home','XDG_RUNTIME_DIR=/trial/run','XDG_CONFIG_HOME=/trial/home/.config','XDG_CACHE_HOME=/trial/home/.cache','S9P_DOCK_SESSION=1','S9P_EXTERNAL_DRM='+card,'S9P_OMARCHY_PROFILE=/trial/profile','dbus-run-session','--','python3','/trial/desktop-session.py']
# Opt-in driver is scoped to the private desktop and its session bus.
if Path('/etc/omarchy-desktop-private-mesa').is_file():
 from gpu_environment import configure
 gpu_env=configure({},enabled=True)
 for key,value in gpu_env.items():cmd.insert(cmd.index('dbus-run-session'),key+'='+value)

# Shared application audio; private PipeWire still owns desktop screencasts.
pulse=Path('/run/user/1000/pulse')
if pulse.is_dir() and not pulse.is_symlink() and pulse.stat().st_uid==1000:
 cmd[cmd.index('--tmpfs',cmd.index('/run/dbus')+1):cmd.index('--tmpfs',cmd.index('/run/dbus')+1)]=['--ro-bind',str(pulse),'/run/host-pulse']
 cmd.insert(cmd.index('dbus-run-session'),'PULSE_SERVER=unix:/run/host-pulse/native')

process=None;broker=None;network=None
def stop(*_):raise SystemExit(0)
for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(sig,stop)
try:
 with open(remote/'network-proxy.log','a') as log:
  network=subprocess.Popen(['setpriv','--reuid=1000','--regid=1000','--init-groups','--','python3',str(source/'network-proxy.py'),str(remote)],stdout=log,stderr=log)
 for _ in range(60):
  if network.poll() is not None:raise RuntimeError('Network proxy exited')
  status=remote/'network-proxy.json'
  if status.exists() and json.loads(status.read_text()).get('ready') and (remote/'run/network-bus').is_socket():break
  time.sleep(.1)
 else:raise RuntimeError('Network proxy readiness timeout')
 with open(remote/'app-broker.log','a') as log:
  broker=subprocess.Popen(['setpriv','--reuid=1000','--regid=1000','--init-groups','--','python3',str(source/'app-broker.py'),str(remote)],stdout=log,stderr=log)
 process=subprocess.Popen(['python3',str(remote/'input-access.py'),str(remote)]+cmd)
 raise SystemExit(process.wait())
finally:
 if broker and broker.poll() is None:
  broker.terminate()
  try:broker.wait(timeout=3)
  except subprocess.TimeoutExpired:broker.kill();broker.wait()
 if process and process.poll() is None:
  process.terminate()
  try:process.wait(timeout=4)
  except subprocess.TimeoutExpired:process.kill();process.wait()
 if network and network.poll() is None:
  network.terminate()
  try:network.wait(timeout=1)
  except subprocess.TimeoutExpired:network.kill();network.wait()
