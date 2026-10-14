#!/usr/bin/env python3
"""Retire a pre-bound disposable container scope; never infer scope after a crash."""
import importlib.util
import json
import os
from pathlib import Path
import re
import stat

s=importlib.util.spec_from_file_location('fence',Path(__file__).with_name('portal-fence.py'))
f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
SCOPE='.portal-private-scope'

def checkpoint(label):pass

def identity(value):
    if type(value) is not dict or set(value)!={'engine_id','container_id','scope_token'}:raise f.a.Refused('Incomplete scope identity')
    if not isinstance(value['engine_id'],str) or not re.fullmatch(r'[A-Za-z0-9:_-]{8,128}',value['engine_id']):raise f.a.Refused('Invalid engine identity')
    for key,length in [('container_id',64),('scope_token',32)]:
        if not isinstance(value[key],str) or not re.fullmatch('[0-9a-f]{'+str(length)+'}',value[key]):raise f.a.Refused('Invalid scope identity')

def read(fd,name):
    h=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    try:
        st=os.fstat(h)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o600 or st.st_size>4096:raise f.a.Refused('Unsafe scope artifact')
        return os.read(h,4097)
    finally:os.close(h)

def bind(gate,value):
    """Before any capture: caller owns the disposable container and all its clients."""
    identity(value)
    with gate.locked(True) as (fd,lock):
        if gate.capture_pending(fd) or gate.pending(fd):raise f.a.Refused('Cannot infer old capture scope')
        h=os.open(SCOPE,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
        try:
            data=json.dumps(value,sort_keys=True).encode()+b'\n'
            with os.fdopen(h,'wb',closefd=False) as stream:stream.write(data);stream.flush()
            os.fsync(h)
        finally:os.close(h)
        os.fsync(fd)

def retire(gate,probe):
    """Terminal retirement, not permission to restart or reuse the old scope.

    Trusted bounded host probe must prove the exact container was destroyed on
    the recorded engine. Merely stopped/restarted/unreachable is insufficient.
    No engine operations or automatic deletion are performed by this function.
    """
    with gate.locked(True) as (fd,lock):
        raw=read(fd,SCOPE)
        try:value=json.loads(raw)
        except (ValueError,UnicodeError) as error:raise f.a.Refused('Lost scope identity') from error
        identity(value)
        h=os.open(f.RETIRED,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=fd) if not exists(fd,f.RETIRED) else None
        if h is not None:os.fsync(h);os.close(h);os.fsync(fd)
        read(fd,f.RETIRED)
        names=sorted(n for n in os.listdir(fd) if n.startswith(f.CAPTURE_PREFIX))
        for n in names:
            if not re.fullmatch(re.escape(f.CAPTURE_PREFIX)+r'(draft-)?[0-9a-f]{32}',n):raise f.a.Refused('Unknown capture artifact')
        before={n:read(fd,n) for n in names}
        proof=probe(dict(value))
        if type(proof) is not dict or proof.get('identity')!=value or proof.get('destroyed') is not True:raise f.a.Refused('Scope destruction unproven')
        if read(fd,SCOPE)!=raw or sorted(n for n in os.listdir(fd) if n.startswith(f.CAPTURE_PREFIX))!=names:raise f.a.Refused('Scope changed')
        if any(read(fd,n)!=data for n,data in before.items()):raise f.a.Refused('Capture evidence changed')
        checkpoint('scope-before-clear')
        for n in names:
            os.unlink(n,dir_fd=fd);os.fsync(fd);checkpoint('scope-cleared-one')
        # RETIRED and scope identity remain forever. New capture needs a new root.
        return len(names)

def exists(fd,name):
    try:os.stat(name,dir_fd=fd,follow_symlinks=False);return True
    except FileNotFoundError:return False
