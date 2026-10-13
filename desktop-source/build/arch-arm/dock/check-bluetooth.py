#!/usr/bin/env python3
"""Read adapter and paired-device counts without pairing or changing connections."""
import json,os,subprocess,time
from pathlib import Path
assert os.geteuid()==1000 and os.environ['HOME']=='/trial/home'
output=Path('/trial/bluetooth-check.json');output.write_text('{"pending":true}\n')
base=['quickshell','ipc','-p','/trial/omarchy-shell/shell','call'];result={}
try:
 deadline=time.monotonic()+8
 while True:
  enabled=subprocess.check_output(base+['shell','enablePlugin','omarchy.bluetooth','{"section":"right","before":"omarchy.network"}'],text=True,timeout=5).strip()
  if enabled=='ok':break
  if enabled not in ('unknown','not ready') or time.monotonic()>deadline:raise RuntimeError(enabled)
  time.sleep(.2)
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  try:status=json.loads(subprocess.check_output(base+['omarchy.bluetooth','portStatus'],text=True,stderr=subprocess.DEVNULL,timeout=3))
  except (subprocess.SubprocessError,ValueError):status={}
  if status.get('adapter_present') and status.get('paired_count',0)>=2:break
  time.sleep(.2)
 assert status.get('adapter_present') and status.get('enabled') and status.get('paired_count',0)>=2,status
 result={'pending':False,'status':status,'pairing_or_connection_changes':False}
except Exception as error:result={'pending':False,'error':str(error)}
finally:output.write_text(json.dumps(result)+'\n')
assert 'error' not in result,result
