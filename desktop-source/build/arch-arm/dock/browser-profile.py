#!/usr/bin/env python3
"""Recover only orphaned Chromium singleton symlinks in the local dock profile."""
import os,time
from pathlib import Path

def recover(profile):
 profile=Path(profile)
 locks=[profile/name for name in ('SingletonLock','SingletonCookie','SingletonSocket')]
 for p in locks:
  if p.exists() and not p.is_symlink():raise RuntimeError('Unexpected regular singleton file; preserve it')
 if not any(p.is_symlink() for p in locks):return False
 # Chromium command lines must remain readable: uncertainty means no repair.
 for proc in Path('/proc').glob('[0-9]*'):
  try:
   if proc.stat().st_uid!=os.getuid():continue
   args=(proc/'cmdline').read_bytes().replace(b'\0',b' ').split()
  except FileNotFoundError:continue
  if ('--user-data-dir='+str(profile)).encode() in args:return False
 lock=profile/'SingletonLock'
 if lock.is_symlink():
  name=os.readlink(lock)
  try:pid=int(name.rsplit('-',1)[1])
  except (ValueError,IndexError):raise RuntimeError('Unrecognized singleton lock')
  if Path('/proc',str(pid)).exists():raise RuntimeError('Old lock PID still exists; preserve it')
 backup=profile/('.omarchy-orphaned-locks-'+str(time.time_ns()));backup.mkdir(mode=0o700)
 for p in locks:
  if p.is_symlink():p.rename(backup/p.name)
 return True

if __name__=='__main__':
 assert os.geteuid()==1000
 print('orphaned_locks_recovered='+str(recover('/home/omarchy/Dock/.config/chromium')))
