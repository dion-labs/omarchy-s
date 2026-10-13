"""Bounded cleanup for applications started in their own process sessions."""
import os,signal,time

def stop_groups(children,timeout=2):
 groups=[]
 for child in children:
  if child.poll() is not None:continue
  try:group=os.getpgid(child.pid)
  except ProcessLookupError:child.wait(timeout=.5);continue
  if group!=child.pid or group==os.getpgrp():raise RuntimeError('Unexpected application process group')
  groups.append((child,group))
 for child,group in groups:
  try:os.killpg(group,signal.SIGTERM)
  except ProcessLookupError:pass
 # Do not reap leaders until cleanup: retaining their PIDs prevents group-ID reuse.
 # One grace period covers all applications, not one delay per child.
 deadline=time.monotonic()+timeout
 while groups and time.monotonic()<deadline:time.sleep(min(.05,max(0,deadline-time.monotonic())))
 for child,group in groups:
  try:os.killpg(group,signal.SIGKILL)
  except ProcessLookupError:pass
  child.wait(timeout=.5)

def stop_group(child,timeout=2):
 stop_groups([child],timeout)


def command_for(request):
 if request=='terminal':
  return ['dbus-run-session','--','/usr/bin/foot','--app-id=omarchy-s-terminal','--title=Terminal']
 from app_protocol import browser_url
 return ['dbus-run-session','--','/usr/local/bin/chromium-phone','--user-data-dir=/home/omarchy/Dock/.config/chromium','--no-first-run','--',browser_url(request)]


def early_exit_failed(child, timeout=.35):
 """Nonzero immediate exit is failure; zero may be normal single-instance reuse.

 A surviving process means dispatch only, not a mapped or responsive window.
 """
 import subprocess
 try:return child.wait(timeout=timeout)!=0
 except subprocess.TimeoutExpired:return False
