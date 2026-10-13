"""Process identity and display status; no application content or task inspection."""
from pathlib import Path
import os

def main_agents(proc=Path('/proc'),uid=1000,include_isolated=False):
 result=[];all_pids=set()
 for p in proc.iterdir():
  if not p.name.isdigit():continue
  try:
   if p.stat().st_uid!=uid or (p/'comm').read_text().strip()!='ChatGPT':continue
   stat=(p/'stat').read_text().rsplit(')',1)[1].split()
   if stat[0]=='Z':continue
   all_pids.add(int(p.name))
   args=(p/'cmdline').read_bytes().split(b'\0')
   if any(a.startswith(b'--type=') for a in args):continue
   # Explicit isolated profiles do not own the normal phone account.
   if not include_isolated and any(a.startswith(b'--user-data-dir') for a in args):continue
   values={}
   for item in (p/'environ').read_bytes().split(b'\0'):
    key,sep,value=item.partition(b'=')
    if sep and key in (b'WAYLAND_DISPLAY',b'XDG_RUNTIME_DIR'):values[key.decode()]=os.fsdecode(value)
   display=Path(values.get('WAYLAND_DISPLAY','wayland-0'))
   if not display.is_absolute():display=Path(values.get('XDG_RUNTIME_DIR','/missing'))/display
   result.append({'pid':int(p.name),'start':int(stat[19]),'display':str(display),'parent':int(stat[1])})
  except (OSError,ValueError,IndexError):continue
 return sorted([a for a in result if a['parent'] not in all_pids],key=lambda a:a['start'])

def owned_cohort(apps,parents,identity,known):
 """Track descendants while parent links exist; retain their exact identities after reparenting."""
 current=set(apps);owned=current & set(known)
 if identity in current:owned.add(identity)
 changed=True
 while changed:
  changed=False;pids={pid for _,pid in owned}
  for item in current-owned:
   if parents.get(item[1]) in pids:owned.add(item);changed=True
 return owned

def describe(agents,phone,desktop):
 state={'desktop_available':bool(desktop),'task_state':'unknown','agent':None,'location':'stopped','can_move':False}
 if len(agents)>1:state['location']='ambiguous';return state
 if not agents:return state
 agent=agents[0];state['agent']=agent
 if agent['display']==phone:state['location']='phone'
 elif desktop and agent['display']==desktop:state['location']='desktop'
 elif agent['display'].startswith('/var/tmp/hyprland-headless-dock-'):state['location']='disconnected'
 else:state['location']='unknown'
 state['can_move']=state['location'] in ('phone','desktop','disconnected')
 return state
