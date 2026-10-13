#!/usr/bin/env python3
"""Open the adapted Omarchy menu, with the GTK launchpad as a recovery path."""
import os,subprocess
try:
 r=subprocess.run(['quickshell','ipc','-p','/trial/omarchy-shell/shell','call','shell','toggle','omarchy.menu','{"menu":"root"}'],capture_output=True,text=True,timeout=3)
 if r.returncode==0 and not any(x in r.stdout for x in ('not found','Not ready','Too few','Too many')):raise SystemExit(0)
except (OSError,subprocess.TimeoutExpired):pass
os.execvp('python3',['python3','/trial/launchpad.py'])
