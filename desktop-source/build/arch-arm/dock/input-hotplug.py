#!/usr/bin/env python3
"""Refresh only approved evdev bindings in an owned desktop mount namespace."""
import argparse,fcntl,json,os,signal,stat,subprocess,time
from pathlib import Path

REBIND="""
import ctypes,os,sys
target=sys.argv[2].encode()
libc=ctypes.CDLL(None,use_errno=True)
def check(result):
 if result:raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
# A removed evdev inode cannot serve as a mount target. Detach that binding;
# existing open streams remain valid, and the bridge retries closed streams.
result=libc.umount2(target,2)
if result and ctypes.get_errno() not in (2,22):check(result)
try:os.unlink(target)
except FileNotFoundError:pass
os.mknod(target,0o20600,int(sys.argv[1]));os.chown(target,1000,1000)
# /trial inherits nodev from bubblewrap. Permit only this validated device node
# in this private mount namespace; retain nosuid/noexec and host restrictions.
check(libc.mount(target,target,None,4096,None)) # MS_BIND
check(libc.mount(None,target,None,4096|32|2|8,None)) # BIND|REMOUNT|NOSUID|NOEXEC

"""

def identity(fd):
    ident=bytearray(8);unique=bytearray(80);name=bytearray(256)
    fcntl.ioctl(fd,0x80084502,ident)
    fcntl.ioctl(fd,0x80504508,unique)
    fcntl.ioctl(fd,0x81004506,name)
    return int.from_bytes(ident[:2],'little'),bytes(unique).split(b'\0')[0].decode().lower(),bytes(name).split(b'\0')[0].decode()

def descendants(pid):
    children={}
    # This kernel lacks /proc/PID/task/PID/children. Use only PPid metadata.
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            parent=next(int(line.split()[1]) for line in (entry/'status').read_text().splitlines() if line.startswith('PPid:'))
            children.setdefault(parent,[]).append(int(entry.name))
        except (OSError,ValueError,StopIteration):pass
    pending=[pid];seen=set()
    while pending:
        current=pending.pop()
        if current in seen:continue
        seen.add(current);yield current;pending.extend(children.get(current,[]))

def pending_bindings(allowed, bindings):
    """Reserve four interfaces per approved peripheral within the bridge's eight slots."""
    result=[]
    if len(allowed)!=2 or len(set(allowed))!=2:
        raise ValueError('Expected two distinct approved peripherals')
    for index,uniq in enumerate(allowed):
        count=sum(b['uniq']==uniq for b in bindings)
        if count>4:raise ValueError('Too many interfaces for approved peripheral')
        for slot in range(count,4):
            result.append(dict(target=f'event-pending-{index}-{slot}',uniq=uniq,name=None))
    return result

def binding_candidates(bindings, current):
    """Match each unique interface once; ambiguous devices are never opened."""
    used={(b['uniq'],b['name']) for b in bindings if b['name'] is not None}
    for binding in bindings:
        name=binding['name']
        if name is None:
            matches=sorted(key for key,paths in current.items()
                           if key[0]==binding['uniq'] and key not in used and len(paths)==1)
            if not matches:continue
            key=matches[0];used.add(key);name=key[1]
        paths=current.get((binding['uniq'],name),[])
        if len(paths)==1:yield binding,name,paths[0]

def input_devices():
    current={}
    for event in Path('/sys/class/input').glob('event*'):
        try:
            d=event/'device'
            if (d/'id/bustype').read_text().strip()!='0005':continue
            key=((d/'uniq').read_text().strip().lower(),(d/'name').read_text().strip())
            current.setdefault(key,[]).append(Path('/dev/input')/event.name)
        except OSError:continue
    return current

def device_mount_blocked(target):
    # ST_NODEV is Linux flag 4; macOS test hosts may not expose the constant.
    return bool(os.statvfs(target).f_flag & getattr(os,'ST_NODEV',4))

class InputHotplug:
    def __init__(self,parent,remote,bindings):
        self.parent=parent;self.remote=Path(remote);self.bindings=bindings
        self.rebound=0;self.last_error=None;self.namespace_pid=None
        self.original=self.remote.stat()
        self.report()
    def namespace(self):
        candidates=[self.namespace_pid] if self.namespace_pid else descendants(self.parent)
        for pid in candidates:
            root=Path(f'/proc/{pid}/root/trial')
            try:
                s=root.stat()
                if (s.st_dev,s.st_ino)==(self.original.st_dev,self.original.st_ino) and (root/'input').is_dir():
                    self.namespace_pid=pid;return pid,root/'input'
            except OSError:pass
        self.namespace_pid=None
        return None,None
    def refresh(self):
        pid,target_root=self.namespace()
        if pid is None:return
        current=input_devices()
        for binding,name,node in binding_candidates(self.bindings,current):
            target=target_root/binding['target'];fd=None
            try:
                fresh=node.stat()
                try:old=target.stat()
                except FileNotFoundError:old=None
                if old and stat.S_ISCHR(old.st_mode) and old.st_rdev==fresh.st_rdev and old.st_nlink and old.st_mode & 0o400 and not device_mount_blocked(target):continue
                fd=os.open(node,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
                opened=os.fstat(fd)
                if not stat.S_ISCHR(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(fresh.st_dev,fresh.st_ino):continue
                if identity(fd)!=(5,binding['uniq'],name):continue
                # Replace an unlinked mount with a private char node after
                # validating the current device. The bridge validates each open.
                subprocess.run(['nsenter','-t',str(pid),'-m','-r','-p','--','/usr/bin/python3','-c',REBIND,str(opened.st_rdev),'/trial/input/'+binding['target']],pass_fds=(fd,),check=True,capture_output=True,timeout=4)
                after=target.stat()
                if not stat.S_ISCHR(after.st_mode) or after.st_rdev!=opened.st_rdev or device_mount_blocked(target):raise RuntimeError('Input binding verification failed')
                binding['name']=name
                self.rebound+=1;self.last_error=None;self.report()
            except (OSError,subprocess.SubprocessError,RuntimeError) as exc:
                self.last_error=str(exc)+((': '+exc.stderr.decode(errors='replace')) if isinstance(exc,subprocess.CalledProcessError) and exc.stderr else '');self.report()
            finally:
                if fd is not None:os.close(fd)
    def report(self):
        tmp=self.remote/'input-hotplug.json.tmp';tmp.write_text(json.dumps({'rebound_nodes':self.rebound,'error':self.last_error})+'\n');tmp.replace(self.remote/'input-hotplug.json')
    def close(self):
        # Private nodes disappear with the session; host device ACLs are untouched.
        (self.remote/'input-hotplug-cleanup.json').write_text(json.dumps({'rebound_nodes':self.rebound,'host_acls_changed':False})+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=int);p.add_argument('remote',type=Path);a=p.parse_args()
    assert os.geteuid()==0 and a.remote.parent==Path('/var/tmp') and a.remote.name.startswith('hyprland-headless-dock-')
    parent=Path('/proc')/str(a.parent);token=(parent/'stat').read_text().split()[21]
    assert str(a.remote/'input-access.py').encode() in (parent/'cmdline').read_bytes()
    guard=InputHotplug(a.parent,a.remote,json.loads((a.remote/'input-bindings.json').read_text()))
    def stop(*_):raise SystemExit(0)
    for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):signal.signal(sig,stop)
    try:
        while parent.exists() and (parent/'stat').read_text().split()[21]==token:
            guard.refresh();time.sleep(1)
    finally:guard.close()
