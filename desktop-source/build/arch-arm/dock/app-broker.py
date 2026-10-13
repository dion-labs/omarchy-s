#!/usr/bin/env python3
"""Unprivileged host-side browser launcher for the private desktop's Wayland socket."""
import json,os,pwd,signal,socket,struct,subprocess,sys,time,runpy
from pathlib import Path
from app_protocol import receive
from app_process import stop_groups,command_for,early_exit_failed
assert os.geteuid()==1000
r=Path(sys.argv[1]);assert r.parent==Path('/var/tmp') and r.name.startswith('hyprland-headless-dock-')
endpoint=r/'run/app-launch.sock';endpoint.unlink(missing_ok=True)
server=socket.socket(socket.AF_UNIX);server.bind(str(endpoint));endpoint.chmod(0o600);server.listen(3);server.settimeout(1)
children=[]
def stop(*_):raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
try:
 while True:
  try:conn,_=server.accept()
  except socket.timeout:continue
  with conn:
   conn.settimeout(2)
   try:
    _,uid,_=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
    assert uid==1000
    url=receive(conn)
    assert Path('/run/omarchy-dock-session').read_text().strip()==str(r)
    ready=json.loads((r/'ready.json').read_text());assert ready['ready']
    displays=[x for x in (r/'run').glob('wayland-*') if x.is_socket() and x.name!='wayland-dock'];assert len(displays)==1
    env=os.environ.copy();env.update(HOME='/home/omarchy/Dock',XDG_CONFIG_HOME='/home/omarchy/Dock/.config',XDG_CACHE_HOME='/home/omarchy/Dock/.cache',XDG_RUNTIME_DIR=str(r/'run'),WAYLAND_DISPLAY=str(displays[0]),GSK_RENDERER='cairo',XDG_SESSION_TYPE='wayland')
    identity=pwd.getpwuid(os.geteuid())
    env['PULSE_SERVER']='unix:/run/user/1000/pulse/native'
    env.update(USER=identity.pw_name,LOGNAME=identity.pw_name,SHELL=identity.pw_shell or '/bin/sh')
    for key in tuple(env):
     if key.startswith('SUDO_'):env.pop(key)
    power=isinstance(url,tuple) and url[0]=='power'
    if not power and url!='terminal':runpy.run_path(str(Path(__file__).with_name('browser-profile.py')))['recover']('/home/omarchy/Dock/.config/chromium')
    # Explicit separate browser profile; no phone account/profile access or copy.
    with open(r/'browser.log','a') as log:
     child=subprocess.Popen((['dbus-run-session','--',sys.executable,str(Path(__file__).with_name('power-menu.py')),str(r),url[1]] if power else command_for(url)),env=env,cwd='/home/omarchy/Projects' if url=='terminal' else '/home/omarchy/Dock',stdout=log,stderr=log,start_new_session=True)
    children[:]=[p for p in children if p.poll() is None];children.append(child)
    conn.sendall(b'error: application exited' if early_exit_failed(child) else b'ok')
   except Exception:
    try:conn.sendall(b'error: launch unavailable')
    except OSError:pass
finally:
 server.close();endpoint.unlink(missing_ok=True)
 stop_groups(children)
