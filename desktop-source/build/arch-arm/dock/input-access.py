#!/usr/bin/env python3
"""Bounded input ACL lease around the existing private desktop namespace."""
import json,os,re,signal,subprocess,sys,time,importlib.util
from pathlib import Path
remote=Path(sys.argv[1]);cmd=sys.argv[2:]
assert os.geteuid()==0 and remote.parent==Path('/var/tmp') and remote.name.startswith('hyprland-headless-')
assert cmd[:3]==['timeout','-k','5'] and cmd[4]=='bwrap'
assert cmd[3]=='180' or (cmd[3]=='0' and remote.name.startswith('hyprland-headless-dock-') and 'S9P_DOCK_SESSION=1' in cmd)
allowed=json.loads((remote/'allowed-inputs.json').read_text())
assert len(allowed)==2 and all(re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',x) for x in allowed)
lease=[];process=None;guard=None;bindings=[]
(remote/'input').mkdir(mode=0o700,exist_ok=True);os.chown(remote/'input',1000,1000)
def cleanup_signal(*_):raise KeyboardInterrupt
for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(sig,cleanup_signal)
try:
 found=set()
 for event in sorted(Path('/sys/class/input').glob('event*')):
  device=event/'device';uniq=(device/'uniq').read_text().strip().lower()
  if uniq not in allowed:continue
  assert (device/'id/bustype').read_text().strip()=='0005'
  node=Path('/dev/input')/event.name
  acl=subprocess.check_output(['getfacl','-p',str(node)],text=True)
  lease.append((node,node.stat().st_ino,acl,uniq))
  bindings.append(dict(target=event.name,uniq=uniq,name=(device/"name").read_text().strip()))
  subprocess.run(['setfacl','-m','u:1000:r',str(node)],check=True)
  cmd[cmd.index('--unshare-pid'):cmd.index('--unshare-pid')]=['--dev-bind',str(node),'/trial/input/'+event.name]
  found.add(uniq)
 if cmd[3]=='0':
  spec=importlib.util.spec_from_file_location('input_hotplug',remote/'input-hotplug.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  pending=module.pending_bindings(allowed,bindings)
  for binding in pending:
   (remote/'input'/binding['target']).touch(mode=0o600)
  bindings.extend(pending)
 else:
  assert found==set(allowed),'Both approved Bluetooth devices must be connected for the bounded input test' 
 cmd.insert(cmd.index('dbus-run-session'),'S9P_INPUT_UNIQS=,'+','.join(allowed)+',')
 process=subprocess.Popen(cmd,start_new_session=True)
 if cmd[3]=='0':
  guard=module.InputHotplug(os.getpid(),remote,bindings)
 while process.poll() is None:
  if guard:guard.refresh()
  time.sleep(1)
 status=process.returncode
finally:
 if process and process.poll() is None:
  os.killpg(process.pid,signal.SIGTERM)
  try:process.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
 if guard:guard.close()
 restored=0
 for node,inode,acl,uniq in lease:
  try:
   current=Path('/sys/class/input')/node.name/'device/uniq'
   if node.stat().st_ino==inode and current.read_text().strip().lower()==uniq:
    subprocess.run(['setfacl','-P','--restore=-'],input=acl,text=True,check=True);restored+=1
  except FileNotFoundError:pass
 (remote/'input-lease.json').write_text(json.dumps({'leased_nodes':len(lease),'restored_nodes':restored,'keystrokes_logged':False})+'\n')
raise SystemExit(status)
