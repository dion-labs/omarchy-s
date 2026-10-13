#!/usr/bin/env python3
"""Enable the Wi-Fi panel and verify current state without modifying connectivity."""
import json,os,subprocess,time
from pathlib import Path
assert os.geteuid()==1000 and os.environ['HOME']=='/trial/home'
output=Path('/trial/network-check.json');output.write_text('{"pending":true}\n')
base=['quickshell','ipc','-p','/trial/omarchy-shell/shell','call']
result={}
try:
 deadline=time.monotonic()+8
 while True:
  enabled=subprocess.check_output(base+['shell','enablePlugin','omarchy.network','{"section":"right","before":"omarchy.tray"}'],text=True,timeout=5).strip()
  if enabled=='ok':break
  if enabled not in ('unknown','not ready') or time.monotonic()>deadline:raise RuntimeError(enabled)
  time.sleep(.2)
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  try:status=json.loads(subprocess.check_output(base+['omarchy.network','portStatus'],text=True,stderr=subprocess.DEVNULL,timeout=3))
  except (subprocess.SubprocessError,ValueError):status={}
  if status.get('connected') and status.get('wifi_present'):break
  time.sleep(.2)
 assert status.get('network_manager') and status.get('wifi_present') and status.get('wifi_enabled') and status.get('connected'),status
 state=subprocess.check_output(['nmcli','-t','-f','STATE','general'],text=True,timeout=5).strip();assert state=='connected'
 blocked=subprocess.run(['busctl','--system','get-property','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','Version'],capture_output=True,text=True,timeout=5)
 assert blocked.returncode!=0
 result={'pending':False,'status':status,'systemd_access_blocked':True,'network_modified':False}
except Exception as error:result={'pending':False,'error':str(error)}
finally:output.write_text(json.dumps(result)+'\n')
assert 'error' not in result,result
