import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('native', Path(__file__).with_name('prepare-native-usb.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class NativeSource(unittest.TestCase):
    def test_pins_and_repeatability(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'
            self.assertEqual(m.prepare(m.ROOT, a), m.prepare(m.ROOT, b))
            for name, (_, expected) in m.SOURCES.items():
                self.assertEqual(m.sha((a/name).read_bytes()), expected)
                self.assertEqual((a/name).read_bytes(), (b/name).read_bytes())
                self.assertEqual((a/name).stat().st_mode & 0o777, 0o644)
            with self.assertRaises(ValueError):
                m.prepare(m.ROOT, a)
    def test_drift_rejected(self):
        for name in m.SOURCES:
            data = (m.ROOT/'build/arch-arm/usb'/name).read_bytes()
            with self.assertRaises(ValueError):
                m.transform(name, data + b'\n')
    def test_symlink_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'build/arch-arm').mkdir(parents=True)
            (root/'build/arch-arm/usb').symlink_to(m.ROOT/'build/arch-arm/usb', target_is_directory=True)
            with self.assertRaises(ValueError):
                m.prepare(root, root/'out')
            self.assertFalse((root/'out').exists())

if __name__ == '__main__':
    unittest.main()
