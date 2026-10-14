#!/usr/bin/env python3
"""Fail-closed admission contract for isolated update adapters, not a live collector."""
import importlib.util
import math
from pathlib import Path
import time

spec=importlib.util.spec_from_file_location('admission_lifecycle',Path(__file__).with_name('portal-lifecycle.py'))
lifecycle=importlib.util.module_from_spec(spec);spec.loader.exec_module(lifecycle)

class Refused(RuntimeError):
    pass

def require_idle(observation, token, epoch, now, max_age=1.0):
    """Validate a fresh inventory under a continuously held admission fence.

    The adapter must own an exclusive fence that prevents NEW clients/requests,
    and collect all frontend/backend sessions, pending requests and media nodes.
    An empty tracked-client list alone cannot meet this contract.
    """
    if not isinstance(observation,dict):raise Refused('Missing inventory')
    if not isinstance(token,str) or not token or not isinstance(epoch,str) or not epoch:
        raise Refused('Missing fence identity')
    for field in ('fenced','complete','responsive'):
        if observation.get(field) is not True:raise Refused('Unconfirmed '+field)
    if observation.get('token')!=token or observation.get('epoch')!=epoch:
        raise Refused('Fence identity changed')
    stamp=observation.get('observed_at')
    if (type(stamp) not in (int,float) or type(now) not in (int,float)
        or type(max_age) not in (int,float) or not all(math.isfinite(x) for x in (stamp,now,max_age))
        or not 0<max_age<=1 or not 0<=now-stamp<=max_age):
        raise Refused('Stale or invalid inventory time')
    for field in ('frontend_sessions','backend_sessions','requests','media_nodes','unknown_clients'):
        value=observation.get(field)
        if type(value) is not list:raise Refused('Missing inventory: '+field)
        if value:raise Refused('Busy or unresolved: '+field)
    return True

class Guard:
    def __init__(self,hooks,lease,clock):
        self.hooks=hooks;self.lease=lease;self.clock=clock
        self.token=lease.token;self.epoch=lease.epoch
    def check(self):
        try:observation=self.lease.observe()
        except Exception as error:raise Refused('Inventory unavailable') from error
        return require_idle(observation,self.token,self.epoch,self.clock())
    def healthy(self,identity):
        self.check();return self.hooks.healthy(identity)
    def quiesce(self):
        self.check();return self.hooks.quiesce()
    def stopped(self):
        # Recheck AFTER stopping, before any payload mutation.
        result=self.hooks.stopped();self.check();return result
    def start(self,identity):
        self.check();return self.hooks.start(identity)

def run(root,hooks,admission,*,recover=False,clock=time.monotonic):
    """Hold an adapter-owned fence for the entire apply/recovery operation.

    No automatic cancellation, force-close, kill, retry or drain is performed.
    Adapter acquire/observe calls MUST have bounded deadlines. This synchronous
    contract cannot bound a broken adapter; no production adapter is supplied.
    Context exit must release the fence even on refusal. After a process crash,
    a new recovery attempt must acquire a new fence and fresh complete inventory.
    """
    with admission.acquire() as lease:
        guarded=Guard(hooks,lease,clock)
        guarded.check()
        return (lifecycle.recover if recover else lifecycle.apply)(root,guarded)
