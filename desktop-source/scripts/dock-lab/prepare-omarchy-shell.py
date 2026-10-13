#!/usr/bin/env python3
"""Prepare pinned upstream shell with an explicit phone-supported plugin set."""
from pathlib import Path
from network_panel import adapt as adapt_network
import json,shutil,hashlib,subprocess,re,argparse
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--upstream',type=Path,default=ROOT/'upstream/omarchy')
parser.add_argument('--output',type=Path,help='Fresh empty output directory for isolated builds')
args=parser.parse_args();up=args.upstream.resolve();out=args.output.resolve() if args.output else ROOT/'artifacts/hyprland-trial/omarchy-shell'
if args.output and out.exists() and any(out.iterdir()):raise SystemExit('Explicit output must be empty')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=up,text=True).strip()=='b83d3df0840504299d3099ebf391eb8110527edd'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=up,text=True).strip(),'Upstream checkout must be clean'
out.mkdir(parents=True,exist_ok=True)
shutil.copytree(up/'shell',out/'shell',dirs_exist_ok=True);shutil.copy2(up/'LICENSE',out/'LICENSE')
# The external session has no phone power or boot-intro ownership.
qml=out/'shell/shell.qml';text=qml.read_text()
text=text.replace('property BrightnessKeys brightnessKeys: BrightnessKeys { host: shell }','property var brightnessKeys: null')
text=text.replace('property BackgroundIntro bootIntro: BackgroundIntro { host: shell }','property var bootIntro: null')
text=text.replace('!shell.brightnessKeys.handle(entry.target)','shell.brightnessKeys && !shell.brightnessKeys.handle(entry.target)')
for method in ('prepareTheme','finishTheme'):
 text=text.replace('      shell.bootIntro.'+method+'(', '      if (shell.bootIntro) shell.bootIntro.'+method+'(')
for method in ('themeStatus','themeCoverStatus'):
 text=text.replace('return shell.bootIntro.'+method+'(token)', 'return shell.bootIntro ? shell.bootIntro.'+method+'(token) : "unsupported"')
qml.write_text(text)
registry=out/'shell/services/PluginRegistry.qml';text=registry.read_text().replace('localPluginWatcher.running = true','localPluginWatcher.running = false');registry.write_text(text)
(out/'default/omarchy').mkdir(parents=True,exist_ok=True)
(out/'default/omarchy/shortcuts').write_text('')
allowed={'omarchy.power','omarchy.bluetooth','omarchy.network','omarchy.background','omarchy.notifications','omarchy.bar','omarchy.menu','omarchy.workspaces','omarchy.clock','omarchy.keyboard-layout','omarchy.active-window','omarchy.clipboard','omarchy.tray'}
ids={json.loads(p.read_text())['id'] for p in (up/'shell/plugins').rglob('*manifest.json')}
config={'version':1,'disabledPlugins':sorted(ids-allowed),'plugins':[],'bar':{'position':'top','transparent':False,'centerAnchor':'omarchy.clock','layout':{'left':[{'id':'omarchy.menu'},{'id':'omarchy.workspaces'}],'center':[{'id':'omarchy.clock','format':'ddd HH:mm'}],'right':[{'id':'omarchy.power'},{'id':'omarchy.bluetooth'},{'id':'omarchy.network'},{'id':'omarchy.tray'},{'id':'omarchy.active-window'},{'id':'omarchy.keyboard-layout'}]}}}
(out/'config/omarchy').mkdir(parents=True,exist_ok=True);(out/'config/omarchy/shell.json').write_text(json.dumps(config,indent=2)+'\n')
menu={'apps':{'label':'Apps','aliases':['app','applications'],'provider':'apps'},'notifications':{'label':'Recent notifications','action':'omarchy-shell notifications showHistory'},'files':{'label':'Files','action':'nautilus --new-window /trial/home'},'projects':{'label':'Projects','action':'nautilus --new-window /home/omarchy/Projects'},'editor':{'label':'Text Editor','action':'env GSK_RENDERER=cairo gnome-text-editor --standalone'},'help':{'label':'Desktop shortcuts','action':'python3 /trial/launchpad.py'}}
menu['system']={'label':'System','icon':''}
for action,label in [('logout','End desktop session…'),('reboot','Restart phone…'),('poweroff','Shut down phone…')]:
 menu['system.'+action]={'label':label,'action':'python3 /usr/local/lib/omarchy-dock/app-launch.py power '+action}
menu['bluetooth']={'label':'Bluetooth','action':'omarchy-shell shell toggle omarchy.bluetooth'}
menu['network']={'label':'Wi-Fi','action':'omarchy-shell shell toggle omarchy.network'}
menu['sound']={'label':'Sound','action':'/usr/local/bin/omarchy-sound'}
menu['screenshot']={'label':'Take screenshot','action':'python3 /trial/screenshot.py'}
menu['clipboard']={'label':'Clipboard history','action':'omarchy-shell shell toggle omarchy.clipboard'}
menu['style']={'label':'Style'}
for name,label in [('tokyo-night','Tokyo Night'),('catppuccin','Catppuccin'),('gruvbox','Gruvbox'),('catppuccin-latte','Catppuccin Latte')]:
 target=out/'themes'/name;target.mkdir(parents=True,exist_ok=True)
 shutil.copy2(up/'themes'/name/'colors.toml',target/'colors.toml')
 shutil.copy2(up/'themes'/name/'backgrounds/omarchy.webp',target/'background.webp')
 menu['style.'+name]={'label':label,'action':'python3 /trial/theme-set.py '+name}
(out/'default/omarchy').mkdir(parents=True,exist_ok=True);(out/'default/omarchy/omarchy-menu.jsonc').write_text(json.dumps(menu,indent=2)+'\n')
(out/'bin').mkdir(exist_ok=True);shutil.copy2(up/'bin/omarchy-shell',out/'bin/omarchy-shell')
shutil.copytree(up/'default/fonts/omarchy',out/'fonts',dirs_exist_ok=True)
for name in ('omarchy-network-status','omarchy-network-band','omarchy-cmd-present'):
 shutil.copy2(up/'bin'/name,out/'bin'/name)
launcher=out/'bin/omarchy-launch-browser'
launcher.write_text('#!/bin/sh\nexec python3 /usr/local/lib/omarchy-dock/app-launch.py browser "$@"\n');launcher.chmod(0o755)
power=out/'shell/plugins/panels/power'
shutil.copy2(ROOT/'build/arch-arm/dock/battery-widget/BarWidget.qml',power/'BarWidget.qml')
power_manifest=json.loads((power/'manifest.json').read_text())
power_manifest['entryPoints']['barWidget']='BarWidget.qml'
power_manifest['description']='Read-only native phone battery percentage and status'
(power/'manifest.json').write_text(json.dumps(power_manifest,indent=2)+'\n')
network=out/'shell/plugins/panels/network/Panel.qml'
network.write_text(adapt_network(network.read_text()))
shutil.copy2(up/'bin/omarchy-bluetooth-device',out/'bin/omarchy-bluetooth-device')
shutil.copy2(ROOT/'build/arch-arm/dock/bluetooth-power',out/'bin/omarchy-bluetooth-power');(out/'bin/omarchy-bluetooth-power').chmod(0o755)
bt=out/'shell/plugins/panels/bluetooth/Panel.qml'
bt_text=bt.read_text().replace('    target: "omarchy.bluetooth"', '    target: "omarchy.bluetooth"\n    function portStatus(): string { return JSON.stringify({ adapter_present: !!root.adapter, enabled: root.adapter ? root.adapter.enabled : false, connected_count: root.connectedDevices.length, paired_count: root.devices.filter(function(d) { return d.paired || d.bonded || d.trusted }).length }) }')
bt.write_text(bt_text)
for name in ('omarchy-clipboard-paste-text','omarchy-clipboard-paste-file'):
 shutil.copy2(up/'bin'/name,out/'bin'/name)
shutil.copy2(ROOT/'build/arch-arm/dock/clipboard-open.py',out/'bin/omarchy-clipboard-open')
(out/'bin/omarchy-clipboard-open').chmod(0o755)
# Watchers belong to this private session and die with their shell; never kill
# processes by a broad command-line pattern when initializing clipboard history.
clipboard=out/'shell/plugins/clipboard/Clipboard.qml'
clip=clipboard.read_text()
lines=clip.splitlines()
lines=[('    command: ["true"]' if 'command: ["pkill"' in line else line) for line in lines]
clipboard.write_text('\n'.join(lines)+'\n')

# Right-click remains useful without introducing an unvalidated terminal.
w=out/'shell/plugins/menu/BarWidget.qml';text=w.read_text().replace('xdg-terminal-exec','python3 /trial/launchpad.py');w.write_text(text)
# Only desktop-supported entries: exclude handset session launchers and the
# phone agent's single-profile launcher from generic app discovery.
library=out/'shell/services/AppLibrary.qml'
text=library.read_text().replace('var values = DesktopEntries.applications.values || []', 'var allowed = ["org.gnome.Nautilus", "org.gnome.TextEditor", "org.gnome.Evince", "omarchy-s-browser", "omarchy-s-terminal"]; var values = (DesktopEntries.applications.values || []).filter(function(entry) { return allowed.indexOf(String(entry.id).replace(/\\.desktop$/, "")) >= 0 })')
text=text.replace('uwsm-app -- gtk-launch ', 'gtk-launch ')
library.write_text(text)
menuqml=out/'shell/plugins/menu/Menu.qml'
text=menuqml.read_text().replace('function requestDeleteSelected() {', 'function requestDeleteSelected() { return; // Package removal is not integrated on this port.')
menuqml.write_text(text)
# Static dock backgrounds use the pinned theme artwork and screen-sized decode.
# No video wallpaper service, GPU reveal animation, or extra image tool is needed.
background=out/'shell/plugins/background/Background.qml'
bg=background.read_text()
bg=bg.replace('  function transitionBackground(fromPath, path, finalPath, instant, force) {', '  function transitionBackground(fromPath, path, finalPath, instant, force) {\n    instant = true')
bg=bg.replace('sizeProbe.command = ["magick", "identify", "-ping", "-format", "%w %h", sizeProbe.path]', 'sizeProbe.command = ["true"]')
for function in ('openSelector','openThemeSwitcher'):
 bg,count=re.subn(r'  function '+function+r'\(\) \{.*?\n  \}', '  function '+function+'() {\n    if (root.shell) root.shell.summon("omarchy.menu", JSON.stringify({ menu: "style" }))\n  }',bg,flags=re.S)
 assert count==1
bg=bg.replace('    target: "background"', '    target: "background"\n    function status(): string { return JSON.stringify({ ready: root.ready, path: root.displayedBackground, surfaces: backgrounds.instances.length }) }')
background.write_text(bg)
manifest={'upstream':'b83d3df0840504299d3099ebf391eb8110527edd','allowed_plugins':sorted(allowed),'files':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'source-manifest.json'}}
manifest['adaptations']=['Read-only native S9+ battery widget; power-profile service disabled','No handset brightness ownership','No fullscreen boot intro','No live third-party plugin watcher','Explicit supported plugin list and menu','Dock-only clipboard with parent-owned watchers','Local clipboard text and image viewer','Static theme backgrounds with screen-sized decode','NetworkManager and BlueZ-only bus proxy; DNS, QR and speed-test UI omitted']
(out/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(out)
