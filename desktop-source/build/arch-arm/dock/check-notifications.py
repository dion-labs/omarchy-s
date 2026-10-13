#!/usr/bin/env python3
"""Exercise an ephemeral dock notification; no history or external message."""
import json,os,subprocess,time
from pathlib import Path
from gi.repository import Gio,GLib
assert os.environ.get('HOME')=='/trial/home'
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
def call(method,args=None):return bus.call_sync('org.freedesktop.Notifications','/org/freedesktop/Notifications','org.freedesktop.Notifications',method,args,None,Gio.DBusCallFlags.NONE,5000,None)
server=call('GetServerInformation').unpack()
nid=call('Notify',GLib.Variant('(susssasa{sv}i)',('Omarchy S check',0,'','Desktop notifications','Temporary integration test. No action needed.',[],{'transient':GLib.Variant('b',True)},5000))).unpack()[0]
record={'server':server,'popup_layer':False,'transient':True}
try:
 end=time.monotonic()+4
 while time.monotonic()<end:
  layers=json.loads(subprocess.check_output(['hyprctl','layers','-j'],text=True))
  names=[x['namespace'] for output in layers.values() for level in output['levels'].values() for x in level]
  if any('notif' in name for name in names):record['popup_layer']=True;break
  time.sleep(.25)
finally:
 call('CloseNotification',GLib.Variant('(u)',(nid,)))
 Path('/trial/notifications-check.json').write_text(json.dumps(record)+'\n')
assert record['popup_layer'],'Notification did not create a desktop layer'
