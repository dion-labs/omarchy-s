#!/usr/bin/env python3
"""Fetch only pinned public package archives; never install them."""
import concurrent.futures,hashlib,json,sys,urllib.request
from pathlib import Path
lock=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
def fetch(item):
 if not item['url'].startswith('https://'):raise ValueError('Only explicit HTTPS package URLs are accepted')
 name=item['filename']
 if not name or Path(name).name!=name or name in ('.','..') or '\\' in name:raise ValueError('Unsafe filename')
 target=out/name;algorithm=item['algorithm'];expected=item['digest']
 def valid(p):return p.is_file() and hashlib.new(algorithm,p.read_bytes()).hexdigest()==expected
 if valid(target):return {'name':item['name'],'status':'cached'}
 temp=target.with_suffix(target.suffix+'.partial')
 try:
  with urllib.request.urlopen(item['url'],timeout=60) as response, temp.open('wb') as f:
   while chunk:=response.read(1024*1024):f.write(chunk)
  if not valid(temp):raise ValueError('Hash mismatch')
  temp.replace(target);return {'name':item['name'],'status':'fetched'}
 except Exception as e:
  temp.unlink(missing_ok=True);return {'name':item['name'],'status':'failed','error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(fetch,lock['packages']+lock.get('supplemental',[])))
(out/'fetch-result.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'total':len(results),'failed':[r for r in results if r['status']=='failed']}),flush=True)
raise SystemExit(any(r['status']=='failed' for r in results))
