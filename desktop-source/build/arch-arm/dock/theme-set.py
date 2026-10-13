#!/usr/bin/env python3
"""Apply a shipped Omarchy palette to this dock's shell, borders and GTK preference."""
import base64,json,os,re,subprocess,sys,tomllib
from pathlib import Path
from terminal_theme import apply as apply_terminal_theme
from gtk_theme import apply as apply_gtk_theme
assert os.geteuid()==1000 and os.environ['HOME']=='/trial/home'
name=sys.argv[1];assert name in ('tokyo-night','catppuccin','gruvbox','catppuccin-latte')
source=Path('/trial/omarchy-shell/themes')/name/'colors.toml'
palette=tomllib.loads(source.read_text())
for key in ('accent','background','muted'):assert re.fullmatch(r'#[0-9a-fA-F]{6}',palette[key])
terminal=apply_terminal_theme(palette,Path.home())
gtk=apply_gtk_theme(palette,Path.home())
current=Path.home()/'.local/state/omarchy/current';theme=current/'theme';theme.mkdir(parents=True,exist_ok=True)
tmp=theme/'colors.toml.tmp';tmp.write_bytes(source.read_bytes());tmp.replace(theme/'colors.toml')
(current/'theme.name').write_text(name+'\n')
background=source.with_name('background.webp')
if background.is_file():
 link=current/'background';temporary=current/'background.new'
 temporary.unlink(missing_ok=True);temporary.symlink_to(background);temporary.replace(link)
 subprocess.run(['quickshell','ipc','-p','/trial/omarchy-shell/shell','call','background','setInstant',str(background)],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
config=Path.home()/'.config/omarchy-s';config.mkdir(parents=True,exist_ok=True)
active='rgba('+palette['accent'][1:]+'ff)';inactive='rgba('+palette['muted'][1:]+'aa)'
(config/'theme.lua').write_text('hl.config({ general = { col = { active_border = { colors = { '+json.dumps(active)+' } }, inactive_border = '+json.dumps(inactive)+' } } })\n')
subprocess.run(['quickshell','ipc','-p','/trial/omarchy-shell/shell','call','shell','applyTheme',base64.b64encode(source.read_bytes()).decode(),''],check=True,timeout=5,stdout=subprocess.DEVNULL)
subprocess.run(['gsettings','set','org.gnome.desktop.interface','color-scheme','prefer-light' if palette.get('mode')=='light' else 'prefer-dark'],check=True,timeout=5)
subprocess.run(['hyprctl','reload','config-only'],check=True,timeout=5)
print(json.dumps({'theme':name,'terminal':terminal,'gtk':gtk}))
