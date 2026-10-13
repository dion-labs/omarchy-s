#!/usr/bin/env python3
"""Configure only this private dock session's desktop services."""
import json,os,subprocess,time,tomllib
from gtk_theme import apply as apply_gtk_theme
from pathlib import Path
assert os.geteuid()==1000 and os.environ['HOME']=='/trial/home'
assert os.environ['XDG_RUNTIME_DIR']=='/trial/run'
applications=Path('/trial/home/.local/share/applications');applications.mkdir(parents=True,exist_ok=True)
(applications/'omarchy-s-browser.desktop').write_text('[Desktop Entry]\nType=Application\nName=Browser\nComment=Browse the web\nExec=python3 /usr/local/lib/omarchy-dock/app-launch.py browser %u\nIcon=chromium\nTerminal=false\nCategories=Network;WebBrowser;\nMimeType=x-scheme-handler/http;x-scheme-handler/https;\n')
for scheme in ('http','https'):
 subprocess.run(['xdg-mime','default','omarchy-s-browser.desktop','x-scheme-handler/'+scheme],check=True,timeout=5)
(applications/'omarchy-s-terminal.desktop').write_text('[Desktop Entry]\nType=Application\nName=Terminal\nExec=python3 /usr/local/lib/omarchy-dock/app-launch.py terminal\nIcon=utilities-terminal\nTerminal=false\nCategories=System;TerminalEmulator;\n')
# Dock-home overrides only: never edit package or handset desktop entries.
hidden_ids=(
 'chatgpt.desktop','chatgpt-software.desktop','chromium.desktop',
 'foot.desktop','footclient.desktop','foot-server.desktop',
 'ai.dionlabs.ContinuityPreview.desktop','ai.dionlabs.ContinuityPreviewDesktop.desktop',
 'ai.dionlabs.OmarchyHome.desktop','ai.dionlabs.OmarchyStatus.desktop',
 'org.gnome.Extensions.desktop','org.freedesktop.IBus.Setup.desktop',
 'qv4l2.desktop','qvidcap.desktop','vim.desktop',
)
backup=applications/'.before-omarchy-catalog';backup.mkdir(exist_ok=True)
for desktop_id in hidden_ids:
 target=applications/desktop_id
 marker=backup/(desktop_id+'.absent')
 if not (backup/desktop_id).exists() and not marker.exists():
  if target.exists():(backup/desktop_id).write_bytes(target.read_bytes())
  else:marker.touch()
 target.write_text('[Desktop Entry]\nType=Application\nName=Unavailable in this desktop\nHidden=true\n')
(applications/'omarchy-s-projects.desktop').write_text('[Desktop Entry]\nType=Application\nName=Projects\nExec=nautilus --new-window /home/omarchy/Projects\nIcon=folder-documents\nTerminal=false\nCategories=Utility;FileManager;\n')
# Resolve exactly the visible catalogue using the standard desktop-entry rules.
from gi.repository import Gio
visible=sorted((app.get_id(),app.get_name()) for app in Gio.AppInfo.get_all() if app.should_show())
visible_ids={entry[0] for entry in visible}
assert not visible_ids.intersection(hidden_ids), 'Hidden dock-only entry leaked'
assert {'omarchy-s-browser.desktop','omarchy-s-terminal.desktop','omarchy-s-projects.desktop'} <= visible_ids
for desktop_id in ('omarchy-s-browser.desktop','omarchy-s-terminal.desktop','omarchy-s-projects.desktop'):
 subprocess.run(['desktop-file-validate',str(applications/desktop_id)],check=True,timeout=3)
Path('/trial/app-catalog.json').write_text(json.dumps({'visible':visible,'hidden':list(hidden_ids),'dock_only':True})+'\n')
# The inherited PDF association can point at the hidden direct Chromium entry.
# Preserve a different explicit application choice; fix only unset/legacy default.
pdf_default=subprocess.check_output(['xdg-mime','query','default','application/pdf'],text=True,timeout=3).strip()
if pdf_default in ('','chromium.desktop'):
 mime=Path(os.environ['XDG_CONFIG_HOME'])/'mimeapps.list'
 saved=mime.with_name('mimeapps.list.before-document-defaults')
 if mime.exists() and not saved.exists():saved.write_bytes(mime.read_bytes())
 subprocess.run(['xdg-mime','default','org.gnome.Evince.desktop','application/pdf'],check=True,timeout=3)
# Use the native viewer for legacy browser image associations, only in dock HOME.
for image_mime in ('image/png','image/jpeg'):
 image_default=subprocess.check_output(['xdg-mime','query','default',image_mime],text=True,timeout=3).strip()
 if image_default in ('','chromium.desktop'):
  mime=Path(os.environ['XDG_CONFIG_HOME'])/'mimeapps.list'
  saved=mime.with_name('mimeapps.list.before-image-defaults')
  if mime.exists() and not saved.exists():saved.write_bytes(mime.read_bytes())
  subprocess.run(['xdg-mime','default','gpicview.desktop',image_mime],check=True,timeout=3)
config=Path(os.environ['XDG_CONFIG_HOME'])
selected=Path.home()/'.local/state/omarchy/current/theme.name'
name=selected.read_text().strip() if selected.exists() else 'tokyo-night'
if name not in ('tokyo-night','catppuccin','gruvbox','catppuccin-latte'):name='tokyo-night'
palette=tomllib.loads((Path('/trial/omarchy-shell/themes')/name/'colors.toml').read_text())
Path('/trial/gtk-theme.json').write_text(json.dumps(apply_gtk_theme(palette,Path.home()))+'\n')
portal=config/'xdg-desktop-portal/portals.conf';portal.parent.mkdir(parents=True,exist_ok=True)
defaults='[preferred]\ndefault=gtk\norg.freedesktop.impl.portal.Screenshot=wlr\norg.freedesktop.impl.portal.ScreenCast=wlr\n'
if not portal.exists() or portal.read_text()=='[preferred]\ndefault=gtk\n':portal.write_text(defaults)
os.environ.update(XDG_CURRENT_DESKTOP='Hyprland',XDG_SESSION_TYPE='wayland')
subprocess.run(['dbus-update-activation-environment','HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','GSK_RENDERER']+([name for name in ('LD_LIBRARY_PATH','OMARCHY_PANFROST_CPU_INVALIDATE') if name in os.environ]),check=True,timeout=5)
marker=config/'omarchy-s/appearance-initialized'
if not marker.exists():
 subprocess.run(['gsettings','set','org.gnome.desktop.interface','color-scheme','prefer-dark'],check=True,timeout=5)
 marker.parent.mkdir(parents=True,exist_ok=True);marker.touch()
# Private runtime and hidden /dev/snd keep this separate from handset hardware.
if not Path('/trial/run/pipewire-0').is_socket():
 with open('/trial/pipewire.log','a') as log:subprocess.Popen(['pipewire'],stdout=log,stderr=log)
 deadline=time.monotonic()+4
 while not Path('/trial/run/pipewire-0').is_socket() and time.monotonic()<deadline:time.sleep(.1)
# Run policy only: no ALSA, Bluetooth or camera hardware ownership.
def policy_running():
 for process in Path('/proc').glob('[0-9]*'):
  try:
   if (process/'comm').read_text().strip()!='wireplumber':continue
   environment=(process/'environ').read_bytes().split(b'\0')
   if b'XDG_RUNTIME_DIR=/trial/run' in environment:return True
  except (OSError,PermissionError):continue
 return False
if not policy_running():
 with open('/trial/wireplumber.log','a') as log:
  subprocess.Popen(['wireplumber','--profile=policy'],stdout=log,stderr=log)
 deadline=time.monotonic()+4
 while not policy_running() and time.monotonic()<deadline:time.sleep(.1)
from portal_backend import start as start_portal_backend
backend=start_portal_backend()
with open('/trial/portal.log','a') as log:
 subprocess.Popen(['/usr/lib/xdg-desktop-portal','--replace'],stdout=log,stderr=log)
base=['gdbus','call','--session','--dest','org.freedesktop.portal.Desktop','--object-path','/org/freedesktop/portal/desktop']
end=time.monotonic()+12;result={'backend':backend}
while time.monotonic()<end:
 try:
  for interface in ('Settings','FileChooser'):
   output=subprocess.check_output(base+['--method','org.freedesktop.DBus.Properties.Get','org.freedesktop.portal.'+interface,'version'],text=True,stderr=subprocess.DEVNULL,timeout=2)
   result[interface]=output.strip()
  result['color_scheme']=subprocess.check_output(base+['--method','org.freedesktop.portal.Settings.Read','org.freedesktop.appearance','color-scheme'],text=True,timeout=2).strip()
  result['ready']=True;break
 except (subprocess.SubprocessError,OSError):time.sleep(.5)
else:result['ready']=False
Path('/trial/desktop-environment.json').write_text(json.dumps(result)+'\n')
raise SystemExit(0 if result['ready'] else 1)
