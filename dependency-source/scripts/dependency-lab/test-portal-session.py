#!/usr/bin/env python3
"""Opt-in real pinned backend on private D-Bus/PipeWire and registry-only Wayland."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

HERE=Path(__file__).resolve().parent
PIN='e3c43847acc34cd113f101087de3c113e7ae821c933515b0c55b2c92cbb7eb3b'
NAME='org.freedesktop.impl.portal.desktop.wlr'
PATH='/org/freedesktop/portal/desktop'
CAST='org.freedesktop.impl.portal.ScreenCast'
SESSION='org.freedesktop.impl.portal.Session'


def wait_for(predicate, seconds=3):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if predicate():return True
        time.sleep(.02)
    return False


@unittest.skipUnless(sys.platform=='linux' and os.environ.get('OMARCHY_PORTAL_LAB_BINARY'),
                     'Requires explicit pinned binary and isolated Linux container')
class PortalSession(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary=Path(os.environ['OMARCHY_PORTAL_LAB_BINARY']).resolve()
        if hashlib.sha256(cls.binary.read_bytes()).hexdigest()!=PIN:raise ValueError('Unreviewed portal binary')
        if not Path('/.dockerenv').exists():raise ValueError('Container-only session laboratory')
        cls.build=Path(tempfile.mkdtemp(prefix='portal-session-build-'))
        cls.addClassCleanup(shutil.rmtree,cls.build)
        protocols=Path('/usr/share/wayland-protocols/staging')
        for stem,name in [('capture','ext-image-copy-capture'),('source','ext-image-capture-source'),('toplevel','ext-foreign-toplevel-list')]:
            xml=protocols/name/(name+'-v1.xml')
            expected={'capture':'41a446653f788fabb404cab3168c0bd667c1ff4b54f1f0bb1e18810a1f47d73f',
                      'source':'4ef41d15e4cdb9f550158391358ceec724a6708b43b7efedec03121a6bb8458d',
                      'toplevel':'6b2ffb3a07d679d1c4170263adfefb9a7c37dd34ed3db5180bf58cb8ff8fbd0b'}
            if hashlib.sha256(xml.read_bytes()).hexdigest()!=expected[stem]:raise ValueError('Protocol input drift')
            for kind,suffix in [('server-header','.h'),('private-code','.c')]:
                subprocess.run(['wayland-scanner',kind,str(xml),str(cls.build/(stem+suffix))],check=True,timeout=10)
        flags=subprocess.check_output(['pkg-config','--cflags','--libs','wayland-server'],text=True).split()
        subprocess.run(['cc','-Wall','-Wextra','-Werror','-I'+str(cls.build),str(HERE/'portal-wayland-fixture.c'),
                        str(cls.build/'capture.c'),str(cls.build/'source.c'),str(cls.build/'toplevel.c'),'-o',str(cls.build/'wayland-fixture')]+flags,check=True,timeout=20)
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='portal-session-test-'));self.children=[];self.logs=[];self.sessions=[]
        self.addCleanup(self.cleanup)
        self.env={'PATH':'/usr/bin:/bin','HOME':str(self.root),'XDG_RUNTIME_DIR':str(self.root),
                  'XDG_CONFIG_HOME':str(self.root),'WAYLAND_DISPLAY':'wayland-lab','LANG':'C'}
        self.bus=self.spawn(['dbus-daemon','--session','--nofork','--nopidfile','--address=unix:path='+str(self.root/'bus')])
        self.env['DBUS_SESSION_BUS_ADDRESS']='unix:path='+str(self.root/'bus')
        self.assertTrue(wait_for(lambda:(self.root/'bus').exists()))
        self.wayland=self.spawn([str(self.build/'wayland-fixture')])
        self.pipewire=self.spawn(['pipewire'])
        self.assertTrue(wait_for(lambda:(self.root/'wayland-lab').exists() and (self.root/'pipewire-0').exists()))
        (self.root/'config').write_text('[screencast]\nchooser_type=none\n')
        self.portal=self.spawn([str(self.binary),'-l','DEBUG','-c',str(self.root/'config')])
        self.assertTrue(wait_for(self.ready),self.logtext())
    def spawn(self,argv):
        log=open(self.root/('log-'+str(len(self.children))),'wb');self.logs.append(log)
        child=subprocess.Popen(argv,env=self.env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        self.children.append(child);return child
    def logtext(self):return '\n'.join(p.read_text(errors='replace') for p in self.root.glob('log-*'))
    def call(self,dest,path,method,*args):
        argv=['gdbus','call','--session','--timeout','1','--dest',dest,'--object-path',path,
              '--method',method,*args]
        try:return subprocess.run(argv,env=self.env,capture_output=True,text=True,timeout=2)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(argv,124,'','outer D-Bus deadline exceeded')
    def owner(self):
        r=self.call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus.GetNameOwner',NAME)
        if r.returncode:return None
        return re.search("'([^']+)'",r.stdout).group(1)
    def ready(self):
        if self.portal.poll() is not None:return False
        owner=self.owner()
        if not owner:return False
        r=self.call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus.GetConnectionUnixProcessID',owner)
        if r.returncode or r.stdout.strip()!=f'(uint32 {self.portal.pid},)':return False
        r=self.call(owner,PATH,'org.freedesktop.DBus.Properties.Get',CAST,'version')
        return r.returncode==0 and r.stdout.strip()=='(<uint32 4>,)' and self.owner()==owner
    def create(self,label):
        path='/org/freedesktop/portal/desktop/session/lab/'+label
        r=self.call(NAME,PATH,CAST+'.CreateSession','/org/freedesktop/portal/desktop/request/lab/'+label,path,'lab.test','{}')
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('uint32 0',r.stdout);self.sessions.append(path);return path
    def exists(self,path):
        r=self.call(NAME,path,'org.freedesktop.DBus.Introspectable.Introspect')
        return r.returncode==0 and SESSION in r.stdout
    def drain(self):
        owner=self.owner()
        if not owner:raise RuntimeError('Backend owner missing')
        for path in list(self.sessions):
            r=self.call(owner,path,SESSION+'.Close')
            if r.returncode or self.exists(path):raise RuntimeError('Close was not confirmed')
            self.sessions.remove(path)
        if self.owner()!=owner:raise RuntimeError('Owner changed during drain')
    def stop(self,child):
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
    def cleanup(self):
        for child in reversed(self.children):self.stop(child)
        for log in self.logs:log.close()
        shutil.rmtree(self.root)
    def test_readiness_owner_pid_and_capabilities(self):
        self.assertTrue(self.ready())
        r=self.call(NAME,PATH,'org.freedesktop.DBus.Properties.Get',CAST,'AvailableSourceTypes')
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('uint32 1',r.stdout)
        self.assertEqual(hashlib.sha256(Path('/proc',str(self.portal.pid),'exe').read_bytes()).hexdigest(),PIN)
    def test_explicit_close_after_caller_disconnect(self):
        paths=[self.create('s'+str(i)) for i in range(3)]
        # Each gdbus client has already exited. Backend sessions still exist.
        self.assertTrue(all(self.exists(p) for p in paths));self.drain()
        self.assertTrue(all(not self.exists(p) for p in paths));self.assertTrue(self.ready())
    def test_duplicate_close_is_not_success(self):
        p=self.create('once');self.drain()
        r=self.call(NAME,p,SESSION+'.Close');self.assertNotEqual(r.returncode,0)
    def test_restart_changes_owner_and_removes_old_sessions(self):
        p=self.create('old');old=self.owner();self.drain();self.stop(self.portal)
        self.assertTrue(wait_for(lambda:self.owner() is None))
        self.portal=self.spawn([str(self.binary),'-c',str(self.root/'config')]);self.assertTrue(wait_for(self.ready),self.logtext())
        self.assertNotEqual(old,self.owner());self.assertFalse(self.exists(p));self.create('new');self.drain()
    def test_pipewire_loss_loses_readiness(self):
        self.stop(self.pipewire);self.assertTrue(wait_for(lambda:self.portal.poll() is not None),self.logtext())
        self.assertFalse(self.ready());self.assertIsNone(self.owner())
    def test_wayland_loss_loses_readiness(self):
        self.stop(self.wayland);self.assertTrue(wait_for(lambda:self.portal.poll() is not None),self.logtext())
        self.assertFalse(self.ready());self.assertIsNone(self.owner())
    def test_name_collision_preserves_original_owner(self):
        owner=self.owner();second=self.spawn([str(self.binary),'-c',str(self.root/'config')])
        self.assertTrue(wait_for(lambda:second.poll() is not None));self.assertNotEqual(second.returncode,0)
        self.assertEqual(self.owner(),owner);self.assertTrue(self.ready())
    def test_unresponsive_backend_drain_fails_bounded(self):
        self.create('pending');self.portal.send_signal(signal.SIGSTOP);start=time.monotonic()
        try:
            self.assertFalse(self.ready())
            with self.assertRaises(RuntimeError):self.drain()
            self.assertLess(time.monotonic()-start,6)
            self.assertEqual(len(self.sessions),1)
        finally:self.portal.send_signal(signal.SIGCONT)
        self.drain();self.assertTrue(self.ready())

if __name__=='__main__':unittest.main()
