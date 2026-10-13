"""Private Mesa selection shared by real and disposable desktop sessions."""
from pathlib import Path
PREFIX = '/opt/omarchy-mesa-cache/lib'
FLAG = 'OMARCHY_PANFROST_CPU_INVALIDATE'

def configure(env, enabled=False, aquamarine=False):
    env = env.copy()
    paths = []
    if enabled:
        assert Path(PREFIX + '/libgallium-26.2.3-omarchy-cache1.so').is_file()
        paths.append(PREFIX)
        env[FLAG] = '1'
    if aquamarine:
        paths.append('/trial/lib')
    if env.get('LD_LIBRARY_PATH'):
        paths.extend(env['LD_LIBRARY_PATH'].split(':'))
    if paths:
        env['LD_LIBRARY_PATH'] = ':'.join(dict.fromkeys(paths))
    return env

def verify(pid):
    paths = sorted({line.split()[-1] for line in Path(f'/proc/{pid}/maps').read_text().splitlines()
                    if PREFIX + '/' in line})
    assert any('libgallium-26.2.3-omarchy-cache1.so' in p for p in paths), paths
    assert any('/libEGL.so' in p for p in paths), paths
    return paths
