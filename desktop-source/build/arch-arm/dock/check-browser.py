#!/usr/bin/env python3
"""Open one public diagnostic page via the dock's default browser handler."""
import json,os,subprocess,time
from pathlib import Path
assert os.geteuid()==1000 and os.environ['HOME']=='/trial/home'
result={'pending':True};output=Path('/trial/browser-check.json')
output.write_text(json.dumps(result))
try:
 before=json.loads(subprocess.check_output(['hyprctl','-j','clients'],text=True,timeout=3))
 assert not any(w.get('class')=='chromium' for w in before),'Browser is already in use'
 url='https://example.com/?omarchy-s=native19'
 subprocess.run(['xdg-open',url],check=True,timeout=10)
 for _ in range(80):
  windows=json.loads(subprocess.check_output(['hyprctl','-j','clients'],text=True,timeout=3))
  browsers=[w for w in windows if w.get('class')=='chromium']
  if any('Example Domain' in w.get('title','') for w in browsers):break
  time.sleep(.25)
 result={'pending':False,'browser_mapped':bool(browsers),'expected_page_loaded':any('Example Domain' in w.get('title','') for w in browsers)}
except Exception as error:result={'pending':False,'error':str(error)}
finally:output.write_text(json.dumps(result)+'\n')
