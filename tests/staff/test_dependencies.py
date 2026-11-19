"""Build inputs must be immutable; never compile an unverified cache."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class Dependencies(unittest.TestCase):
    def test_lock_and_tampered_archive(self):
        spec = importlib.util.spec_from_file_location('staff_build', ROOT/'tools/Build-Staff.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.verify_dependencies(ROOT/'dist/staff-deps')
        with tempfile.TemporaryDirectory(dir=ROOT/'dist/verification/staff-20261012') as tmp:
            p = Path(tmp)
            (p/'sodium.tar.gz').write_bytes(b'changed archive')
            with self.assertRaisesRegex(RuntimeError, 'checksum'):
                module.verify_dependencies(p)

if __name__ == '__main__':
    unittest.main()
