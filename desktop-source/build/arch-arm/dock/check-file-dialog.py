#!/usr/bin/env python3
"""Open and cancel an owned portal dialog without reading/selecting any file."""
import json,os,subprocess,time
from pathlib import Path
import gi
from gi.repository import Gio,GLib
assert os.environ.get('HOME')=='/trial/home'
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
request=None;record={'selected_file':False,'dialog_mapped':False}
try:
 reply=bus.call_sync('org.freedesktop.portal.Desktop','/org/freedesktop/portal/desktop','org.freedesktop.portal.FileChooser','OpenFile',GLib.Variant('(ssa{sv})',('','Omarchy desktop dialog check',{'handle_token':GLib.Variant('s','omarchydialogcheck'),'modal':GLib.Variant('b',False)})),None,Gio.DBusCallFlags.NONE,5000,None)
 request=reply.unpack()[0]
 end=time.monotonic()+8
 while time.monotonic()<end:
  clients=json.loads(subprocess.check_output(['hyprctl','clients','-j'],text=True))
  if any(c['mapped'] and c['title']=='Omarchy desktop dialog check' for c in clients):record['dialog_mapped']=True;break
  time.sleep(.25)
finally:
 if request:bus.call_sync('org.freedesktop.portal.Desktop',request,'org.freedesktop.portal.Request','Close',None,None,Gio.DBusCallFlags.NONE,5000,None)
 Path('/trial/file-dialog-check.json').write_text(json.dumps(record)+'\n')
assert record['dialog_mapped'],'Portal dialog did not map on external desktop'
