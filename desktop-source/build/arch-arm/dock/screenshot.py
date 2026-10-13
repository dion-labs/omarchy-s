#!/usr/bin/env python3
"""Save and copy a screenshot of this dock session through its desktop portal."""
import datetime,json,os,struct,subprocess,uuid
from pathlib import Path
from urllib.parse import urlparse,unquote
from gi.repository import Gio,GLib
assert os.geteuid()==1000 and os.environ.get('HOME')=='/trial/home'
assert os.environ.get('XDG_RUNTIME_DIR')=='/trial/run'
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None);loop=GLib.MainLoop()
token='omarchyscreenshot'+uuid.uuid4().hex
request='/org/freedesktop/portal/desktop/request/'+bus.get_unique_name()[1:].replace('.','_')+'/'+token
result={'pending':True};status=Path('/trial/screenshot-result.json')
status.write_text(json.dumps(result)+'\n')
def notify(title,body):
 try:
  bus.call_sync('org.freedesktop.Notifications','/org/freedesktop/Notifications','org.freedesktop.Notifications','Notify',GLib.Variant('(susssasa{sv}i)',('Screenshot',0,'camera-photo',title,body,[],{'transient':GLib.Variant('b',True)},5000)),None,Gio.DBusCallFlags.NONE,3000,None)
 except GLib.Error:pass

def response(connection,sender,path,interface,signal,params):
 if path!=request:return
 global result
 try:
  code,values=params.unpack()
  if code!=0:
   result={'pending':False,'cancelled':True};return
  uri=urlparse(values['uri'])
  if uri.scheme!='file' or uri.netloc not in ('','localhost'):raise ValueError('Unexpected screenshot location')
  source=Path(unquote(uri.path))
  if not source.is_absolute() or source.stat().st_size>64*1024*1024:raise ValueError('Unexpected screenshot size')
  data=source.read_bytes()
  if len(data)<24 or data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid PNG')
  dimensions=struct.unpack('>II',data[16:24])
  if not all(0<n<=16384 for n in dimensions):raise ValueError('Invalid screenshot dimensions')
  folder=Path.home()/'Pictures/Screenshots';folder.mkdir(parents=True,exist_ok=True,mode=0o700)
  name='Screenshot-'+datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S-%f')+'.png'
  target=folder/name
  fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as f:f.write(data)
  copied=False
  try:
   subprocess.run(['wl-copy','--type','image/png'],input=data,check=True,timeout=5);copied=True
  except (OSError,subprocess.SubprocessError):pass
  result={'pending':False,'saved':True,'filename':name,'dimensions':dimensions,'clipboard':copied}
  notify('Screenshot saved','Pictures/Screenshots'+(' · Copied to clipboard' if copied else ''))
 except Exception as error:
  result={'pending':False,'error':str(error)};notify('Screenshot failed','Please try again.')
 finally:
  status.write_text(json.dumps(result)+'\n');loop.quit()

subscription=bus.signal_subscribe('org.freedesktop.portal.Desktop','org.freedesktop.portal.Request','Response',request,None,Gio.DBusSignalFlags.NONE,response)
def timeout():
 try:bus.call_sync('org.freedesktop.portal.Desktop',request,'org.freedesktop.portal.Request','Close',None,None,Gio.DBusCallFlags.NONE,3000,None)
 except GLib.Error:pass
 status.write_text(json.dumps({'pending':False,'timeout':True})+'\n');loop.quit();return False
try:
 returned=bus.call_sync('org.freedesktop.portal.Desktop','/org/freedesktop/portal/desktop','org.freedesktop.portal.Screenshot','Screenshot',GLib.Variant('(sa{sv})',('',{'handle_token':GLib.Variant('s',token),'interactive':GLib.Variant('b',False)})),None,Gio.DBusCallFlags.NONE,5000,None).unpack()[0]
 if returned!=request:raise RuntimeError('Unexpected portal request path')
 timer=GLib.timeout_add_seconds(30,timeout);loop.run()
except Exception as error:
 status.write_text(json.dumps({'pending':False,'error':str(error)})+'\n');notify('Screenshot unavailable','Please try again after the desktop is ready.')
finally:bus.signal_unsubscribe(subscription)
