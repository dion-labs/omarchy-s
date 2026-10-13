#!/usr/bin/env python3
import importlib.util,struct,unittest
from pathlib import Path
from container import parse
spec=importlib.util.spec_from_file_location('explicit',Path(__file__).with_name('explicit-container.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ExplicitTests(unittest.TestCase):
    def table(self):
        d=bytearray(4096);struct.pack_into('<4sII8I',d,0,b'DTBH',2,1,9810,20646,561349850,26,255,2048,2048,32);d[2048:2052]=b'\xd0\x0d\xfe\xed';return bytes(d)
    def test_header(self):
        b=m.build(b'loader',self.table());parse(b)
        self.assertEqual(struct.unpack_from('<I',b,12)[0],0x10008000)
        self.assertEqual(struct.unpack_from('<I',b,20)[0],0x11000000)
        self.assertEqual(struct.unpack_from('<I',b,32)[0],0x10000100)
        self.assertFalse(any(b[608:2048]))
    def test_bad_board(self):
        for pos in (4,8,12,16,20,24,28,32,40):
            d=bytearray(self.table());d[pos]^=1
            with self.assertRaises(ValueError):m.build(b'loader',d)
    def test_bounds(self):
        for n in (0,43,2048,4095):
            with self.assertRaises(ValueError):m.build(b'loader',self.table()[:n])
if __name__=='__main__':unittest.main()
