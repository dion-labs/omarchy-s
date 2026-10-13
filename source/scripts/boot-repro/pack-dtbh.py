#!/usr/bin/env python3
"""Narrow S9+ DTBH reconstruction from a pinned DTB and measured format profile.
Written from binary layout observations and the public FDT header specification;
not a general dtbtool replacement. No upstream dtbtool code is included.
"""
import argparse,hashlib,json,struct
from pathlib import Path

def pack(data,profile):
    if profile['schema']!=1 or profile['format']!='s9-single-dtbh-v2':raise ValueError('Unsupported profile')
    if hashlib.sha256(data).hexdigest()!=profile['dtb_sha256']:raise ValueError('Unrecognized DTB')
    if len(data)<40:raise ValueError('Truncated FDT header')
    magic,total,off_struct,off_strings,off_reserved,version,last,boot,strings_size,struct_size=struct.unpack_from('>10I',data)
    if magic!=0xd00dfeed or total!=len(data) or version!=17 or last!=16:raise ValueError('Unsupported FDT header')
    if off_struct%4 or off_reserved%8 or not 40<=off_reserved<off_struct or not off_struct+struct_size<=off_strings or off_strings+strings_size>total:raise ValueError('Invalid FDT bounds')
    if profile['alignment']!=2048:raise ValueError('Unsupported alignment')
    entry=profile['entry_prefix_words']
    if len(entry)!=5 or any(type(v)!=int or not 0<=v<=0xffffffff for v in entry):raise ValueError('Invalid entry metadata')
    size=((len(data)+2047)//2048)*2048
    if size>0xffffffff:raise ValueError('DTB too large')
    # Five measured selection words, payload offset/extent, final observed word.
    header=struct.pack('<4s10I',b'DTBH',2,1,*entry,2048,size,profile['entry_final_word'])
    return header+bytes(2048-len(header))+data+bytes(size-len(data))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dtb',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    profile=json.loads(a.profile.read_text());result=pack(a.dtb.read_bytes(),profile)
    if hashlib.sha256(result).hexdigest()!=profile['expected_dtbh_sha256']:raise ValueError('DTBH output mismatch')
    with a.output.open('xb') as f:f.write(result)
    print(json.dumps({'bytes':len(result),'sha256':hashlib.sha256(result).hexdigest(),'profile':'s9-single-dtbh-v2'}))
if __name__=='__main__':main()
