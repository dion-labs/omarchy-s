#!/usr/bin/env python3
"""Open a dock clipboard entry locally, without treating copied text as commands."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
assert os.geteuid()==1000 and os.environ.get('HOME')=='/trial/home'
assert len(sys.argv)==3 and sys.argv[1]=='--history-index'
index=int(sys.argv[2]);assert index>=0
state=Path.home()/'.local/state/omarchy'
entry=json.loads((state/'clipboard-history.json').read_text())[index]
if entry['type']=='text':
 directory=state/'clipboard-open';directory.mkdir(mode=0o700,exist_ok=True)
 fd,name=tempfile.mkstemp(prefix='clipboard-',suffix='.txt',dir=directory)
 with os.fdopen(fd,'w') as f:f.write(entry['text'])
 os.execvp('gnome-text-editor',['gnome-text-editor','--standalone',name])
elif entry['type']=='image':
 path=Path(entry['path']).resolve()
 assert path.parent==(state/'clipboard-images').resolve() and path.is_file()
 import gi
 gi.require_version('Gtk','4.0')
 from gi.repository import Gtk
 app=Gtk.Application(application_id='org.omarchys.ClipboardImage')
 def activate(app):
  window=Gtk.ApplicationWindow(application=app,title='Clipboard image')
  window.set_default_size(800,600)
  picture=Gtk.Picture.new_for_filename(str(path));picture.set_can_shrink(True)
  window.set_child(picture);window.present()
 app.connect('activate',activate);app.run([])
else:raise SystemExit('Unsupported clipboard entry')
