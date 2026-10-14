#!/usr/bin/env python3
"""Cooperative private-session fence. Not a portal/D-Bus interception mechanism."""
import contextlib
import fcntl
import importlib.util
import math
import os
from pathlib import Path
import secrets
import stat
import time

s=importlib.util.spec_from_file_location('admission',Path(__file__).with_name('portal-admission.py'))
a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
tx=a.lifecycle.tx
LOCK='.portal-admission-lock'
DIRTY='.portal-admission-pending'
CAPTURE_PREFIX='.portal-capture-'

def checkpoint(label):
    """Abrupt-exit test hook."""

class Fence:
    """Every cooperating client holds a shared lock for its entire session.

    Exclusive admission excludes those clients. A durable pending marker keeps
    clients blocked after coordinator death until explicit reconciliation. Fresh
    private sessions only: no completeness claim about arbitrary portal clients.
    """
    def __init__(self,root,timeout=.5):
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not .01<=timeout<=2:
            raise ValueError('Expected bounded lock timeout')
        self.root=Path(root);self.timeout=timeout
    @contextlib.contextmanager
    def locked(self,exclusive):
        with tx.locked(self.root) as rootfd:fd=os.dup(rootfd)
        lock=None
        try:
            lock=os.open(LOCK,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=fd)
            st=os.fstat(lock)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o600:
                raise a.Refused('Unsafe fence file')
            end=time.monotonic()+self.timeout
            while True:
                try:fcntl.flock(lock,(fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()>=end:raise a.Refused('Admission deadline exceeded')
                    time.sleep(.005)
            current=os.stat(LOCK,dir_fd=fd,follow_symlinks=False)
            if (current.st_dev,current.st_ino)!=(st.st_dev,st.st_ino):raise a.Refused('Fence replaced')
            yield fd,lock
        finally:
            if lock is not None:os.close(lock)
            os.close(fd)
    @staticmethod
    def pending(fd):
        try:os.stat(DIRTY,dir_fd=fd,follow_symlinks=False);return True
        except FileNotFoundError:return False
    @contextlib.contextmanager
    def client(self):
        with self.locked(False) as (fd,lock):
            if self.pending(fd):raise a.Refused('Explicit reconciliation required')
            yield
    @staticmethod
    def capture_pending(fd):
        return any(name.startswith(CAPTURE_PREFIX) for name in os.listdir(fd))
    @contextlib.contextmanager
    def capture_client(self):
        """Durable unresolved receipt precedes any portal call.

        Caller must confirm cleanup with an authoritative, bounded probe while
        still holding the shared lock. Exceptions/death preserve the receipt.
        Unresolved capture receipts cannot be cleared by transaction recovery.
        """
        with self.locked(False) as (fd,lock):
            if self.pending(fd):raise a.Refused('Explicit reconciliation required')
            name=CAPTURE_PREFIX+secrets.token_hex(16)
            receipt=os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=fd)
            try:os.write(receipt,b'capture cleanup unconfirmed\n');os.fsync(receipt)
            finally:os.close(receipt)
            os.fsync(fd)
            handle=CaptureReceipt(fd,name)
            try:yield handle
            finally:handle.active=False
    @contextlib.contextmanager
    def acquire(self):
        with self.locked(True) as (fd,lock):
            if self.pending(fd):raise a.Refused('Explicit reconciliation required')
            if self.capture_pending(fd):raise a.Refused('Capture cleanup unconfirmed')
            marker=os.open(DIRTY,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
            try:os.write(marker,b'private admission pending\n');os.fsync(marker)
            finally:os.close(marker)
            os.fsync(fd);checkpoint('fence-durable')
            lease=Lease(fd,lock)
            try:
                yield lease
                checkpoint('before-clear')
                os.unlink(DIRTY,dir_fd=fd);os.fsync(fd)
            finally:lease.active=False
    def reconcile(self,hooks):
        """Explicitly restore prior transaction under exclusivity, then reopen.

        Fresh prepared transactions can be abandoned only after exact old-state
        verification. Interrupted lifecycle transactions use lifecycle recovery.
        Exceptions retain the pending marker; no forced client termination.
        """
        with self.locked(True) as (fd,lock):
            if self.capture_pending(fd):raise a.Refused('Capture cleanup unconfirmed')
            if not self.pending(fd):raise a.Refused('No pending admission')
            with tx.transaction(self.root) as (rootfd,txfd,journal):
                has_lifecycle='lifecycle' in journal
                if not has_lifecycle:
                    if journal['state']!='prepared' or any(tx.snapshot(rootfd,r['target'])[1]!=r['old'] for r in journal['entries']):
                        raise a.Refused('Cannot reconcile unproven prior state')
            if has_lifecycle:
                lease=Lease(fd,lock)
                try:a.lifecycle.recover(self.root,a.Guard(hooks,lease,time.monotonic))
                finally:lease.active=False
            checkpoint('reconciled-before-clear')
            os.unlink(DIRTY,dir_fd=fd);os.fsync(fd)

class Lease:
    def __init__(self,fd,lock):
        self.fd=fd;self.lock=lock;self.active=True;self.pid=os.getpid()
        self.token=secrets.token_hex(16);self.epoch=secrets.token_hex(16)
        st=os.fstat(lock);self.identity=(st.st_dev,st.st_ino)
    def observe(self):
        if not self.active or os.getpid()!=self.pid:raise a.Refused('Expired or inherited lease')
        st=os.stat(LOCK,dir_fd=self.fd,follow_symlinks=False)
        if (st.st_dev,st.st_ino)!=self.identity or not Fence.pending(self.fd):raise a.Refused('Lost admission evidence')
        return dict(token=self.token,epoch=self.epoch,fenced=True,complete=True,responsive=True,
            observed_at=time.monotonic(),frontend_sessions=[],backend_sessions=[],requests=[],media_nodes=[],unknown_clients=[])

class CaptureReceipt:
    def __init__(self,fd,name):
        self.fd=fd;self.name=name;self.active=True;self.pid=os.getpid()
    def confirm_cleanup(self,probe):
        if not self.active or self.pid!=os.getpid():raise a.Refused('Expired capture receipt')
        if probe() is not True:raise a.Refused('Cleanup not confirmed')
        os.unlink(self.name,dir_fd=self.fd);os.fsync(self.fd);self.active=False
