import copy,hashlib,importlib.util,struct,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('pack',Path(__file__).with_name('pack-dtbh.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def fixture(size):
 data=struct.pack('>10I',0xd00dfeed,size,56,64,40,17,16,0,size-64,8)+bytes(size-40)
 profile={'schema':1,'format':'s9-single-dtbh-v2','alignment':2048,'entry_prefix_words':[9810,20646,561349850,26,255],'entry_final_word':32,'dtb_sha256':hashlib.sha256(data).hexdigest()}
 return data,profile
class Packer(unittest.TestCase):
 def test_alignment_boundaries(self):
  for size,extent in [(2047,2048),(2048,2048),(2049,4096)]:
   data,p=fixture(size);out=m.pack(data,p)
   self.assertEqual(len(out),2048+extent);self.assertEqual(out[2048:2048+size],data)
   self.assertEqual(out[44:2048],bytes(2004));self.assertEqual(out[2048+size:],bytes(extent-size))
   self.assertEqual(struct.unpack_from('<3I',out,32),(2048,extent,32))
 def test_unknown_input(self):
  data,p=fixture(100)
  with self.assertRaisesRegex(ValueError,'Unrecognized'):m.pack(data+b'x',p)
 def test_bad_header_even_with_matching_hash(self):
  for offset,value in [(0,0),(4,99),(8,55),(12,200),(16,41),(20,16),(24,15)]:
   data,p=fixture(100);b=bytearray(data);struct.pack_into('>I',b,offset,value);p['dtb_sha256']=hashlib.sha256(b).hexdigest()
   with self.subTest(offset=offset):
    with self.assertRaises(ValueError):m.pack(b,p)
 def test_profile_restriction(self):
  data,p=fixture(100)
  for key,value in [('schema',2),('format','general'),('alignment',4096),('entry_prefix_words',[1])]:
   q=copy.deepcopy(p);q[key]=value
   with self.assertRaises(ValueError):m.pack(data,q)
if __name__=='__main__':unittest.main()
