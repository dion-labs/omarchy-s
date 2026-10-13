#!/usr/bin/env python3
"""Linux disposable service fixture and bounded adapter; never launches portal binaries."""
import ctypes
import fcntl
import importlib.util
import json
import math
import os
from pathlib import Path
import secrets
import select
import signal
import socket
import struct
import subprocess
import sys
import time

s=importlib.util.spec_from_file_location('tx',Path(__file__).with_name('portal-transaction.py'))
tx=importlib.util.module_from_spec(s);s.loader.exec_module(tx)
SCRIPT=Path(__file__).resolve()
RECORD='.portal-child.json'
MODES={'normal','no-ready','bad-health','ignore-term','crash','silent'}


def checkpoint(label):
    """Coordinator death injection hook."""


def proc(pid):
    try:
        text=Path('/proc',str(pid),'stat').read_text();rest=text[text.rfind(')')+2:].split()
        return {'start':rest[19],'state':rest[0]}
    except FileNotFoundError:return None


def disk(fd):return {n:tx.identity(tx.snapshot(fd,n)[1]) for n in tx.TARGETS[:-1]}


def endpoint(token):return '\0omarchy-lab-'+token


class Child:
    def __init__(self,root,timeout=1.0,mode='normal'):
        if mode not in MODES or not math.isfinite(timeout) or not 0.05<=timeout<=5:
            raise ValueError('Invalid bounded fixture options')
        with tx.locked(root) as fd:self.fd=os.dup(fd)
        self.root=Path(root).absolute();self.timeout=timeout;self.mode=mode;self.children=[];self.owned=[]
        self.lock=None
        try:
            self.lock=os.open('.portal-child-controller',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
            import stat
            st=os.fstat(self.lock)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:raise ValueError('Invalid controller lock')
            fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:
            if self.lock is not None:os.close(self.lock)
            os.close(self.fd);raise
    def record(self):
        raw,_=tx.read_at(self.fd,RECORD)
        if raw is None:return None
        r=json.loads(raw);st=os.fstat(self.fd)
        if r.get('root')!=[st.st_dev,st.st_ino] or r.get('schema')!=1 or not isinstance(r.get('pid'),int) or r['pid']<=1:
            raise ValueError('Invalid child identity')
        if not isinstance(r.get('token'),str) or len(r['token'])!=32 or any(c not in '0123456789abcdef' for c in r['token']):
            raise ValueError('Invalid child token')
        return r
    def handle(self):
        r=self.record()
        if r is None:return None,None
        try:fd=os.pidfd_open(r['pid'])
        except ProcessLookupError:return r,None
        try:
            p=proc(r['pid'])
            if p is None or p['state']=='Z':os.close(fd);return r,None
            command=Path('/proc',str(r['pid']),'cmdline').read_bytes().split(b'\0')
            if p['start']!=r.get('start') or command[1:5]!=[str(SCRIPT).encode(),b'--fixture',str(self.root).encode(),r['token'].encode()]:
                raise ValueError('Process identity mismatch; no signal sent')
            return r,fd
        except BaseException:os.close(fd);raise
    def stopped(self):
        _,fd=self.handle()
        try:
            handles=self.owned+([fd] if fd is not None else [])
            return all(select.select([handle],[],[],0)[0] for handle in handles)
        finally:
            if fd is not None:os.close(fd)
    def terminate(self,fd):
        if select.select([fd],[],[],0)[0]:return True
        checkpoint('child:before-term')
        try:signal.pidfd_send_signal(fd,signal.SIGTERM)
        except ProcessLookupError:return True
        checkpoint('child:after-term')
        if not select.select([fd],[],[],self.timeout)[0]:
            try:signal.pidfd_send_signal(fd,signal.SIGKILL)
            except ProcessLookupError:pass
            checkpoint('child:after-kill')
            if not select.select([fd],[],[],self.timeout)[0]:return False
        return True
    def quiesce(self):
        _,fd=self.handle()
        try:
            if fd is not None and not self.terminate(fd):return False
            for owned in self.owned:
                if not self.terminate(owned):return False
            for child in self.children:child.poll()
            return True
        finally:
            if fd is not None:os.close(fd)
    def healthy(self,identity):
        r,fd=self.handle()
        if fd is None:return False
        try:
            if select.select([fd],[],[],0)[0]:return False
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                client.settimeout(self.timeout);client.connect(endpoint(r['token']))
                peer=struct.unpack('3i',client.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                if peer[0]!=r['pid'] or peer[1]!=os.geteuid():return False
                client.sendall(b'health\n');data=b''
                deadline=time.monotonic()+self.timeout
                while not data.endswith(b'\n'):
                    remaining=deadline-time.monotonic()
                    if remaining<=0 or len(data)>8192:return False
                    client.settimeout(remaining);chunk=client.recv(8192-len(data)+1)
                    if not chunk:return False
                    data+=chunk
                response=json.loads(data)
                return response=={'token':r['token'],'identity':identity} and disk(self.fd)==identity
        except (OSError,ValueError):return False
        finally:os.close(fd)
    def start(self,identity):
        if not self.stopped() or disk(self.fd)!=identity:return False
        token=secrets.token_hex(16)
        child=subprocess.Popen([sys.executable,str(SCRIPT),'--fixture',str(self.root),token,self.mode,str(os.getpid())],
                               stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
        self.children.append(child)
        try:self.owned.append(os.pidfd_open(child.pid))
        except ProcessLookupError:return False
        checkpoint('child:spawned')
        deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            if child.poll() is not None:return False
            try:r=self.record()
            except RuntimeError as error:
                if str(error)!='Concurrent snapshot change':raise
                # Atomic record replacement can change the old inode's ctime.
                # Retry only during this known spawn, within the same deadline.
                time.sleep(0.01);continue
            if r and r['pid']==child.pid and r['token']==token and self.healthy(identity):
                checkpoint('child:ready');return True
            time.sleep(0.01)
        # Keep known failed child for explicit lifecycle recovery; never silently commit.
        return False
    def close(self):
        try:self.quiesce()
        finally:
            for child in self.children:
                try:child.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:pass
            for owned in self.owned:os.close(owned)
            os.close(self.lock);os.close(self.fd)


def fixture(root,token,mode,parent):
    # Death before prctl is covered by the parent recheck; death after it kills us.
    if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0:raise OSError('PDEATHSIG failed')
    if os.getppid()!=parent:return
    if mode not in MODES or len(token)!=32 or any(c not in '0123456789abcdef' for c in token):return
    root=Path(root)
    # Parent owns transaction lock, so verify marker directly rather than relock.
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        st=os.fstat(fd)
        if root.parent!=Path('/tmp') or not root.name.startswith('omarchy-portal-test-') or st.st_uid!=os.geteuid() or st.st_mode&0o777!=0o700 or tx.read_at(fd,tx.MARKER)[0]!=tx.MAGIC:
            raise ValueError('Invalid fixture root')
        identity=disk(fd)
        record={'schema':1,'root':[st.st_dev,st.st_ino],'pid':os.getpid(),'start':proc(os.getpid())['start'],'token':token}
        draft='.portal-child-'+token+'.tmp';tx.write(fd,draft,tx.encoded(record))
        os.replace(draft,RECORD,src_dir_fd=fd,dst_dir_fd=fd);os.fsync(fd)
        if mode=='crash':return
        if mode=='ignore-term':signal.signal(signal.SIGTERM,signal.SIG_IGN)
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
            if mode!='no-ready':server.bind(endpoint(token));server.listen(1)
            end=time.monotonic()+30
            while time.monotonic()<end:
                if mode=='no-ready':time.sleep(0.05);continue
                server.settimeout(min(0.2,end-time.monotonic()))
                try:client,_=server.accept()
                except socket.timeout:continue
                with client:
                    client.settimeout(0.2)
                    try:
                        if client.recv(32)==b'health\n':
                            if mode=='silent':time.sleep(2);continue
                            reply={'token':token,'identity':identity if mode!='bad-health' else {}}
                            client.sendall(json.dumps(reply).encode()+b'\n')
                    except OSError:pass
    finally:os.close(fd)


if __name__=='__main__':
    if len(sys.argv)!=6 or sys.argv[1]!='--fixture':raise SystemExit('Internal disposable fixture only')
    fixture(sys.argv[2],sys.argv[3],sys.argv[4],int(sys.argv[5]))
