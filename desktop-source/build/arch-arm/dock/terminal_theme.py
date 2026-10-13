"""Generate dock-managed foot colours without replacing a user's custom config."""
import re,subprocess
from pathlib import Path
MARKER='# Managed by Omarchy S terminal palette\n'
def render(palette):
 def color(key):
  value=palette[key]
  if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError('Invalid colour: '+key)
  return value[1:]
 regular=('background','red','green','yellow','blue','magenta','cyan','foreground')
 bright=('dark_foreground','bright_red','bright_green','bright_yellow','bright_blue','bright_magenta','bright_cyan','bright_foreground')
 mode=palette.get('mode','dark')
 if mode not in ('dark','light'):raise ValueError('Invalid palette mode')
 text=MARKER+'font=JetBrainsMono Nerd Font:size=11\ndpi-aware=no\npad=8x8\ninitial-color-theme='+mode+'\n\n[colors-'+mode+']\n'
 text+='background='+color('background')+'\nforeground='+color('foreground')+'\n'
 for prefix,keys in (('regular',regular),('bright',bright)):
  for index,key in enumerate(keys):text+=prefix+str(index)+'='+color(key)+'\n'
 return text

def apply(palette,home):
 target=Path(home)/'.config/foot/foot.ini'
 if target.is_symlink() or (target.exists() and not target.read_text().startswith(MARKER)):
  return {'updated':False,'reason':'custom configuration preserved'}
 value=render(palette);target.parent.mkdir(parents=True,exist_ok=True)
 temporary=target.with_name('.foot.ini.palette')
 try:
  temporary.write_text(value);temporary.chmod(0o600)
  subprocess.run(['foot','--check-config','--config',str(temporary)],check=True,capture_output=True,text=True,timeout=5)
  temporary.replace(target)
 finally:temporary.unlink(missing_ok=True)
 return {'updated':True,'applies_to':'new terminals'}
