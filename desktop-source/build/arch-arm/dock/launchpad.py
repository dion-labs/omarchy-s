#!/usr/bin/env python3
"""Small graphical entry point for the currently supported dock applications."""
import os,subprocess
from pathlib import Path
os.environ['GSK_RENDERER']='cairo'
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk
class Launchpad(Gtk.Application):
 def __init__(self):super().__init__(application_id='ai.dionlabs.OmarchySDock')
 def do_activate(self):
  window=self.get_active_window()
  if window:window.present();return
  window=Gtk.ApplicationWindow(application=self,title='Omarchy S');window.set_default_size(460,360)
  box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
  for prop in ('top','bottom','start','end'):getattr(box,'set_margin_'+prop)(24)
  title=Gtk.Label(label='Your desktop',xalign=0);title.add_css_class('title-1');box.append(title)
  apps=[('Browser',['python3','/trial/app-launch.py','browser']),('Terminal',['python3','/trial/app-launch.py','terminal']),('Files',['nautilus','--new-window',os.environ['HOME']]),('Text Editor',['gnome-text-editor','--standalone'])]
  if Path('/home/omarchy/Projects').is_dir():apps.insert(1,('Projects',['nautilus','--new-window','/home/omarchy/Projects']))
  for label,command in apps:
   button=Gtk.Button(label=label);button.connect('clicked',lambda _,cmd=command:subprocess.Popen(cmd));box.append(button)
  guide=Gtk.Label(label='Super + Space  ·  Omarchy menu and Apps\nSuper + Shift + S  ·  Screenshot\nSuper + V  ·  Clipboard history\nSuper + Return  ·  Terminal\nSuper + E  ·  Files\nSuper + N  ·  New text document\nSuper + F  ·  Full screen\nSuper + 1–0  ·  Workspaces\nSuper + Shift + 1–0  ·  Move window\nAlt + Tab  ·  Switch windows\n\nSuper is the Windows key.\nSave your work before unplugging the monitor.',xalign=0)
  guide.set_wrap(True);guide.set_selectable(True);box.append(guide)
  window.set_child(box);window.present()
Launchpad().run()
