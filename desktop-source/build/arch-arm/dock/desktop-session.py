#!/usr/bin/env python3
"""External desktop inside the private namespace. No handset session access."""
import json,os,signal,subprocess,time
from pathlib import Path
from gpu_environment import configure,verify
assert os.geteuid()==1000 and os.environ['XDG_RUNTIME_DIR']=='/trial/run'
assert not Path('/dev/input').exists()
card=os.environ['S9P_EXTERNAL_DRM']
assert 's9p-frame-lab.' in str((Path('/sys/class/drm')/card).resolve())
assert [p.name for p in Path('/dev/dri').glob('card*')]==[card]
children=[]
def stop(*_):raise SystemExit(0)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,stop)
env=os.environ.copy();env.update(WAYLAND_DISPLAY='wayland-dock',LIBSEAT_BACKEND='noop',MESA_LOADER_DRIVER_OVERRIDE='kmsro',PAN_MESA_DEBUG='noafbc',HYPRLAND_NO_SD_VARS='1',HYPRLAND_NO_SD_NOTIFY='1',HYPRLAND_NO_CRASHREPORTER='1')
Path('/trial/home').mkdir(exist_ok=True)
Path('/trial/weston.ini').write_text('[core]\ngbm-format=xrgb8888\nrequire-input=false\n')
try:
 with open('/trial/session.log','a') as log:
  weston=subprocess.Popen(['weston','-B','drm','--renderer=gl','--drm-device='+card,'--seat=seat-dock','--continue-without-input','--shell=kiosk-shell.so','--config=/trial/weston.ini','--modules=/trial/input-seat.so','--socket=wayland-dock','--logger-scopes=log','--log=/trial/weston.log'],env=env,stdout=log,stderr=log);children.append(weston)
  for _ in range(60):
   if weston.poll() is not None:raise RuntimeError('Weston exited')
   if Path('/trial/run/wayland-dock').exists():break
   time.sleep(.1)
  else:raise RuntimeError('Weston socket timeout')
  hypr_env=configure(env,aquamarine=True)
  hypr_env.update(LIBSEAT_BACKEND='seatd',SEATD_SOCK='/nonexistent')
  hypr_env.pop('MESA_LOADER_DRIVER_OVERRIDE',None)
  hypr=subprocess.Popen(['Hyprland','-c','/trial/profile/hyprland.lua'],env=hypr_env,stdout=log,stderr=log);children.append(hypr)
  for _ in range(60):
   if hypr.poll() is not None:raise RuntimeError('Hyprland exited')
   probe=subprocess.run(['hyprctl','instances','-j'],env=env,capture_output=True,text=True,timeout=3)
   try:instances=json.loads(probe.stdout)
   except ValueError:instances=[]
   if len(instances)==1 and instances[0].get('wl_socket'):break
   time.sleep(.25)
  else:raise RuntimeError('Hyprland socket timeout')
  if env.get('OMARCHY_PANFROST_CPU_INVALIDATE')=='1':
   Path('/trial/gpu-runtime.json').write_text(json.dumps({'weston':verify(weston.pid),'hyprland':verify(hypr.pid)})+'\n')
  env.update(XDG_CURRENT_DESKTOP='Hyprland',XDG_SESSION_TYPE='wayland',WAYLAND_DISPLAY=instances[0]['wl_socket'],HYPRLAND_INSTANCE_SIGNATURE=instances[0]['instance'],GSK_RENDERER='cairo')
  for _ in range(40):
   monitor=json.loads(subprocess.check_output(['hyprctl','monitors','-j'],env=env,text=True,timeout=3))
   if len(monitor)==1 and (monitor[0]['width'],monitor[0]['height'])==(1920,1080):break
   time.sleep(.25)
  else:raise RuntimeError('External mode did not become ready')
  errors=subprocess.check_output(['hyprctl','configerrors'],env=env,text=True,timeout=3)
  assert not errors.strip(),errors
  try:subprocess.run(['python3','/trial/desktop-environment.py'],env=env,stdout=log,stderr=log,timeout=25)
  except subprocess.TimeoutExpired:log.write('Desktop portal setup timed out; continuing with application fallback.\n');log.flush()
  shell_env=env.copy()
  shell_env.update(OMARCHY_PATH='/trial/omarchy-shell',QT_QUICK_BACKEND='software',QSG_RENDER_LOOP='basic',QS_DISABLE_FILE_WATCHER='1',PATH='/trial/omarchy-shell/bin:'+env['PATH'])
  shell_log=open('/trial/omarchy-shell.log','a')
  try:
   shell_process=subprocess.Popen(['quickshell','-n','-p','/trial/omarchy-shell/shell'],env=shell_env,stdout=shell_log,stderr=shell_log)
   children.append(shell_process)
  except OSError as error:log.write('Omarchy shell unavailable; GTK launcher remains available: '+str(error)+'\n');log.flush()
  shell_ready=False
  for _ in range(25):
   probe=subprocess.run(['quickshell','ipc','-p','/trial/omarchy-shell/shell','call','shell','ping'],env=shell_env,capture_output=True,text=True,timeout=3)
   if probe.returncode==0 and probe.stdout.strip()=='ok':shell_ready=True;break
   time.sleep(.2)
  if shell_ready:
   selected=Path('/trial/home/.local/state/omarchy/current/theme.name')
   name=selected.read_text().strip() if selected.exists() else 'tokyo-night'
   if name not in ('tokyo-night','catppuccin','gruvbox','catppuccin-latte'):name='tokyo-night'
   try:subprocess.run(['python3','/trial/theme-set.py',name],env=shell_env,stdout=log,stderr=log,check=True,timeout=20)
   except (subprocess.SubprocessError,OSError) as error:log.write('Theme setup failed: '+str(error)+'\n');log.flush()
  # These documents persist across dock sessions. Never overwrite user edits.
  welcome=Path('/trial/home/Desktop.txt')
  if not welcome.exists():welcome.write_text('Omarchy S external desktop\n\nThis desktop is separate from the phone screen.\nYour dock files are kept between sessions.\nItalian keyboard layout is selected.\n\nAutomatic docking is under development.\n')
  children.append(subprocess.Popen(['gnome-text-editor','--standalone',str(welcome)],env=env,stdout=log,stderr=log))
  children.append(subprocess.Popen(['nautilus','--new-window','/trial/home'],env=env,stdout=log,stderr=log))
  Path('/trial/ready.json').write_text(json.dumps({'ready':True,'resolution':[1920,1080],'weston_pid':weston.pid,'hyprland_pid':hypr.pid,'input_protocol_logging':False,'shell_ready':shell_ready})+'\n')
  while True:
   if weston.poll() is not None or hypr.poll() is not None:raise RuntimeError('Desktop compositor exited')
   for name in ('big','little','gpu'):
    sensor=Path('/sys/module/s9p_cpufreq/parameters/temp_'+name)
    if sensor.exists() and int(sensor.read_text())>=70:raise RuntimeError('Desktop temperature limit')
   time.sleep(1)
finally:
 for process in reversed(children):
  if process.poll() is None:
   process.terminate()
   try:process.wait(timeout=2)
   except subprocess.TimeoutExpired:process.kill();process.wait()
 Path('/trial/stopped.json').write_text('{"stopped":true}\n')
