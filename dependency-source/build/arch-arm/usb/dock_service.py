"""Automatic dock session, called only by the existing exclusive USB owner."""
import fcntl,json,os,secrets,signal,subprocess,time
from pathlib import Path

def acquire_display_lock(path='/run/omarchy-display.lock'):
    """One inode shared with virtual tests; never unlink a flock lock file."""
    lock=open(path,'a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return None
    return lock

class DockPolicy:
    def __init__(self):self.since=None;self.attempted=False
    def decide(self,now,attached,enabled):
        if not attached:
            self.since=None;self.attempted=False
            return False
        if not enabled or self.attempted:return False
        if self.since is None:self.since=now
        if now-self.since<2:return False
        self.attempted=True
        return True

def inputs_ready():
    try:
        allowed=set(json.loads(Path('/usr/local/lib/omarchy-dock/allowed-inputs.json').read_text()))
        present={(p/'device/uniq').read_text().strip().lower()
                 for p in Path('/sys/class/input').glob('event*')
                 if (p/'device/id/bustype').read_text().strip()=='0005'}
        return len(allowed)==2 and allowed<=present
    except (OSError,ValueError):return False


def publish(event,**values):
    p=Path('/run/omarchy-dock.json.tmp')
    p.write_text(json.dumps(dict(event=event,uptime=time.monotonic(),**values))+'\n')
    p.replace('/run/omarchy-dock.json')

def session_ready(launch_id,pointer=Path('/run/omarchy-dock-session')):
    """A surviving ready file from another launch must never satisfy startup."""
    try:
        remote=Path(pointer.read_text().strip())
        owner=json.loads((remote/'launch.json').read_text())
        ready=json.loads((remote/'ready.json').read_text())
        return (owner.get('launch_id')==launch_id and ready.get('ready') is True
                and not (remote/'stopped.json').exists())
    except (OSError,ValueError,AttributeError):return False

def logout_requested(launch_id,pointer=Path('/run/omarchy-dock-session')):
    try:
        runtime=Path(pointer.read_text().strip())
        return (json.loads((runtime/'launch.json').read_text()).get('launch_id')==launch_id
                and json.loads((runtime/'logout-request.json').read_text())=={'action':'logout'})
    except (OSError,ValueError,AttributeError):return False

def session(hw,heartbeat):
    """Never outlives attachment, enable marker, child, or kernel lease."""
    module=Path('/sys/module/s9p_dp_pll_lab')
    if module.exists():raise RuntimeError('Display already owned')
    if Path('/sys/module/s9p_allocator_lab').exists():raise RuntimeError('Virtual display active')
    process=None;reason='starting';token=0
    launch_id=secrets.token_hex(16)
    start=time.monotonic()
    publish('starting')
    load=subprocess.Popen(['/usr/bin/insmod','/var/tmp/s9p-dp-pll-lab.ko','aux_test=1','train=1','pattern_seconds=180','decon_test=1','drm_test=1','dock_session=1'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    try:
        for _ in range(20):
            heartbeat()
            try:
                _,error=load.communicate(timeout=.25)
                if load.returncode:raise RuntimeError('Display module: '+error.strip())
                break
            except subprocess.TimeoutExpired:pass
        else:raise RuntimeError('Display module load timeout')
        result=module/'parameters/result';lease=module/'parameters/lease_token'
        while True:
            heartbeat()
            st=hw.status()
            if st['cc']!=1 or not st['vbus']:reason='detached';break
            if not Path('/etc/omarchy-dock-enabled').exists():reason='disabled';break
            if int(result.read_text())!=-115:raise RuntimeError('Kernel session ended: '+result.read_text().strip())
            token=(token+1)&0xffffffff
            if not Path('/run/omarchy-dock-test-expire-lease').exists():lease.write_text(str(token))
            if process is None:
                cards=[p.name for p in Path('/sys/class/drm').glob('card[0-9]') if 's9p-frame-lab.' in str(p.resolve())]
                if len(cards)==1:
                    with open('/run/omarchy-dock-launch.log','a') as log:
                        process=subprocess.Popen(['python3','/usr/local/lib/omarchy-dock/dock-launch.py',cards[0],launch_id],stdout=log,stderr=log,start_new_session=True)
                elif time.monotonic()-start>8:raise RuntimeError('External DRM node timeout')
            if process:
                if logout_requested(launch_id):reason='logout';break
                if process.poll() is not None:raise RuntimeError('Desktop session exited: '+str(process.returncode))
                ready=session_ready(launch_id)
                if not ready and time.monotonic()-start>35:raise RuntimeError('Desktop readiness timeout')
                publish('running' if ready else 'starting',pid=process.pid,retained_buffers=int((module/'parameters/retained_buffers').read_text()))
            time.sleep(.5)
        return {'reason':reason,'seconds':round(time.monotonic()-start,1)}
    finally:
        # Stop clients before unplugging their DRM device, while continuing the
        # separate USB watchdog heartbeat. Input wrapper restores the ACL lease.
        if process and process.poll() is None:
            process.terminate()
            deadline=time.monotonic()+8
            while process.poll() is None and time.monotonic()<deadline:
                heartbeat();time.sleep(.2)
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=2)
        if module.exists():
            (module/'parameters/stop_requested').write_text('1')
            deadline=time.monotonic()+5
            while int((module/'parameters/result').read_text())==-115:
                heartbeat()
                if time.monotonic()>deadline:raise RuntimeError('Display stop acknowledgment timeout')
                time.sleep(.2)
        deadline=time.monotonic()+8
        while module.exists():
            heartbeat()
            cleanup=subprocess.Popen(['/usr/bin/rmmod','s9p_dp_pll_lab'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            while cleanup.poll() is None and time.monotonic()<deadline:
                heartbeat();time.sleep(.2)
            if cleanup.poll() is None:raise RuntimeError('Display removal timeout')
            error=cleanup.stderr.read()
            if not cleanup.returncode:break
            if time.monotonic()>=deadline:raise RuntimeError('Display removal failed: '+error.strip())
            time.sleep(.2)
        if load.poll() is None:load.terminate();load.wait(timeout=2)
        publish('stopped',reason=reason,cleaned=not module.exists())
