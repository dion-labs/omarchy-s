#!/usr/bin/env python3
"""Replay pinned BusyBox signature and Ubuntu build provenance checks, offline."""
import argparse,hashlib,json,lzma,re,subprocess
from pathlib import Path
from toolchain import ROOT,resolve

def fields(text):
 result={};key=None
 for line in text.splitlines():
  if line.startswith((' ','\t')) and key:result[key]+='\n'+line.strip()
  elif ': ' in line or line.endswith(':'):
   key,_,v=line.partition(':');result[key]=v.strip()
 return result

def checks(text,key):
 return {name:(digest,int(size)) for digest,size,name in (line.split() for line in fields(text)[key].splitlines() if line.strip())}

def match(data,pair):
 if (hashlib.sha256(data).hexdigest(),len(data))!=pair:raise ValueError('Checksum/size mismatch')

def one(text,package,version):
 rows=[fields(b) for b in text.split('\n\n') if fields(b).get('Package')==package and fields(b).get('Version')==version]
 if len(rows)!=1:raise ValueError('Ambiguous/missing package record')
 return rows[0]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--sources',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 lock=json.loads((ROOT/'packaging/busybox-trust.lock.json').read_text());r=a.evidence.resolve();src=a.sources.resolve()
 for name,h in lock['evidence'].items():
  if hashlib.sha256((r/name).read_bytes()).hexdigest()!=h:raise ValueError('Evidence changed: '+name)
 image,_=resolve(lock['image_id']);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 results={}
 for label,key,sig,data in [('archive','archive','/e/InRelease',None),('dsc','uploader','/s/busybox_1.36.1-6ubuntu3.1.dsc',None),('upstream','upstream','/s/busybox_1.36.1.orig.tar.bz2.asc','/s/busybox_1.36.1.orig.tar.bz2')]:
  cmd=['docker','run','--rm','--network','none','--cap-drop','ALL','-v',str(r)+':/e:ro','-v',str(src)+':/s:ro',image,'gpgv','--homedir','/tmp','--status-fd','1','--keyring','/e/'+('archive-keyring.gpg' if key=='archive' else key+'-key.gpg'),sig]
  if data:cmd.append(data)
  proc=subprocess.run(cmd,capture_output=True,text=True);(out/(label+'-status.txt')).write_text(proc.stdout);(out/(label+'-diagnostic.txt')).write_text(proc.stderr)
  fingerprints=re.findall(r'^\[GNUPG:\] VALIDSIG ([A-F0-9]+) ',proc.stdout,re.M)
  if proc.returncode or fingerprints!=[lock['fingerprints'][label]]:raise ValueError('Signature/fingerprint failure: '+label)
  results[label]=fingerprints[0]
 published=json.loads((r/'published.json').read_text());keys=json.loads((r/'signer-keys.json').read_text())
 if lock['fingerprints']['dsc'] not in [x['fingerprint'] for x in keys['entries']]:raise ValueError('Signer attribution mismatch')
 if not any(e['package_signer_link']==lock['uploader_profile'] for e in published['entries']):raise ValueError('Source signer mismatch')
 release=(r/'InRelease').read_text();sums=checks(release,'SHA256')
 for file,index in [('main_binary-arm64_Packages.xz','main/binary-arm64/Packages.xz'),('main_source_Sources.xz','main/source/Sources.xz')]:match((r/file).read_bytes(),sums[index])
 version='1:1.36.1-6ubuntu3.1'
 binary=one(lzma.decompress((r/'main_binary-arm64_Packages.xz').read_bytes()).decode(),'busybox-static',version)
 match(a.binary.read_bytes(),(binary['SHA256'],int(binary['Size'])))
 source=one(lzma.decompress((r/'main_source_Sources.xz').read_bytes()).decode(),'busybox',version)
 sourcehashes=checks('\n'.join(k+': '+v for k,v in source.items()),'Checksums-Sha256')
 for name,pair in sourcehashes.items():match((src/name).read_bytes(),pair)
 dsc=checks((src/'busybox_1.36.1-6ubuntu3.1.dsc').read_text(),'Checksums-Sha256')
 for name,pair in dsc.items():match((src/name).read_bytes(),pair)
 build=next(x for x in json.loads((r/'builds.json').read_text())['entries'] if x['arch_tag']=='arm64' and x['source_package_version']==version)
 info=(r/'buildinfo_url').read_text();changes=(r/'changesfile_url').read_text();filename=Path(binary['Filename']).name
 for record in [info,changes]:match(a.binary.read_bytes(),checks(record,'Checksums-Sha256')[filename])
 meta=fields(info)
 if meta['Source']!='busybox' or meta['Version']!=version or meta['Architecture']!='arm64':raise ValueError('Wrong buildinfo identity')
 report={'signatures_verified':results,'archive_date':fields(release).get('Date'),'archive_valid_until':fields(release).get('Valid-Until'),'scope':'Authentic pinned historical snapshot; not an automatic update freshness check','signed_archive_source_and_binary_hashes_match':True,'ubuntu_build':build['web_link'],'build_path':meta['Build-Path'],'build_environment':meta['Environment'],'installed_build_depends':meta['Installed-Build-Depends'],'buildinfo_and_changes':'Unsigned records retrieved from official Launchpad HTTPS; binary hashes match signed archive','upstream_signature':'Legacy DSA/SHA1; also bound by signed Ubuntu SHA256 source index','device_contacted':False,'binary_reproduction_claimed':False}
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='installed_build_depends'},indent=2))
if __name__=='__main__':main()
