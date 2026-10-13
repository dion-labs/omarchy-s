#!/usr/bin/env python3
"""Request a dock app and report bounded dispatch failures without URL disclosure."""
import json,os,socket,subprocess,sys
from pathlib import Path
from app_protocol import encode

def send_request(endpoint,request):
 with socket.socket(socket.AF_UNIX) as connection:
  connection.settimeout(5);connection.connect(str(endpoint));connection.sendall(request)
  # Replies may arrive fragmented; EOF terminates the broker's single response.
  response=b''
  while True:
   part=connection.recv(1024)
   if not part:break
   response+=part
   if len(response)>1024:raise RuntimeError('Invalid launcher response')
  if response!=b'ok':raise RuntimeError('Launch request failed')

def endpoint_for(env):
 if env.get('HOME')=='/trial/home':return Path('/trial/run/app-launch.sock')
 if env.get('HOME')!='/home/omarchy/Dock':raise RuntimeError('Not a dock application')
 remote=Path(Path('/run/omarchy-dock-session').read_text().strip())
 if remote.parent!=Path('/var/tmp') or not remote.name.startswith('hyprland-headless-dock-'):raise RuntimeError('Invalid dock session')
 if env.get('XDG_RUNTIME_DIR')!=str(remote/'run') or (remote/'stopped.json').exists():raise RuntimeError('Dock is unavailable')
 return remote/'run/app-launch.sock'

def notify_failure(app):
 title={'browser':'Browser could not open','terminal':'Terminal could not open','power':'System menu could not open'}.get(app,'Application could not open')
 message='Check that the desktop is connected, then try again.'
 if app=='browser':message+=' If the browser keeps failing, close it normally and use the software fallback. See Browser recovery in Projects/phone-lab.'
 try:
  subprocess.run(['notify-send','--app-name=Omarchy',title,message],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3,check=False)
 except (OSError,subprocess.TimeoutExpired):pass
 # Fixed text only: never forward a broker exception, URL or profile path.
 print(title+'. '+message,file=sys.stderr)

def main(argv=None):
 args=sys.argv[1:] if argv is None else argv
 app=args[0] if args else ''
 try:
  if args==['terminal']:request=b'{"app":"terminal"}\n'
  elif len(args)==2 and app=='power':
   from power_actions import command
   command(args[1]);request=json.dumps({'app':'power','action':args[1]}).encode()+b'\n'
  elif len(args) in (1,2) and app=='browser':request=encode(args[1] if len(args)==2 else 'about:blank')
  else:raise ValueError('Unsupported request')
  send_request(endpoint_for(os.environ),request)
  return 0
 except (OSError,ValueError,RuntimeError):
  notify_failure(app);return 1
if __name__=='__main__':raise SystemExit(main())
