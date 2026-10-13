"""Native20 legacy Samsung container from explicit fields and source-built DTBH."""
import struct
from container import ident,parse,TRAILER

def build(loader,dtbh):
    if len(dtbh)<44 or dtbh[:4]!=b'DTBH':raise ValueError('Invalid DTBH')
    magic,version,count=struct.unpack_from('<4sII',dtbh)
    if version!=2 or count!=1:raise ValueError('Unexpected DTBH variant')
    chip,platform,subtype,rev,end,offset,size,space=struct.unpack_from('<8I',dtbh,12)
    if (chip,platform,subtype,rev,end,offset,space)!=(9810,20646,561349850,26,255,2048,32):raise ValueError('Unexpected board metadata')
    if offset+size!=len(dtbh) or dtbh[offset:offset+4]!=b'\xd0\x0d\xfe\xed':raise ValueError('Invalid DTBH bounds')
    page=2048
    ram=bytes.fromhex('1f8b08000000000002ff0300000000000000000000')
    parts=[loader,ram,b'',dtbh]
    header=bytearray(page);header[:8]=b'ANDROID!'
    struct.pack_into('<10I',header,8,len(loader),0x10008000,len(ram),0x11000000,0,0,0x10000100,page,len(dtbh),0)
    header[64:576]=b'console=tty0'.ljust(512,b'\0');header[576:608]=ident(parts)
    result=bytes(header)+b''.join(d+bytes((-len(d))%page) for d in parts)+TRAILER
    parse(result)
    return result
