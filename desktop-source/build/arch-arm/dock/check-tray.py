#!/usr/bin/env python3
"""Register a short-lived synthetic status icon on this desktop's private bus."""
import json,os
from pathlib import Path
from gi.repository import Gio,GLib
assert os.geteuid()==1000 and os.environ.get('HOME')=='/trial/home'
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None);loop=GLib.MainLoop()
properties={'Category':('s','ApplicationStatus'),'Id':('s','omarchy-s-tray-check'),'Title':('s','System tray check'),'Status':('s','Active'),'WindowId':('u',0),'IconName':('s','dialog-information'),'IconPixmap':('a(iiay)',[]),'OverlayIconName':('s',''),'OverlayIconPixmap':('a(iiay)',[]),'AttentionIconName':('s',''),'AttentionIconPixmap':('a(iiay)',[]),'AttentionMovieName':('s',''),'ToolTip':('(sa(iiay)ss)',('dialog-information',[],'System tray check','Temporary desktop check')),'ItemIsMenu':('b',False),'Menu':('o','/')}
xml='<node><interface name="org.kde.StatusNotifierItem">'+''.join('<property name="'+name+'" type="'+kind+'" access="read"/>' for name,(kind,value) in properties.items())+'</interface></node>'
info=Gio.DBusNodeInfo.new_for_xml(xml).interfaces[0]
registration=bus.register_object('/StatusNotifierItem',info,None,lambda c,s,p,i,n:GLib.Variant(*properties[n]),None)
watcher='org.kde.StatusNotifierWatcher';path='/StatusNotifierWatcher'
result={}
try:
 host=bus.call_sync(watcher,path,'org.freedesktop.DBus.Properties','Get',GLib.Variant('(ss)',(watcher,'IsStatusNotifierHostRegistered')),None,Gio.DBusCallFlags.NONE,5000,None).unpack()[0]
 assert host,'Tray host is unavailable'
 bus.call_sync(watcher,path,watcher,'RegisterStatusNotifierItem',GLib.Variant('(s)',('/StatusNotifierItem',)),None,Gio.DBusCallFlags.NONE,5000,None)
 def verify():
  try:
   items=bus.call_sync(watcher,path,'org.freedesktop.DBus.Properties','Get',GLib.Variant('(ss)',(watcher,'RegisteredStatusNotifierItems')),None,Gio.DBusCallFlags.NONE,5000,None).unpack()[0]
   result.update(host_registered=bool(host),synthetic_item_registered=any(bus.get_unique_name() in x for x in items))
  except Exception as error:result['error']=str(error)
  loop.quit();return False
 GLib.timeout_add_seconds(3,verify);loop.run()
finally:
 bus.unregister_object(registration)
 Path('/trial/tray-check.json').write_text(json.dumps(result)+'\n')
assert result.get('synthetic_item_registered'),result
