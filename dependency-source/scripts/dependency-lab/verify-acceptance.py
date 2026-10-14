#!/usr/bin/env python3
"""Offline saved-evidence verification and comparison; not execution attestation."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('acceptance_runner',HERE/'run-acceptance.py');runner=importlib.util.module_from_spec(s);s.loader.exec_module(runner)
ROOT=HERE.parents[1]

def read_regular(path):
 if path.is_symlink() or not path.is_file():raise ValueError('Missing or linked evidence: '+path.name)
 return path.read_bytes()
def parse(raw):
 def unique(pairs):
  value={}
  for key,item in pairs:
   if key in value:raise ValueError('Duplicate JSON key')
   value[key]=item
  return value
 return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Non-finite JSON')))

def verify(root,evidence,manifest,manifest_hash,builder,stage,receipt_hash):
 raw=read_regular(evidence/'acceptance.json')
 if runner.sha(raw)!=receipt_hash:raise ValueError('Acceptance receipt hash differs')
 report=parse(raw)
 if type(report.get('schema')) is not int or report['schema'] not in (1,2) or report.get('status')!='passed':raise ValueError('Not a completed supported acceptance')
 if report.get('phone_contacted') is not False or report.get('production_updater_enabled') is not False:raise ValueError('Unexpected acceptance scope')
 if 'error' in report or 'error_type' in report or 'cleanup_error' in report:raise ValueError('Receipt contains an error')
 if report['schema']==2 and not re.fullmatch('[0-9a-f]{32}',report.get('run_id','')):raise ValueError('Invalid run identity')
 elapsed=report.get('elapsed_seconds')
 if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0:raise ValueError('Invalid duration')
 count=runner.verify_tree(root,manifest,manifest_hash)
 if type(report.get('source_files')) is not int or report['source_files']!=count or report.get('manifest_sha256')!=manifest_hash:raise ValueError('Source receipt differs')
 build_raw=read_regular(builder);build=parse(build_raw);lock=read_regular(root/'packaging/portal-frontend-lab.lock.json')
 if build.get('lock_sha256')!=runner.sha(lock) or not re.fullmatch('sha256:[0-9a-f]{64}',build.get('image_id','')):raise ValueError('Builder identity differs')
 binary=read_regular(stage/'usr/local/lib/omarchy-dock/portal-wlr')
 runtime=dict(image_id=build['image_id'],builder_receipt_sha256=runner.sha(build_raw),frontend_lock_sha256=runner.sha(lock),portal_sha256=runner.sha(binary))
 if runtime['portal_sha256']!=runner.PIN or report.get('runtime')!=runtime:raise ValueError('Runtime evidence differs')
 cases=[(n,c,'linux') for n,c in runner.CASES]+[(*runner.HOST,'host')]
 expected_names={'acceptance.json','linux.log','host.log'}|{'case-'+str(i)+'.json' for i in range(len(cases))}
 if any(p.is_symlink() or not p.is_file() for p in evidence.iterdir()) or {p.name for p in evidence.iterdir()}!=expected_names:raise ValueError('Evidence membership differs')
 if set(report.get('logs',{}))!={'linux.log','host.log'} or set(report.get('case_artifacts',{}))!=expected_names-{'acceptance.json','linux.log','host.log'}:raise ValueError('Incomplete artifact inventory')
 for group in ('logs','case_artifacts'):
  for name,digest in report[group].items():
   if runner.sha(read_regular(evidence/name))!=digest:raise ValueError('Artifact hash differs: '+name)
 checked=[]
 for i,(name,n,platform) in enumerate(cases):
  result=runner.validate_result(parse(read_regular(evidence/('case-'+str(i)+'.json'))),n)
  checked.append(dict(file=name,platform=platform,**result))
 if report.get('cases')!=checked:raise ValueError('Summary/case evidence mismatch')
 totals=dict(tests=sum(c for _,c,_ in cases),linux_tests=sum(c for _,c in runner.CASES),host_tests=runner.HOST[1])
 if any(type(report.get(k)) is not int or report[k]!=v for k,v in totals.items()):raise ValueError('Test totals differ')
 return dict(verified=True,receipt_sha256=receipt_hash,manifest_sha256=manifest_hash,runtime=runtime,cases=checked,run_id=report.get('run_id'),**totals)

def compare(first,second):
 if first['receipt_sha256']==second['receipt_sha256'] or (first.get('run_id') and first['run_id']==second.get('run_id')):raise ValueError('Same run cannot establish independent reproduction')
 fields=('manifest_sha256','runtime','cases','tests','linux_tests','host_tests')
 differences=[key for key in fields if first[key]!=second[key]]
 return dict(equivalent=not differences,differences=differences,run_ids=[first.get('run_id'),second.get('run_id')],
  limitation='Distinct declared runs and matching evidence do not authenticate execution or prove host independence')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('evidence','manifest','builder-receipt','stage'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--manifest-sha256',required=True);p.add_argument('--receipt-sha256',required=True)
 p.add_argument('--compare',type=Path);p.add_argument('--compare-receipt-sha256');args=p.parse_args()
 if bool(args.compare)!=bool(args.compare_receipt_sha256):p.error('Comparison directory and receipt hash must be supplied together')
 first=verify(ROOT,args.evidence,args.manifest,args.manifest_sha256,args.builder_receipt,args.stage,args.receipt_sha256)
 result={'verification':first,'limitation':'Offline consistency check; receipt hashes must come from a trusted source. No Docker/device contact.'}
 if args.compare:
  second=verify(ROOT,args.compare,args.manifest,args.manifest_sha256,args.builder_receipt,args.stage,args.compare_receipt_sha256);result['comparison']=compare(first,second)
 print(json.dumps(result,indent=2))
 if args.compare and not result['comparison']['equivalent']:raise SystemExit(1)
if __name__=='__main__':main()
