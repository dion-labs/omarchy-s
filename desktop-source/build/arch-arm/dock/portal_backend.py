"""Start the verified private portal inside the separate dock session only."""
import hashlib,json,os,subprocess,time
from pathlib import Path

def start():
    assert os.geteuid()==1000 and os.environ.get('XDG_RUNTIME_DIR')=='/trial/run'
    assert os.environ.get('HOME')=='/trial/home'
    if os.environ.get('S9P_SCREENCAST_TEST')=='stock':return {'private_backend':False}
    base=Path('/usr/local/lib/omarchy-dock')
    if os.environ.get('S9P_VIRTUAL_DRM') and Path('/trial/portal-wlr').is_file():
        base=Path('/trial')
    elif not Path('/etc/omarchy-desktop-portal-compat').exists():
        return {'private_backend':False}
    binary=base/'portal-wlr';manifest=json.loads((base/'portal-manifest.json').read_text())
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==manifest['binary_sha256'],'Portal binary hash mismatch'
    bus=['gdbus','call','--session','--dest','org.freedesktop.DBus','--object-path','/org/freedesktop/DBus']
    def owner():
        return 'true' in subprocess.check_output(bus+['--method','org.freedesktop.DBus.NameHasOwner','org.freedesktop.impl.portal.desktop.wlr'],text=True,timeout=3)
    if not owner():
        with open('/trial/portal-wlr.log','a') as log:
            child=subprocess.Popen([str(binary),'-l','INFO'],stdout=log,stderr=log)
        end=time.monotonic()+4
        while not owner():
            assert child.poll() is None,'Private portal exited'
            if time.monotonic()>end:raise TimeoutError('Private portal did not acquire its bus name')
            time.sleep(.1)
    # A repeated setup must never replace another backend or interrupt sharing.
    pid_text=subprocess.check_output(bus+['--method','org.freedesktop.DBus.GetConnectionUnixProcessID','org.freedesktop.impl.portal.desktop.wlr'],text=True,timeout=3)
    import re
    pid=int(re.search(r'uint32 (\d+)',pid_text)[1])
    assert (Path('/proc')/str(pid)/'exe').resolve()==binary.resolve(),'Another portal owns this private bus'
    return {'private_backend':True,'version':manifest['version'],'pid':pid}
