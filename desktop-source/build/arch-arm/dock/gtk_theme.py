"""Dock-local GTK3 and GPicView palette; preserve unrelated settings."""
import configparser,re
from pathlib import Path
MARKER='/* Managed by Omarchy S GTK palette */\n'
def apply(palette,home):
 home=Path(home);config=home/'.config'
 def color(key):
  value=palette[key]
  if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError(key)
  return value
 bg,fg,accent,muted,base=[color(k) for k in ('background','foreground','accent','muted','dark_background')]
 light=palette.get('mode')=='light'
 def merge(path,section,values):
  if path.is_symlink():return False
  path.parent.mkdir(parents=True,exist_ok=True)
  backup=path.with_name(path.name+'.before-omarchy-theme')
  absent=path.with_name(path.name+'.before-omarchy-theme.absent')
  parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str
  if path.exists():
   parser.read(path)
   if not backup.exists() and not absent.exists():backup.write_bytes(path.read_bytes())
  elif not backup.exists() and not absent.exists():absent.touch()
  if not parser.has_section(section):parser.add_section(section)
  for key,value in values.items():parser.set(section,key,str(value))
  path.parent.mkdir(parents=True,exist_ok=True)
  temp=path.with_name(path.name+'.tmp')
  with temp.open('w') as f:parser.write(f)
  temp.replace(path);return True
 settings=merge(config/'gtk-3.0/settings.ini','Settings',{'gtk-theme-name':'Adwaita' if light else 'Adwaita-dark','gtk-application-prefer-dark-theme':0 if light else 1})
 css=config/'gtk-3.0/gtk.css'
 managed=not css.is_symlink() and (not css.exists() or css.read_text().startswith(MARKER))
 if managed:
  css.parent.mkdir(parents=True,exist_ok=True)
  text=MARKER+f'''@define-color theme_bg_color {bg};
@define-color theme_fg_color {fg};
@define-color theme_base_color {base};
@define-color theme_text_color {fg};
@define-color theme_selected_bg_color {accent};
@define-color theme_selected_fg_color {bg};
window, dialog, .background, headerbar, toolbar {{ background-color: {bg}; color: {fg}; }}
.view, treeview, textview, entry {{ background-color: {base}; color: {fg}; }}
button {{ background-image: none; background-color: {bg}; color: {fg}; border-color: {muted}; }}
placessidebar, placessidebar viewport, placessidebar list, placessidebar row {{ background-color: {bg}; color: {fg}; }}
placessidebar label {{ color: inherit; }}
placessidebar row:selected {{ background-color: {accent}; color: {bg}; }}
button:hover {{ background-color: {muted}; }}
button.suggested-action, .view:selected, treeview:selected, selection {{ background-color: {accent}; color: {bg}; }}
'''
  tmp=css.with_name('gtk.css.tmp');tmp.write_text(text);tmp.replace(css)
 image=merge(config/'gpicview/gpicview.conf','General',{'bg':bg,'bg_full':base})
 return {'gtk_settings':settings,'managed_css':managed,'image_background':image,'mode':'light' if light else 'dark','background':bg,'foreground':fg,'applies_to':'new GTK3 apps and next portal start'}
