#!/usr/bin/env python3
"""Linux-only transaction laboratory. Only freshly marked /tmp test roots accepted.
No live-root mode, service hooks, shell execution or device access.
"""
import base64
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

spec = importlib.util.spec_from_file_location('portal_policy', Path(__file__).with_name('portal-ownership.py'))
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
MARKER = '.portal-test-root'
MAGIC = b'omarchy-portal-isolated-transaction-v1\n'
TX = '.portal-transaction'
OWNER = '.portal-owner.json'
TARGETS = sorted(policy.TARGETS) + [OWNER]
LIMIT = 64 * 1024 * 1024

def checkpoint(label):
    """Fault-injection hook; production behavior is a no-op."""

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()

def initialize():
    if sys.platform != 'linux':
        raise ValueError('Linux test filesystem required')
    root = Path(tempfile.mkdtemp(prefix='omarchy-portal-test-')).resolve()
    (root/MARKER).write_bytes(MAGIC)
    (root/'usr/local/lib/omarchy-dock').mkdir(parents=True)
    return root

@contextlib.contextmanager
def parent(rootfd, relative):
    parts = relative.split('/')
    if not parts or any(p in ('', '.', '..') for p in parts):
        raise ValueError('Unsafe relative path')
    fd = os.dup(rootfd)
    try:
        for part in parts[:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = following
        yield fd, parts[-1]
    finally:
        os.close(fd)

def read_at(fd, name, with_xattrs=True):
    try:
        handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOATIME, dir_fd=fd)
    except FileNotFoundError:
        return None, None
    try:
        before = os.fstat(handle)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > LIMIT:
            raise ValueError('Expected bounded singly linked regular file')
        chunks = []
        while True:
            data = os.read(handle, 1024*1024)
            if not data: break
            chunks.append(data)
            if sum(map(len, chunks)) > LIMIT: raise ValueError('File grew beyond limit')
        data = b''.join(chunks)
        attrs = {key: base64.b64encode(os.getxattr(handle, key)).decode() for key in sorted(os.listxattr(handle))} if with_xattrs else {}
        after = os.fstat(handle)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise RuntimeError('Concurrent snapshot change')
        return data, {'sha256': sha(data), 'mode': stat.S_IMODE(before.st_mode),
                      'uid': before.st_uid, 'gid': before.st_gid, 'atime_ns': before.st_atime_ns,
                      'mtime_ns': before.st_mtime_ns, 'xattrs': attrs}
    finally:
        os.close(handle)

def snapshot(fd, name, with_xattrs=True):
    with parent(fd, name) as (directory, leaf):
        return read_at(directory, leaf, with_xattrs)

@contextlib.contextmanager
def locked(root):
    root = Path(root).absolute()
    if sys.platform != 'linux' or root.resolve() != root or root.parent != Path(tempfile.gettempdir()).resolve() or not root.name.startswith('omarchy-portal-test-'):
        raise ValueError('Only isolated temporary test roots supported')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    lock = None
    try:
        st = os.fstat(fd)
        if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o700:
            raise ValueError('Test root must be private and owned by caller')
        if snapshot(fd, MARKER)[0] != MAGIC:
            raise ValueError('Missing test marker')
        lock = os.open('.portal-lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
        info = os.fstat(lock)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('Invalid lock file')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield fd
    finally:
        if lock is not None: os.close(lock)
        os.close(fd)

def write(fd, name, data, metadata=None, label='blob'):
    handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        view = memoryview(data)
        while view:
            count = os.write(handle, view)
            if count <= 0: raise OSError('Short write')
            view = view[count:]; checkpoint(label+':write')
        if metadata is not None:
            current = os.fstat(handle)
            if (current.st_uid, current.st_gid) != (metadata['uid'], metadata['gid']):
                os.fchown(handle, metadata['uid'], metadata['gid'])
            os.fchmod(handle, metadata['mode'])
            for key, value in metadata['xattrs'].items():
                os.setxattr(handle, key, base64.b64decode(value, validate=True))
            os.utime(handle, ns=(metadata['atime_ns'], metadata['mtime_ns']))
            checkpoint(label+':metadata')
        os.fsync(handle); checkpoint(label+':fsync')
    finally:
        os.close(handle)

def save(txfd, journal):
    # A crashed journal rewrite is disposable; the durable journal stays authoritative.
    data, _ = read_at(txfd, 'journal.tmp')
    if data is not None: os.unlink('journal.tmp', dir_fd=txfd)
    write(txfd, 'journal.tmp', encoded(journal), label='journal')
    os.replace('journal.tmp', 'journal.json', src_dir_fd=txfd, dst_dir_fd=txfd)
    checkpoint('journal:rename'); os.fsync(txfd); checkpoint('journal:directory-fsync')

def identity(meta):
    return None if meta is None else {'sha256': meta['sha256'], 'mode': format(meta['mode'], '04o')}

def candidate(stage):
    stage = Path(stage).absolute()
    if stage.resolve() != stage: raise ValueError('Symlink stage root')
    fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        raw, _ = snapshot(fd, 'ownership.json', with_xattrs=False)
        receipt = json.loads(raw)
        expected = policy.ownership(receipt)
        payload = {}
        for target in sorted(expected):
            data, meta = snapshot(fd, 'rootfs/'+target, with_xattrs=False)
            if identity(meta) != expected[target]: raise ValueError('Staged payload drift')
            payload[target] = data
        payload[OWNER] = encoded(receipt)
        return receipt, payload
    finally:
        os.close(fd)

def prepare(root, stage):
    receipt, payload = candidate(stage)
    with locked(root) as fd:
        try: os.stat(TX, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError: pass
        else: raise ValueError('Retained transaction must be resolved in its existing test root')
        old = {target: snapshot(fd, target) for target in TARGETS}
        if old[OWNER][1] is not None and old[OWNER][1]['mode'] != 0o644:
            raise ValueError('Unexpected installed receipt mode')
        previous = json.loads(old[OWNER][0]) if old[OWNER][0] is not None else None
        policy.plan(previous, receipt, {target: identity(old[target][1]) for target in policy.TARGETS})
        os.mkdir(TX, mode=0o700, dir_fd=fd); os.fsync(fd); checkpoint('prepare:directory-fsync')
        txfd = os.open(TX, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            st = os.fstat(fd)
            journal = {'schema': 1, 'root': [st.st_dev, st.st_ino], 'state': 'prepared', 'entries': []}
            for i, target in enumerate(TARGETS):
                old_data, old_meta = old[target]
                new_data = payload[target]
                new_meta = dict(old_meta) if old_meta else {'uid': os.geteuid(), 'gid': os.getegid(), 'xattrs': {}, 'atime_ns': 0, 'mtime_ns': 0}
                new_meta.update(sha256=sha(new_data), mode=int(policy.TARGETS.get(target, '0644'), 8))
                if old_data is not None: write(txfd, str(i)+'.old', old_data, label='backup-'+str(i))
                write(txfd, str(i)+'.new', new_data, label='candidate-'+str(i))
                journal['entries'].append({'target': target, 'old': old_meta, 'new': new_meta})
            os.fsync(txfd); checkpoint('prepare:blobs-directory-fsync')
            save(txfd, journal)
            return journal
        finally:
            os.close(txfd)

def load(fd, txfd):
    raw, _ = read_at(txfd, 'journal.json')
    if raw is None: raise ValueError('Preparation incomplete; no target mutation occurred; retain test root for inspection')
    value = json.loads(raw)
    st = os.fstat(fd)
    if value.get('schema') != 1 or value.get('root') != [st.st_dev, st.st_ino] or value.get('state') not in ('prepared', 'committed-test', 'rolled-back'):
        raise ValueError('Invalid journal or wrong root')
    if [r['target'] for r in value['entries']] != TARGETS: raise ValueError('Invalid journal ownership')
    for i, row in enumerate(value['entries']):
        if set(row) != {'target', 'old', 'new'} or row['new'] is None: raise ValueError('Invalid journal entry')
        for version in ('old', 'new'):
            meta = row[version]
            if meta is not None:
                if set(meta) != {'sha256','mode','uid','gid','atime_ns','mtime_ns','xattrs'} or meta['mode'] != int(policy.TARGETS.get(row['target'], '0644'), 8):
                    raise ValueError('Invalid journal metadata')
                data, _ = read_at(txfd, str(i)+'.'+version)
                if data is None or sha(data) != meta['sha256']: raise ValueError('Backup or candidate corruption')
        if snapshot(fd, row['target'])[1] not in (row['old'], row['new']):
            raise RuntimeError('Target drift; refusing entire operation')
        with parent(fd, row['target']) as (directory, _):
            stale, meta = read_at(directory, '.portal-transaction-'+str(i)+'.tmp')
            if stale is not None:
                choices = [read_at(txfd, str(i)+'.'+v)[0] for v in ('old', 'new') if row[v] is not None]
                if not any(blob.startswith(stale) for blob in choices) or meta['mode'] not in (0o600, row['new']['mode']):
                    raise RuntimeError('Unexpected temporary file; refusing entire operation')
    return value

def replace(fd, txfd, row, version, i):
    expected = row[version]
    data = read_at(txfd, str(i)+'.'+version)[0] if expected is not None else None
    with parent(fd, row['target']) as (directory, leaf):
        current = read_at(directory, leaf)[1]
        if current not in (row['old'], row['new']): raise RuntimeError('Concurrent target drift')
        temporary = '.portal-transaction-'+str(i)+'.tmp'
        stale, stale_meta = read_at(directory, temporary)
        if stale is not None:
            choices = [read_at(txfd, str(i)+'.'+v)[0] for v in ('old', 'new') if row[v] is not None]
            if not any(value.startswith(stale) for value in choices): raise RuntimeError('Unexpected temporary contents')
            os.unlink(temporary, dir_fd=directory); os.fsync(directory)
        if current == expected: return
        label = version+'-'+str(i)
        if expected is None:
            os.unlink(leaf, dir_fd=directory); checkpoint(label+':unlink')
        else:
            write(directory, temporary, data, expected, label)
            if read_at(directory, temporary)[1] != expected: raise RuntimeError('Temporary readback mismatch')
            if read_at(directory, leaf)[1] != current: raise RuntimeError('Concurrent replacement')
            os.replace(temporary, leaf, src_dir_fd=directory, dst_dir_fd=directory); checkpoint(label+':rename')
        os.fsync(directory); checkpoint(label+':directory-fsync')
        if snapshot(fd, row['target'])[1] != expected: raise RuntimeError('Visible readback mismatch')

@contextlib.contextmanager
def transaction(root):
    with locked(root) as fd:
        txfd = os.open(TX, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        try: yield fd, txfd, load(fd, txfd)
        finally: os.close(txfd)

def apply(root, health):
    with transaction(root) as (fd, txfd, journal):
        if journal['state'] != 'prepared': raise ValueError('Expected prepared journal')
        # Refuse resume through apply; interrupted updates must be explicitly recovered.
        if any(snapshot(fd, r['target'])[1] != r['old'] for r in journal['entries']):
            raise ValueError('Partially applied transaction requires rollback')
        for i, row in enumerate(journal['entries'][:-1]): replace(fd, txfd, row, 'new', i)
        checkpoint('apply:before-health')
        if health() is not True: raise RuntimeError('Synthetic health gate failed; explicit recovery required')
        checkpoint('apply:after-health')
        # Callback cannot legitimize mutations or a changed journal/blob set.
        load(fd, txfd)
        if any(snapshot(fd, r['target'])[1] != r['new'] for r in journal['entries'][:-1]): raise RuntimeError('Payload changed before receipt commit')
        replace(fd, txfd, journal['entries'][-1], 'new', 3)
        if any(snapshot(fd, r['target'])[1] != r['new'] for r in journal['entries']):
            raise RuntimeError('Whole-group commit readback failed')
        checkpoint('apply:group-verified')
        journal['state'] = 'committed-test'; save(txfd, journal)

def recover(root):
    with transaction(root) as (fd, txfd, journal):
        for i in (2, 1, 0, 3): replace(fd, txfd, journal['entries'][i], 'old', i)
        if any(snapshot(fd, r['target'])[1] != r['old'] for r in journal['entries']):
            raise RuntimeError('Whole-group rollback readback failed')
        checkpoint('recover:group-verified')
        journal['state'] = 'rolled-back'; save(txfd, journal)
        return journal
