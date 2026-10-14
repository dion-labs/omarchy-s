#!/usr/bin/env python3
"""Opt-in real headless Phoc, frontend and capture cancellation tests."""
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE=Path(__file__).resolve().parent
ENABLED=sys.platform=='linux' and os.environ.get('OMARCHY_FRONTEND_LAB')=='1'
if ENABLED:
    from gi.repository import Gio,GLib

PIN='e3c43847acc34cd113f101087de3c113e7ae821c933515b0c55b2c92cbb7eb3b'
FRONT='org.freedesktop.portal.Desktop'
BACK='org.freedesktop.impl.portal.desktop.wlr'
PATH='/org/freedesktop/portal/desktop'
CAST='org.freedesktop.portal.ScreenCast'

@unittest.skipUnless(ENABLED,'Requires explicit reconstructed frontend Linux lab')
class Frontend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Path('/.dockerenv').exists():raise ValueError('Container-only test')
        lock=json.loads((HERE.parents[1]/'packaging/portal-frontend-lab.lock.json').read_text())
        for filename,digest in lock['runtime_files'].items():
            if hashlib.sha256(Path(filename).read_bytes()).hexdigest()!=digest:raise ValueError('Runtime pin differs: '+filename)
        cls.binary=Path(os.environ['OMARCHY_PORTAL_LAB_BINARY'])
        if hashlib.sha256(cls.binary.read_bytes()).hexdigest()!=PIN:raise ValueError('Portal pin differs')
        cls.build=Path(tempfile.mkdtemp(prefix='portal-front-build-'));cls.addClassCleanup(shutil.rmtree,cls.build)
        for mode,suffix in [('client-header','.h'),('private-code','.c')]:
            subprocess.run(['wayland-scanner',mode,'/usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml',str(cls.build/('xdg-shell'+suffix))],check=True,timeout=5)
        for file,extra,lib in [('portal-painter.c',[str(cls.build/'xdg-shell.c')],'wayland-client'),('portal-frame-probe.c',[],'libpipewire-0.3')]:
            flags=subprocess.check_output(['pkg-config','--cflags','--libs',lib],text=True).split()
            subprocess.run(['cc','-Wall','-Wextra','-Werror','-I'+str(cls.build),str(HERE/file),*extra,'-o',str(cls.build/file[:-2])]+flags,check=True,timeout=15)
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='portal-front-test-'));self.children=[];self.logs=[];self.connections=[];self.results={};self.counter=0
        self.addCleanup(self.cleanup)
        self.env={'PATH':'/usr/bin:/usr/sbin:/bin','HOME':str(self.root),'XDG_RUNTIME_DIR':str(self.root),
          'XDG_CONFIG_HOME':str(self.root),'XDG_DATA_HOME':str(self.root),'WAYLAND_DISPLAY':'wayland-lab','LANG':'C',
          'WLR_BACKENDS':'headless','WLR_RENDERER':'pixman','WLR_HEADLESS_OUTPUTS':'1','XDG_CURRENT_DESKTOP':'lab',
          'XDG_DESKTOP_PORTAL_DIR':str(self.root/'portals')}
        self.spawn(['dbus-daemon','--session','--nofork','--nopidfile','--address=unix:path='+str(self.root/'bus')])
        self.wait(lambda:(self.root/'bus').exists());self.env['DBUS_SESSION_BUS_ADDRESS']='unix:path='+str(self.root/'bus')
        self.compositor=self.spawn(['phoc','--no-xwayland','--socket','wayland-lab'])
        self.spawn(['pipewire']);self.wait(lambda:(self.root/'wayland-lab').exists() and (self.root/'pipewire-0').exists())
        self.spawn(['wireplumber']);self.spawn([str(self.build/'portal-painter')])
        (self.root/'wlr.conf').write_text('[screencast]\nchooser_type=none\noutput_name=HEADLESS-1\nmax_fps=25\n')
        self.backend=self.spawn([str(self.binary),'-c',str(self.root/'wlr.conf'),'-l','DEBUG'])
        (self.root/'portals').mkdir();(self.root/'portals/wlr.portal').write_text('[portal]\nDBusName='+BACK+'\nInterfaces=org.freedesktop.impl.portal.ScreenCast;\nUseIn=lab;\n')
        (self.root/'portals/portals.conf').write_text('[preferred]\ndefault=none\norg.freedesktop.impl.portal.ScreenCast=wlr\n')
        self.spawn(['/usr/lib/xdg-permission-store']);self.frontend=self.spawn(['/usr/lib/xdg-desktop-portal','--verbose'])
        self.client=self.connect();self.monitor=self.connect()
        self.wait(self.ready)
        self.client.signal_subscribe(None,'org.freedesktop.portal.Request','Response',None,None,Gio.DBusSignalFlags.NONE,self.response,None)
    def wait(self,predicate,seconds=5):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
            if predicate():return
            time.sleep(.02)
        self.fail('deadline exceeded\n'+self.logtext())
    def spawn(self,argv,pass_fds=()):
        path=self.root/('log-'+str(len(self.children)));log=path.open('wb');self.logs.append(log)
        p=subprocess.Popen(argv,env=self.env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,pass_fds=pass_fds)
        self.children.append(p);p.log_path=path;return p
    def connect(self):
        c=Gio.DBusConnection.new_for_address_sync(self.env['DBUS_SESSION_BUS_ADDRESS'],Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
        self.connections.append(c);return c
    def call(self,iface,method,params=None,path=PATH,dest=FRONT,connection=None):
        return (connection or self.client).call_sync(dest,path,iface,method,params,None,Gio.DBusCallFlags.NO_AUTO_START,1500,None)
    def ready(self):
        if self.frontend.poll() is not None:return False
        try:return self.call('org.freedesktop.DBus.Properties','Get',GLib.Variant('(ss)',(CAST,'version'))).unpack()==(4,)
        except GLib.Error:return False
    def response(self,c,sender,path,iface,name,params,data):self.results[path]=params.unpack()
    def token(self):self.counter+=1;return 'r'+str(self.counter)
    def request(self,method,signature,args,options,wait=True):
        options=dict(options);options['handle_token']=GLib.Variant('s',self.token())
        params=GLib.Variant(signature,(*args,options));path=self.call(CAST,method,params).unpack()[0]
        if not wait:return path
        self.wait(lambda:path in self.results);code,result=self.results.pop(path);self.assertEqual(code,0,result);return result
    def create(self):
        return self.request('CreateSession','(a{sv})',(),{'session_handle_token':GLib.Variant('s',self.token())})['session_handle']
    def start(self,session):
        self.request('SelectSources','(oa{sv})',(session,),{'types':GLib.Variant('u',1),'cursor_mode':GLib.Variant('u',1)})
        result=self.request('Start','(osa{sv})',(session,''),{})
        self.assertEqual(len(result['streams']),1);node,props=result['streams'][0];self.assertEqual(props['size'],(1280,720));return node
    def nodes(self):
        return {n['id'] for n in json.loads(subprocess.check_output(['pw-dump'],env=self.env,text=True,timeout=2)) if n['type']=='PipeWire:Interface:Node'}
    def exists(self,session,dest):
        try:
            xml=self.call('org.freedesktop.DBus.Introspectable','Introspect',None,session,dest,self.monitor).unpack()[0]
            interface='org.freedesktop.impl.portal.Session' if dest==BACK else 'org.freedesktop.portal.Session'
            return 'interface name="'+interface+'"' in xml
        except GLib.Error:return False
    def capture(self,session,node):
        value,fds=self.client.call_with_unix_fd_list_sync(FRONT,PATH,CAST,'OpenPipeWireRemote',GLib.Variant('(oa{sv})',(session,{})),None,Gio.DBusCallFlags.NO_AUTO_START,1500,None,None)
        fd=fds.get(value.unpack()[0])
        try:probe=self.spawn([str(self.build/'portal-frame-probe'),str(fd),str(node)],pass_fds=(fd,))
        finally:os.close(fd)
        def frames():return [json.loads(l) for l in probe.log_path.read_text().splitlines() if l.startswith('{')]
        self.wait(lambda:len(frames())>=3)
        values=frames();self.assertTrue(all(v['bytes']==1280*720*4 for v in values));self.assertTrue(any(v['color']>0 for v in values));self.assertGreater(len({v['color'] for v in values}),1)
        return values
    def close_session(self,session):self.call('org.freedesktop.portal.Session','Close',None,session)
    def assert_gone(self,session,node):
        self.wait(lambda:node not in self.nodes() and not self.exists(session,BACK) and not self.exists(session,FRONT))
    def stop(self,p):
        if p.poll() is None:
            p.send_signal(signal.SIGCONT);p.terminate()
            try:p.wait(timeout=2)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
    def logtext(self):return '\n'.join(p.read_text(errors='replace')[-5000:] for p in self.root.glob('log-*'))
    def cleanup(self):
        for c in self.connections:
            if not c.is_closed():c.close_sync(None)
        for p in reversed(self.children):self.stop(p)
        for log in self.logs:log.close()
        shutil.rmtree(self.root)
    def capture_fence(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('capture_fence',HERE/'portal-fence.py')
        fence=importlib.util.module_from_spec(spec);spec.loader.exec_module(fence)
        root=fence.tx.initialize();self.addCleanup(shutil.rmtree,root,True)
        return fence,root,fence.Fence(root,timeout=.06)
    def cleanup_confirmed(self,session,node):
        # Never convert D-Bus timeout/access errors into evidence of absence.
        if node in self.nodes():return False
        for dest,interface in [(FRONT,'org.freedesktop.portal.Session'),(BACK,'org.freedesktop.impl.portal.Session')]:
            if dest==BACK and self.backend.poll() is not None:
                owner=self.call('org.freedesktop.DBus','NameHasOwner',GLib.Variant('(s)',(BACK,)),
                    '/org/freedesktop/DBus','org.freedesktop.DBus',self.monitor).unpack()[0]
                if owner:return False
                continue
            try:xml=self.call('org.freedesktop.DBus.Introspectable','Introspect',None,session,dest,self.monitor).unpack()[0]
            except GLib.Error as error:
                if Gio.DBusError.get_remote_error(error)=='org.freedesktop.DBus.Error.UnknownObject':continue
                raise
            if 'interface name="'+interface+'"' in xml:return False
        return True
    def test_capture_admission_held_through_confirmed_close(self):
        fence,root,gate=self.capture_fence()
        with gate.capture_client() as receipt:
            session=self.create();node=self.start(session);self.capture(session,node)
            with self.assertRaises(fence.a.Refused):
                with gate.acquire():pass
            with self.assertRaises(fence.a.Refused):receipt.confirm_cleanup(lambda:self.cleanup_confirmed(session,node))
            self.close_session(session);self.wait(lambda:self.cleanup_confirmed(session,node))
            receipt.confirm_cleanup(lambda:self.cleanup_confirmed(session,node))
            # Even confirmed cleanup retains the shared lock until scope exit.
            with self.assertRaises(fence.a.Refused):
                with gate.acquire():pass
        with gate.acquire():pass
    def test_capture_disconnect_requires_media_confirmation(self):
        fence,root,gate=self.capture_fence()
        with gate.capture_client() as receipt:
            session=self.create();node=self.start(session);self.capture(session,node)
            self.client.close_sync(None);self.wait(lambda:self.cleanup_confirmed(session,node))
            receipt.confirm_cleanup(lambda:self.cleanup_confirmed(session,node))
        with gate.acquire():pass
    def test_capture_backend_death_retains_admission_until_frontend_closed(self):
        fence,root,gate=self.capture_fence()
        with gate.capture_client() as receipt:
            session=self.create();node=self.start(session);self.capture(session,node);self.stop(self.backend)
            self.wait(lambda:node not in self.nodes())
            with self.assertRaises(fence.a.Refused):receipt.confirm_cleanup(lambda:self.cleanup_confirmed(session,node))
            self.close_session(session);self.wait(lambda:self.cleanup_confirmed(session,node))
            receipt.confirm_cleanup(lambda:self.cleanup_confirmed(session,node))
        with gate.acquire():pass
    def test_capture_probe_failure_preserves_durable_refusal(self):
        fence,root,gate=self.capture_fence()
        with gate.capture_client() as receipt:
            session=self.create();node=self.start(session);self.capture(session,node)
            self.close_session(session);self.assert_gone(session,node)
            def unavailable():raise TimeoutError('cleanup probe unavailable')
            with self.assertRaises(TimeoutError):receipt.confirm_cleanup(unavailable)
        self.assertTrue(list(root.glob(fence.CAPTURE_PREFIX+'*')))
        with self.assertRaises(fence.a.Refused):
            with gate.acquire():pass
    def capture_identity(self,session,node):
        def bus(method,args):return self.call('org.freedesktop.DBus',method,args,'/org/freedesktop/DBus','org.freedesktop.DBus',self.monitor).unpack()[0]
        objects=json.loads(subprocess.check_output(['pw-dump'],env=self.env,text=True,timeout=2))
        core=next(o for o in objects if o['type']=='PipeWire:Interface:Core')
        return dict(bus_id=bus('GetId',None),frontend_owner=bus('GetNameOwner',GLib.Variant('(s)',(FRONT,))),
            backend_owner=bus('GetNameOwner',GLib.Variant('(s)',(BACK,))),session=session,node=node,pipewire_cookie=core['info']['cookie'])
    def recovery_probe(self,identity):
        current=self.capture_identity(identity['session'],identity['node'])
        gone=self.cleanup_confirmed(identity['session'],identity['node'])
        if self.capture_identity(identity['session'],identity['node'])!=current:
            raise RuntimeError('Service identity changed during cleanup probe')
        return dict(identity=current,frontend_absent=gone,backend_absent=gone,media_absent=gone)
    def test_recorded_capture_recovery_after_scope_loss(self):
        fence,root,gate=self.capture_fence()
        with gate.capture_client() as receipt:
            session=self.create();node=self.start(session);self.capture(session,node)
            receipt.record_identity(self.capture_identity(session,node));name=receipt.name
        with self.assertRaises(fence.a.Refused):gate.reconcile_capture(name,self.recovery_probe)
        self.close_session(session);self.wait(lambda:self.cleanup_confirmed(session,node))
        gate.reconcile_capture(name,self.recovery_probe)
        with gate.acquire():pass
    def test_recorded_capture_recovery_rejects_service_restart(self):
        fence,root,gate=self.capture_fence()
        with gate.capture_client() as receipt:
            session=self.create();node=self.start(session);self.capture(session,node)
            receipt.record_identity(self.capture_identity(session,node));name=receipt.name
            self.close_session(session);self.wait(lambda:self.cleanup_confirmed(session,node))
        self.stop(self.backend)
        self.backend=self.spawn([str(self.binary),'-c',str(self.root/'wlr.conf'),'-l','DEBUG'])
        self.wait(lambda:self.call('org.freedesktop.DBus','NameHasOwner',GLib.Variant('(s)',(BACK,)),
            '/org/freedesktop/DBus','org.freedesktop.DBus',self.monitor).unpack()[0])
        # A live replacement has a different unique owner: never clear old evidence.
        with self.assertRaises(fence.a.Refused):gate.reconcile_capture(name,self.recovery_probe)
        self.assertTrue((root/name).exists())
    def test_closed_tracked_sessions_cannot_authorize_update(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('admission',HERE/'portal-admission.py')
        admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
        session=self.create();node=self.start(session);self.capture(session,node)
        self.close_session(session);self.assert_gone(session,node)
        # These real observed objects are gone, but we cannot enumerate all clients
        # or fence new requests. Never turn this local success into global approval.
        observation=dict(fenced=False,complete=False,responsive=True,token='lab',epoch='lab',
            observed_at=time.monotonic(),frontend_sessions=[],backend_sessions=[],
            requests=[],media_nodes=[],unknown_clients=[])
        with self.assertRaises(admission.Refused):
            admission.require_idle(observation,'lab','lab',time.monotonic())
    def test_frames_and_explicit_close(self):
        session=self.create();node=self.start(session);values=self.capture(session,node);self.close_session(session);self.assert_gone(session,node)
        print('capture proof',json.dumps(values),flush=True)
    def test_application_disconnect_removes_capture(self):
        session=self.create();node=self.start(session);self.capture(session,node);self.client.close_sync(None);self.assert_gone(session,node)
    def test_repeat_capture_close(self):
        for _ in range(3):
            session=self.create();node=self.start(session);self.capture(session,node);self.close_session(session);self.assert_gone(session,node)
    def test_unresponsive_cancel_requires_reconciliation(self):
        session=self.create();self.backend.send_signal(signal.SIGSTOP)
        try:
            request=self.request('SelectSources','(oa{sv})',(session,),{'types':GLib.Variant('u',1)},wait=False)
            with self.assertRaises(GLib.Error):
                self.call('org.freedesktop.portal.Request','Close',None,request)
        finally:self.backend.send_signal(signal.SIGCONT)
        # Timed-out Close has unknown outcome. Reconcile by closing its session.
        if self.exists(session,FRONT):self.close_session(session)
        fresh=self.create();node=self.start(fresh);self.close_session(fresh);self.assert_gone(fresh,node)
        self.wait(lambda:not self.exists(session,BACK) and not self.exists(session,FRONT))
        print("cancel timeout reconciled; response observed",request in self.results,flush=True)
    def test_backend_death_requires_frontend_cleanup(self):
        session=self.create();node=self.start(session);self.capture(session,node);self.stop(self.backend)
        self.wait(lambda:node not in self.nodes() and not self.exists(session,BACK))
        self.assertTrue(self.exists(session,FRONT))
        self.close_session(session);self.assert_gone(session,node)

if __name__=='__main__':unittest.main()
