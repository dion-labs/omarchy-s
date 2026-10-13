#!/usr/bin/env python3
"""Bounded portal stream check. Frames are discarded; normal output selection stays enabled."""
import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gio,GLib,Gst
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seconds',type=int,default=10);p.add_argument('--require-changes',action='store_true');a=p.parse_args()
assert 3<=a.seconds<=30
assert os.environ.get('HOME')=='/trial/home' and os.environ.get('XDG_RUNTIME_DIR')=='/trial/run'
Gst.init(None);bus=Gio.bus_get_sync(Gio.BusType.SESSION,None);context=GLib.MainContext.default()
status=Path('/trial/screencast-check.json');session=None;pipeline=None;fd=None;serial=None
base=('org.freedesktop.portal.Desktop','/org/freedesktop/portal/desktop','org.freedesktop.portal.ScreenCast')
report={'pending':True,'recording_saved':False};frames=[];digests=set();dimensions=set();errors=[]
def write(**values):report.update(values);status.write_text(json.dumps(report)+'\n')
class PortalCancelled(Exception):pass

def request(method,args):
 found={};path=None
 def response(conn,sender,obj,iface,sig,params):found[obj]=params.unpack()
 sub=bus.signal_subscribe(base[0],'org.freedesktop.portal.Request','Response',None,None,Gio.DBusSignalFlags.NONE,response)
 try:
  path=bus.call_sync(*base,method,args,None,Gio.DBusCallFlags.NONE,5000,None).unpack()[0]
  deadline=time.monotonic()+45
  while path not in found:
   while context.pending():context.iteration(False)
   if time.monotonic()>deadline:raise TimeoutError('Output selection timed out')
   time.sleep(.01)
  code,result=found[path]
  if code==1:raise PortalCancelled()
  if code:raise RuntimeError('Portal request ended with response '+str(code))
  return result
 except BaseException:
  if path:
   try:bus.call_sync(base[0],path,'org.freedesktop.portal.Request','Close',None,None,Gio.DBusCallFlags.NONE,2000,None)
   except GLib.Error:pass
  raise
 finally:bus.signal_unsubscribe(sub)
def graph():return json.loads(subprocess.check_output(['pw-dump'],text=True,timeout=4))
def sample(sink,buffer,pad):
 try:
  ok,mapped=buffer.map(Gst.MapFlags.READ)
  if not ok:raise RuntimeError('Frame could not be mapped')
  try:digests.add(hashlib.blake2b(mapped.data,digest_size=8).digest())
  finally:buffer.unmap(mapped)
  caps=pad.get_current_caps().get_structure(0);dimensions.add((caps.get_value('width'),caps.get_value('height')))
  frames.append((time.monotonic(),buffer.pts))
  return Gst.FlowReturn.OK
 except Exception as error:errors.append(str(error));return Gst.FlowReturn.ERROR
def interrupted(*_):raise RuntimeError('Stream check interrupted')
for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,interrupted)
try:
 write(phase='creating_session')
 session=request('CreateSession',GLib.Variant('(a{sv})',({'handle_token':GLib.Variant('s','create'+str(os.getpid())),'session_handle_token':GLib.Variant('s','cast'+str(os.getpid()))},)))['session_handle']
 request('SelectSources',GLib.Variant('(oa{sv})',(session,{'types':GLib.Variant('u',1),'multiple':GLib.Variant('b',False),'persist_mode':GLib.Variant('u',0)})))
 write(phase='waiting_for_output_selection')
 streams=request('Start',GLib.Variant('(osa{sv})',(session,'',{})))['streams'];assert len(streams)==1
 node=streams[0][0];serial=next(x['info']['props']['object.serial'] for x in graph() if x['id']==node)
 reply,fds=bus.call_with_unix_fd_list_sync(*base,'OpenPipeWireRemote',GLib.Variant('(oa{sv})',(session,{})),GLib.VariantType.new('(h)'),Gio.DBusCallFlags.NONE,5000,None,None)
 fd=fds.get(reply.unpack()[0])
 pipeline=Gst.parse_launch('pipewiresrc name=source min-buffers=3 use-bufferpool=false ! video/x-raw ! fakesink name=frames signal-handoffs=true sync=false enable-last-sample=false')
 source=pipeline.get_by_name('source');source.set_property('fd',fd);source.set_property('target-object',str(serial))
 pipeline.get_by_name('frames').connect('handoff',sample);pipeline.set_state(Gst.State.PLAYING)
 write(phase='receiving_frames');started=time.monotonic();messages=pipeline.get_bus()
 while not frames or time.monotonic()-frames[0][0]<a.seconds:
  while context.pending():context.iteration(False)
  message=messages.timed_pop_filtered(0,Gst.MessageType.ERROR|Gst.MessageType.EOS)
  if message:
   if message.type==Gst.MessageType.ERROR:
    if os.environ.get('S9P_VIRTUAL_DRM'):Path('/trial/screencast-graph.log').write_text(json.dumps(graph(),indent=2))
    raise RuntimeError(str(message.parse_error()[0]))
   raise RuntimeError('Stream ended before observation completed')
  if errors:raise RuntimeError(errors[0])
  if not frames and time.monotonic()-started>12:raise TimeoutError('No frame received')
  if a.require_changes and frames and time.monotonic()-frames[-1][0]>4:raise TimeoutError('Stream stopped delivering frames')
  time.sleep(.01)
 pipeline.set_state(Gst.State.NULL);pipeline=None
 pts=[frame[1] for frame in frames];assert all(x!=Gst.CLOCK_TIME_NONE for x in pts)
 assert all(x<=y for x,y in zip(pts,pts[1:])),'Frame timestamps moved backwards'
 assert len(frames)>=(a.seconds*3 if a.require_changes else 1),'Insufficient frames'
 assert len(dimensions)==1 and all(0<n<=4096 for n in next(iter(dimensions)))
 if a.require_changes:assert len(digests)>2,'Stream did not contain changing content'
 write(pending=False,stream_passed=True,frames=len(frames),distinct_frames=len(digests),dimensions=list(next(iter(dimensions))),seconds=round(frames[-1][0]-frames[0][0],2),timestamps_monotonic=True,continuous_motion_checked=a.require_changes,max_frame_gap=round(max((y[0]-x[0] for x,y in zip(frames,frames[1:])),default=0),3))
except PortalCancelled:
 write(pending=False,cancelled=True,stream_passed=False)
except BaseException as error:
 write(pending=False,error=str(error),stream_passed=False,frames=len(frames),distinct_frames=len(digests));raise
finally:
 if pipeline:pipeline.set_state(Gst.State.NULL)
 if fd is not None:os.close(fd)
 if session:
  try:bus.call_sync(base[0],session,'org.freedesktop.portal.Session','Close',None,None,Gio.DBusCallFlags.NONE,3000,None)
  except GLib.Error:pass
 if serial is not None:
  deadline=time.monotonic()+4
  while True:
   exists=any(x.get('info',{}).get('props',{}).get('object.serial')==serial for x in graph())
   if not exists or time.monotonic()>deadline:break
   time.sleep(.1)
  write(stream_node_removed=not exists)
  assert not exists,'Portal stream node survived session close'
 print(json.dumps(report),flush=True)
