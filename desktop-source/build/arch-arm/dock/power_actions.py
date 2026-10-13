"""Fixed native actions; desktop logout never terminates the handset session."""
ACTIONS={
 'logout':('End desktop session?', 'Save your work first. External desktop apps will close. The phone interface stays running.', 'End desktop session'),
 'reboot':('Restart phone?', 'Save your work first. This restarts the whole phone and closes both phone and desktop apps.', 'Restart phone'),
 'poweroff':('Shut down phone?', 'Save your work first. This shuts down the whole phone and closes both phone and desktop apps.', 'Shut down phone'),
}
def command(action):
 if action not in ACTIONS:raise ValueError('Unsupported power action')
 if action=='logout':return None
 return ['/usr/bin/sudo','-n','/usr/bin/systemctl',action]
