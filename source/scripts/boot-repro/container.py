"""Strict parser/repacker for this project's legacy Samsung Android boot layout."""
import hashlib
import struct
TRAILER=b'SEANDROIDENFORCE'
def ident(parts):
    h=hashlib.sha1()
    for i,data in enumerate(parts):
        if i==3 and not data: continue
        h.update(data); h.update(struct.pack('<I',len(data)))
    return h.digest().ljust(32,b'\0')
def parse(data,check_id=True,require_trailer=True):
    if len(data)<1632 or data[:8]!=b'ANDROID!': raise ValueError('Invalid boot header')
    page=struct.unpack_from('<I',data,36)[0]
    if page not in (2048,4096): raise ValueError('Unsupported page size')
    parts=[]; pos=page
    for field in (8,16,24,40):
        n=struct.unpack_from('<I',data,field)[0]
        end=pos+n; aligned=pos+(n+page-1)//page*page
        if aligned>len(data): raise ValueError('Truncated section')
        if any(data[end:aligned]): raise ValueError('Nonzero section padding')
        parts.append(data[pos:end]);pos=aligned
    if require_trailer and data[pos:pos+len(TRAILER)]!=TRAILER: raise ValueError('Missing Samsung trailer')
    if check_id and data[576:608]!=ident(parts): raise ValueError('Invalid image ID')
    return page,parts,pos+len(TRAILER)
def pack(reference,loader):
    page,parts,_=parse(reference,check_id=False,require_trailer=False)
    if parts[2] or not parts[3].startswith(b'DTBH'): raise ValueError('Unexpected reference layout')
    ram=bytes.fromhex('1f8b08000000000002ff0300000000000000000000')
    new=[loader,ram,b'',parts[3]]
    head=bytearray(reference[:page])
    for field,data in zip((8,16,24,40),new): struct.pack_into('<I',head,field,len(data))
    head[64:576]=b'console=tty0'.ljust(512,b'\0');head[608:1632]=bytes(1024)
    head[576:608]=ident(new)
    result=bytes(head)+b''.join(d+bytes((-len(d))%page) for d in new)+TRAILER
    parse(result)
    return result
