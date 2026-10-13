#!/usr/bin/env python3
"""Explicit finalization and pruning for the isolated portal transaction laboratory."""
import importlib.util
import json
import os
from pathlib import Path
import re

spec = importlib.util.spec_from_file_location('portal_transaction', Path(__file__).with_name('portal-transaction.py'))
tx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tx)
HISTORY = '.portal-history-'
PRUNE = '.portal-prune-'

def checkpoint(label):
    """Fault injection hook for retirement and deletion boundaries."""

def names(inventory):
    allowed = {'journal.json'} | {str(i)+'.'+v for i in range(4) for v in ('old','new')}
    if not isinstance(inventory, dict) or not inventory or not set(inventory) <= allowed:
        raise ValueError('Unexpected archive inventory')

def identifier(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value):
        raise ValueError('Invalid transaction ID')
    return value

def atomic(fd, name, data):
    temporary = name+'.tmp'
    existing, _ = tx.read_at(fd, temporary)
    if existing is not None:
        # No externally named file is removed; only this operation's fixed draft.
        if not data.startswith(existing): raise RuntimeError('Unexpected decision draft')
        os.unlink(temporary, dir_fd=fd); os.fsync(fd); checkpoint('draft:removed')
    handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        view = memoryview(data)
        while view:
            count = os.write(handle, view)
            if count <= 0: raise OSError('Short decision write')
            view = view[count:]; checkpoint(name+':write')
        os.fsync(handle); checkpoint(name+':file-fsync')
    finally: os.close(handle)
    os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd); checkpoint(name+':rename')
    os.fsync(fd); checkpoint(name+':directory-fsync')

def validate_close(fd, value):
    st = os.fstat(fd)
    if value.get('schema') != 1 or value.get('root') != [st.st_dev, st.st_ino] or value.get('disposition') not in ('committed-test','rolled-back'):
        raise ValueError('Invalid close record or wrong root')
    identifier(value['transaction_id']); names(value['inventory'])
    if 'journal.json' not in value['inventory']: raise ValueError('Missing journal identity')

def inspect_inventory(fd, expected, missing=False, extra=()):
    actual = set(os.listdir(fd))
    if actual - set(expected) - set(extra): raise RuntimeError('Unexpected archive entry')
    if not missing and set(expected)-actual: raise RuntimeError('Missing retained evidence')
    for name in sorted(set(expected)&actual):
        if tx.read_at(fd, name)[1] != expected[name]: raise RuntimeError('Retained evidence drift')

def finalize(root):
    """End rollback eligibility; retain all blobs in a uniquely named archive."""
    with tx.locked(root) as fd:
        try: active = os.open(tx.TX, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        except FileNotFoundError: return None  # Never select some earlier history implicitly.
        try:
            journal = tx.load(fd, active)
            if journal['state'] not in ('committed-test','rolled-back'):
                raise ValueError('Only terminal transactions can be finalized')
            lifecycle = journal.get('lifecycle')
            if lifecycle is not None:
                expected = 'committed' if journal['state']=='committed-test' else 'restored'
                if lifecycle.get('schema') != 1 or lifecycle.get('phase') != expected:
                    raise ValueError('Lifecycle incomplete; recover service before finalization')
            txn = identifier(journal.get('transaction_id'))
            desired = 'new' if journal['state']=='committed-test' else 'old'
            if any(tx.snapshot(fd, row['target'])[1] != row[desired] for row in journal['entries']):
                raise RuntimeError('Terminal target drift')
            for i,target in enumerate(tx.TARGETS):
                with tx.parent(fd,target) as (parent,_):
                    if tx.read_at(parent,'.portal-transaction-'+str(i)+'.tmp')[0] is not None:
                        raise ValueError('Resolve temporary payload files before finalization')
            expected = {'journal.json'} | {str(i)+'.'+v for i,row in enumerate(journal['entries']) for v in ('old','new') if row[v] is not None}
            raw, _ = tx.read_at(active,'close.json')
            if raw is None:
                if set(os.listdir(active))-expected-{'close.json.tmp'}:
                    raise RuntimeError('Unexpected transaction contents')
                inventory = {name:tx.read_at(active,name)[1] for name in sorted(expected)}
                if any(v is None for v in inventory.values()):raise RuntimeError('Missing transaction contents')
                st = os.fstat(fd)
                record = {'schema':1,'transaction_id':txn,'root':[st.st_dev,st.st_ino],
                          'disposition':journal['state'],'inventory':inventory}
                raw = tx.encoded(record)
                atomic(active,'close.json',raw)
            record = json.loads(raw);validate_close(fd,record)
            if record['transaction_id'] != txn or record['disposition'] != journal['state'] or set(record['inventory']) != expected:
                raise RuntimeError('Close record differs from transaction')
            inspect_inventory(active,record['inventory'],extra=('close.json',))
            history = HISTORY+txn
            try:os.stat(history,dir_fd=fd,follow_symlinks=False)
            except FileNotFoundError:pass
            else:raise ValueError('History destination occupied')
            # The durable decision precedes the namespace change that frees TX.
            os.rename(tx.TX,history,src_dir_fd=fd,dst_dir_fd=fd);checkpoint('finalize:archive-rename')
            os.fsync(fd);checkpoint('finalize:root-fsync')
            return {'history':history,'close_sha256':tx.sha(raw),'disposition':record['disposition']}
        finally:os.close(active)

def histories(root):
    """Read retained handles after interruption; never auto-prune them."""
    result=[]
    with tx.locked(root) as fd:
        for name in sorted(os.listdir(fd)):
            if not name.startswith(HISTORY):continue
            txn=identifier(name[len(HISTORY):])
            archive=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            try:
                raw,_=tx.read_at(archive,'close.json')
                if raw is None:raise ValueError('Pruning in progress; use its saved handle')
                record=json.loads(raw);validate_close(fd,record)
                if record['transaction_id']!=txn:raise ValueError('History identity mismatch')
                result.append({'history':name,'close_sha256':tx.sha(raw),'disposition':record['disposition']})
            finally:os.close(archive)
    return result

def prune(root, history, close_sha256):
    """Explicit irreversible blob deletion; retain a small durable completion record."""
    if not isinstance(history,str) or not history.startswith(HISTORY):raise ValueError('Invalid history name')
    txn=identifier(history[len(HISTORY):])
    if not isinstance(close_sha256,str) or not re.fullmatch('[0-9a-f]{64}',close_sha256):raise ValueError('Invalid close digest')
    record_name=PRUNE+txn+'.json'
    with tx.locked(root) as fd:
        raw,_=tx.read_at(fd,record_name)
        record=json.loads(raw) if raw is not None else None
        archive=None
        try:
            try:archive=os.open(history,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            except FileNotFoundError:
                if record is None:raise ValueError('Unknown history; nothing authorized for deletion')
            if record is None:
                close,close_meta=tx.read_at(archive,'close.json')
                if close is None or tx.sha(close)!=close_sha256:raise ValueError('Close digest mismatch')
                decision=json.loads(close);validate_close(fd,decision)
                if decision['transaction_id']!=txn:raise ValueError('Wrong archive ID')
                inspect_inventory(archive,decision['inventory'],extra=('close.json',))
                inventory=dict(decision['inventory']);inventory['close.json']=close_meta
                st=os.fstat(fd)
                record={'schema':1,'transaction_id':txn,'root':[st.st_dev,st.st_ino],
                        'close_sha256':close_sha256,'state':'pruning','inventory':inventory}
                atomic(fd,record_name,tx.encoded(record))
            st=os.fstat(fd)
            if record.get('schema')!=1 or record.get('transaction_id')!=txn or record.get('root')!=[st.st_dev,st.st_ino] or record.get('close_sha256')!=close_sha256 or record.get('state') not in ('pruning','pruned'):
                raise ValueError('Invalid deletion receipt')
            inventory=record['inventory'];names({n:v for n,v in inventory.items() if n!='close.json'})
            if 'close.json' not in inventory:raise ValueError('Missing close identity')
            if archive is not None:
                if record['state']=='pruned':raise RuntimeError('Archive reappeared after completed pruning')
                # Validate every surviving entry before deleting even one.
                inspect_inventory(archive,inventory,missing=True)
                for name in sorted(os.listdir(archive)):
                    if tx.read_at(archive,name)[1]!=inventory[name]:raise RuntimeError('Concurrent archive drift')
                    os.unlink(name,dir_fd=archive);checkpoint('prune:unlink-'+name)
                    os.fsync(archive);checkpoint('prune:directory-fsync-'+name)
                os.rmdir(history,dir_fd=fd);checkpoint('prune:rmdir')
                os.fsync(fd);checkpoint('prune:root-fsync')
            if record['state']!='pruned':
                record['state']='pruned';atomic(fd,record_name,tx.encoded(record))
            return {'history':history,'state':'pruned','close_sha256':close_sha256}
        finally:
            if archive is not None:os.close(archive)

def prune_receipts(root):
    """Discover saved cleanup handles, including an interrupted cleanup."""
    result=[]
    with tx.locked(root) as fd:
        st=os.fstat(fd)
        for name in sorted(os.listdir(fd)):
            if not name.startswith(PRUNE) or not name.endswith('.json'):continue
            txn=identifier(name[len(PRUNE):-5]);raw,_=tx.read_at(fd,name);r=json.loads(raw)
            if r.get('schema')!=1 or r.get('root')!=[st.st_dev,st.st_ino] or r.get('transaction_id')!=txn or r.get('state') not in ('pruning','pruned'):
                raise ValueError('Invalid cleanup receipt')
            if not re.fullmatch('[0-9a-f]{64}',r.get('close_sha256','')):raise ValueError('Invalid cleanup identity')
            result.append({'history':HISTORY+txn,'close_sha256':r['close_sha256'],'state':r['state']})
    return result
