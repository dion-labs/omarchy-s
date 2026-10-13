"""Small bounded desktop launch protocol. URLs are arguments, never shell code."""
import json
from urllib.parse import urlsplit
LIMIT=8192

def browser_url(value):
 if not isinstance(value,str) or len(value.encode('utf-8'))>LIMIT-100:
  raise ValueError('Invalid URL size')
 if value=='about:blank':return value
 if any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError('Control character in URL')
 parts=urlsplit(value)
 if parts.scheme not in ('http','https') or not parts.hostname:raise ValueError('Only HTTP(S) links are supported')
 return value

def encode(url='about:blank'):
 return json.dumps({'app':'browser','url':browser_url(url)},ensure_ascii=False).encode()+b'\n'

def receive(conn):
 data=b''
 while b'\n' not in data:
  chunk=conn.recv(1024)
  if not chunk:raise ValueError('Incomplete request')
  data+=chunk
  if len(data)>LIMIT:raise ValueError('Request too large')
 if data.count(b'\n')!=1 or not data.endswith(b'\n'):raise ValueError('Multiple requests')
 request=json.loads(data)
 if request=={'app':'terminal'}:return 'terminal'
 if isinstance(request,dict) and set(request)=={'app','action'} and request['app']=='power':
  from power_actions import command
  command(request['action'])
  return ('power',request['action'])
 if not isinstance(request,dict) or set(request)!= {'app','url'} or request['app']!='browser':raise ValueError('Unsupported application')
 return browser_url(request['url'])
