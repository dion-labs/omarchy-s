#!/usr/bin/env python3
"""Single-owner USB attachment service for explicitly pinned S9+ boot profiles."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time
from usb_hardware import Hardware
from dock_service import acquire_display_lock, DockPolicy, session as dock_session, publish as dock_publish

BOOT_PROFILES = {
    '#16 SMP': '728d764bae142f221848ccf73418b3a094188d4bf30b6e070d6eb6e8a9e40815',
    '#17 SMP': '0cfe7163d71e409d215b9c822ebcb7c66b86d522df5f157b04a8e4864c7b24a4',
}

def validate_kernel_profile(version, boot_digest):
    matches = [digest for tag, digest in BOOT_PROFILES.items() if tag in version]
    if len(matches) != 1 or matches[0] != boot_digest:
        raise RuntimeError('Kernel and BOOT do not match an approved profile')


class Policy:
    def __init__(self):
        self.host=False
        self.since=None
    def decide(self, now, cc, vbus, capacity):
        if self.host:
            if cc!=2 or capacity<5:
                self.host=False; self.since=None
                return 'stop'
            return 'hold'
        if cc!=2 or vbus or capacity<5:
            self.since=None
            return 'idle'
        if self.since is None: self.since=now
        if now-self.since>=.2:
            self.host=True
            return 'start'
        return 'idle'

def emit(event, **fields):
    record=dict(event=event,uptime=time.monotonic(),pid=os.getpid(),**fields)
    print(json.dumps(record),flush=True)
    p=Path('/run/omarchy-usb.json.tmp');p.write_text(json.dumps(record)+'\n');p.replace('/run/omarchy-usb.json')

def watchdog(hw):
    rd,wr=os.pipe(); parent=os.getpid();pid=os.fork()
    if pid==0:
        os.close(wr)
        for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP): signal.signal(sig,signal.SIG_DFL)
        try:
            while True:
                ready,_,_=select.select([rd],[],[],10)
                message=os.read(rd,1) if ready else b''
                if message==b'.': continue
                if message!=b'1':
                    hw.power_off()
                    try:
                        if not ready: os.kill(parent,signal.SIGTERM)
                    except ProcessLookupError: pass
                break
        finally: os._exit(0)
    os.close(rd)
    return pid,wr

def usb_devices():
    devices=[]
    for d in Path('/sys/bus/usb/devices').glob('*'):
        try:
            vid=(d/'idVendor').read_text().strip();pid=(d/'idProduct').read_text().strip()
            if vid!='1d6b': devices.append(vid+':'+pid)
        except FileNotFoundError: pass
    return sorted(devices)

def display_aux_probe(train=False, pattern_seconds=0, heartbeat=lambda: None, decon=False, drm=False, half_rate=False):
    """Bounded diagnostic; retain mailbox ownership and watchdog heartbeat."""
    args=['/usr/bin/insmod','/var/tmp/s9p-dp-pll-lab.ko','aux_test=1',
          'train='+str(int(train)),'pattern_seconds='+str(pattern_seconds),'decon_test='+str(int(decon)),'drm_test='+str(int(drm)),'half_rate='+str(int(half_rate))]
    process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    deadline=time.monotonic()+pattern_seconds+5
    try:
        while True:
            heartbeat()
            try:
                _,stderr=process.communicate(timeout=.5)
                break
            except subprocess.TimeoutExpired:
                if time.monotonic()>deadline:
                    raise RuntimeError('Display lab exceeded bounded duration')
        probe_code=process.returncode
        if process.returncode == 0:
            if drm:
                result_path=Path('/sys/module/s9p_dp_pll_lab/parameters/result')
                while int(result_path.read_text()) == -115:
                    heartbeat()
                    if time.monotonic()>deadline:
                        raise RuntimeError('DRM lab exceeded bounded duration')
                    time.sleep(.25)
                result=int(result_path.read_text())
                probe_code=result
                if result: stderr+=' kernel result='+str(result)
            subprocess.run(['/usr/bin/rmmod','s9p_dp_pll_lab'],check=True,timeout=2)
        return dict(returncode=probe_code,stderr=stderr.strip())
    finally:
        if drm and Path('/sys/module/s9p_dp_pll_lab').exists():
            subprocess.run(['/usr/bin/rmmod','s9p_dp_pll_lab'],check=True,timeout=8)
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def main():
    if os.geteuid()!=0: raise RuntimeError('Root required')
    if Path('/proc/device-tree/model').read_text().rstrip('\0')!='Samsung Galaxy S9+ (SM-G965F)':
        raise RuntimeError('Wrong device')
    # Same lock as the lab runner: diagnostics and service cannot share hardware.
    lock=open('/var/tmp/omarchy-usb-lab.lock','a')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise RuntimeError('USB owner already active')
    validate_kernel_profile(Path('/proc/version').read_text(),
                            hashlib.sha256(Path('/dev/sda10').read_bytes()).hexdigest())
    def stop(*_): raise SystemExit(0)
    for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP): signal.signal(sig,stop)
    hw=Hardware();pid,pipe=watchdog(hw);clean=False
    try:
        hw.acquire()
        policy=Policy(); docking=DockPolicy(); previous=None;last_emit=0;heartbeat=0;last_sink=None
        emit('started')
        while True:
            now=time.monotonic()
            if now-heartbeat>=1: os.write(pipe,b'.');heartbeat=now
            st=hw.status()
            if Path('/run/omarchy-usb-observe-display').exists():
                events=hw.display_events()
                if events['pd_interrupt'] or events['vdm_interrupt']:
                    with open('/run/omarchy-display-events.jsonl','a') as output:
                        output.write(json.dumps(dict(uptime=now,connector=st,**events))+'\n')
            capture=Path('/run/omarchy-usb-read-display-cache')
            if capture.exists():
                capture.unlink()
                records=hw.display_cache()
                Path('/run/omarchy-display-cache.json').write_text(json.dumps(dict(uptime=now,connector=st,records=records))+'\n')
            enter_test=Path('/run/omarchy-usb-test-display-enter')
            if enter_test.exists():
                enter_test.unlink()
                result=hw.display_enter_test()
                Path('/run/omarchy-display-enter.json').write_text(json.dumps(dict(uptime=now,**result))+'\n')
            configure_test=Path('/run/omarchy-usb-test-display-configure')
            if configure_test.exists():
                configure_test.unlink()
                result=hw.display_enter_test(configure=True)
                Path('/run/omarchy-display-configure.json').write_text(json.dumps(dict(uptime=now,**result))+'\n')
            aux_test=Path('/run/omarchy-usb-test-display-aux')
            if aux_test.exists():
                aux_test.unlink()
                result=hw.display_enter_test(configure=True,probe=display_aux_probe)
                Path('/run/omarchy-display-aux.json').write_text(json.dumps(dict(uptime=now,**result))+'\n')
            training_test=Path('/run/omarchy-usb-test-display-training')
            if training_test.exists():
                training_test.unlink()
                result=hw.display_enter_test(configure=True,probe=lambda: display_aux_probe(True))
                Path('/run/omarchy-display-training.json').write_text(json.dumps(dict(uptime=now,**result))+'\n')
            pattern_test=Path('/run/omarchy-usb-test-display-pattern')
            if pattern_test.exists():
                pattern_test.unlink()
                result=hw.display_enter_test(configure=True,
                    probe=lambda: display_aux_probe(True,180,lambda: os.write(pipe,b'.')))
                Path('/run/omarchy-display-pattern.json').write_text(json.dumps(dict(uptime=now,**result))+'\n')
            decon_test=Path('/run/omarchy-usb-test-display-decon')
            if decon_test.exists():
                decon_test.unlink()
                result=hw.display_enter_test(configure=True,
                    probe=lambda: display_aux_probe(True,10,lambda: os.write(pipe,b'.'),decon=True))
                Path('/run/omarchy-display-decon.json').write_text(json.dumps(dict(uptime=now,**result))+'\n')
            half_test=Path('/run/omarchy-usb-test-display-half')
            if half_test.exists():
                half_test.unlink()
                result=hw.display_enter_test(configure=True,
                    probe=lambda: display_aux_probe(True,10,lambda: os.write(pipe,b'.'),decon=True,half_rate=True))
                Path('/run/omarchy-display-half.json').write_text(json.dumps(dict(uptime=now,**result))+'\n')
            drm_test=Path('/run/omarchy-usb-test-display-drm')
            if drm_test.exists():
                drm_test.unlink()
                result=hw.display_enter_test(configure=True,
                    probe=lambda: display_aux_probe(True,60,lambda: os.write(pipe,b'.'),decon=True,drm=True))
                Path('/run/omarchy-display-drm.json').write_text(json.dumps(dict(uptime=now,**result))+'\n')
            preview_test=Path('/run/omarchy-usb-test-display-drm-preview')
            if preview_test.exists():
                preview_test.unlink()
                result=hw.display_enter_test(configure=True,
                    probe=lambda: display_aux_probe(True,180,lambda: os.write(pipe,b'.'),decon=True,drm=True))
                Path('/run/omarchy-display-drm-preview.json').write_text(json.dumps(dict(uptime=now,**result))+'\n')
            if docking.decide(now,st['cc']==1 and st['vbus'],Path('/etc/omarchy-dock-enabled').exists()):
                display_lock=acquire_display_lock()
                if display_lock is None:
                    docking=DockPolicy()  # Retry after the lab releases ownership.
                else:
                    try:
                        discovered=hw.prepare_display_discovery(lambda:os.write(pipe,b'.'))
                        Path('/run/omarchy-dock-discovery.json').write_text(json.dumps(dict(uptime=time.monotonic(),**discovered))+'\n')
                        dock_result=hw.display_enter_test(configure=True,detach_ok=True,
                            probe=lambda:dock_session(hw,lambda:os.write(pipe,b'.')))
                        if dock_result.get('probe',{}).get('reason')=='detached':docking=DockPolicy()
                    except Exception as error:
                        dock_publish('failed',error=str(error))
                        # No retry until physical detach or explicit service restart.
                        # A loaded module means cleanup is uncertain: stop ownership.
                        if Path('/sys/module/s9p_dp_pll_lab').exists():raise
                    finally:
                        display_lock.close()
                st=hw.status();now=time.monotonic()
            capacity=int(Path('/sys/class/power_supply/max170xx_battery/capacity').read_text())
            action=policy.decide(now,st['cc'],st['vbus'],capacity)
            if action=='start': hw.start_host()
            elif action=='stop': hw.stop_host()
            elif action=='idle' and st['cc']==1 and st['vbus'] and last_sink!=(st['cc'],st['vbus']): hw.path_usb(require_usb=False)
            last_sink=(st['cc'],st['vbus'])
            if policy.host and hw.power_read(0xb7)!=((hw.original[0xb7]&~1)|0x0a):
                raise RuntimeError('Host power changed; no automatic retry')
            devices=usb_devices()
            state=(policy.host,st['cc'],st['vbus'],tuple(devices))
            if state!=previous or now-last_emit>=30:
                emit('host' if policy.host else 'device',cc=st['cc'],vbus=st['vbus'],capacity=capacity,devices=devices)
                previous=state;last_emit=now
            time.sleep(.05)
    finally:
        try:
            hw.close();clean=True
        finally:
            if clean: os.write(pipe,b'1')
            os.close(pipe);os.waitpid(pid,0)
            emit('stopped' if clean else 'recovery-required')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        emit('failed',error=str(exc))
        raise
