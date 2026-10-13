#!/usr/bin/env python3
"""Request a desktop screenshot through the portal; retain no account metadata."""
import json,os,struct,shutil
from pathlib import Path
from urllib.parse import urlparse,unquote
from gi.repository import Gio,GLib
assert os.environ.get('HOME')=='/trial/home'
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None);loop=GLib.MainLoop();request=None
status=Path('/trial/capture-check.json')
status.write_text(json.dumps({'pending':True})+'\n')
def response(connection,sender,path,interface,signal,params):
 if path!=request:return
 code,result=params.unpack();record={'pending':False,'response':code}
 if code==0:
  uri=urlparse(result['uri']);assert uri.scheme=='file'
  source=Path(unquote(uri.path));header=source.read_bytes()[:24]
  assert header[:8]==b'\x89PNG\r\n\x1a\n'
  record['dimensions']=list(struct.unpack('>II',header[16:24]))
  shutil.copyfile(source,'/trial/capture-check.png')
 status.write_text(json.dumps(record)+'\n');loop.quit()
bus.signal_subscribe('org.freedesktop.portal.Desktop','org.freedesktop.portal.Request','Response',None,None,Gio.DBusSignalFlags.NONE,response)
request=bus.call_sync('org.freedesktop.portal.Desktop','/org/freedesktop/portal/desktop','org.freedesktop.portal.Screenshot','Screenshot',GLib.Variant('(sa{sv})',('',{'handle_token':GLib.Variant('s','omarchycapturecheck'),'interactive':GLib.Variant('b',False)})),None,Gio.DBusCallFlags.NONE,5000,None).unpack()[0]
def timeout():
 bus.call_sync('org.freedesktop.portal.Desktop',request,'org.freedesktop.portal.Request','Close',None,None,Gio.DBusCallFlags.NONE,5000,None)
 status.write_text(json.dumps({'pending':False,'timeout':True})+'\n');loop.quit();return False
GLib.timeout_add_seconds(180,timeout);loop.run()
