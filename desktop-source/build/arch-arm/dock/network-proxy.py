#!/usr/bin/env python3
"""Expose only the existing NetworkManager and BlueZ services to one external desktop."""
import fcntl,json,os,signal,socket,subprocess,sys,time
from pathlib import Path
assert os.geteuid()==1000
r=Path(sys.argv[1]);assert r.parent==Path('/var/tmp') and r.name.startswith('hyprland-headless-dock-')
assert Path('/run/omarchy-dock-session').read_text().strip()==str(r)
lock=open(r/'run/network-proxy.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
owner=json.loads((r/'launch.json').read_text());process_path=Path('/proc')/str(owner['pid'])
def identity():
 fields=(process_path/'stat').read_text().rsplit(')',1)[1].split()
 if fields[0]=='Z':raise RuntimeError('Launcher exited')
 return fields[19]
start=identity();endpoint=r/'run/network-bus'
if endpoint.exists():
 assert endpoint.is_socket();endpoint.unlink()
parent,child=socket.socketpair();parent.settimeout(5)
process=None
status=r/'network-proxy.json'
def stop(*_):raise SystemExit(0)
for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(sig,stop)
try:
 process=subprocess.Popen(['xdg-dbus-proxy','--fd='+str(child.fileno()),'unix:path=/run/dbus/system_bus_socket',str(endpoint),'--filter','--talk=org.freedesktop.NetworkManager','--talk=org.bluez'],pass_fds=(child.fileno(),))
 child.close();assert parent.recv(1),'Proxy exited before ready';assert endpoint.is_socket();endpoint.chmod(0o600)
 alias=r/'run/system_bus_socket'
 if alias.is_symlink():assert os.readlink(alias)=='network-bus'
 else:
  assert not alias.exists();alias.symlink_to('network-bus')
 status.write_text(json.dumps({'ready':True,'pid':os.getpid(),'allowed_services':['org.freedesktop.NetworkManager','org.bluez']})+'\n')
 while process.poll() is None:
  try:
   if identity()!=start or Path('/run/omarchy-dock-session').read_text().strip()!=str(r) or (r/'stopped.json').exists():break
  except (OSError,RuntimeError):break
  time.sleep(.25)
finally:
 parent.close();child.close()
 if process and process.poll() is None:
  try:process.wait(timeout=1)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=1)
 endpoint.unlink(missing_ok=True)
 status.write_text('{"ready":false}\n')
