#!/usr/bin/env python3
import struct,unittest
from container import pack,parse,ident,TRAILER
class ContainerTests(unittest.TestCase):
    def reference(self):
        h=bytearray(2048);h[:8]=b'ANDROID!';struct.pack_into('<I',h,36,2048)
        parts=[b'kernel',b'ram',b'',b'DTBHtable']
        for f,d in zip((8,16,24,40),parts):struct.pack_into('<I',h,f,len(d))
        h[576:608]=ident(parts)
        return bytes(h)+b''.join(d+bytes((-len(d))%2048) for d in parts)+TRAILER
    def test_roundtrip(self):
        b=pack(self.reference(),b'loader');p,parts,end=parse(b)
        self.assertEqual(parts[0],b'loader');self.assertEqual(end,len(b));self.assertEqual(p,2048)
    def test_rejects_payload_corruption(self):
        b=bytearray(pack(self.reference(),b'loader'));b[2048]^=1
        with self.assertRaises(ValueError):parse(b)
    def test_rejects_truncation_and_trailer(self):
        b=pack(self.reference(),b'loader')
        for n in (0,100,2048,len(b)-1):
            with self.assertRaises(ValueError):parse(b[:n])
    def test_rejects_padding(self):
        b=bytearray(self.reference());b[2055]=1
        with self.assertRaises(ValueError):parse(b)
    def test_rejects_sizes(self):
        for field,val in ((36,0),(36,8192),(8,0xffffffff)):
            b=bytearray(self.reference());struct.pack_into('<I',b,field,val)
            with self.assertRaises(ValueError):parse(b)
if __name__=='__main__':unittest.main()
