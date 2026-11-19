"""Binary-format tests: independent frame decoding catches relocated-pool errors."""
import importlib.util
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

def fixture(frames, pool, skeleton=b'rig-one!'):
    # Compact synthetic one-bone rig is enough for format relocation checks.
    frame_start = 100 + len(skeleton)
    data = b''.join(int(i).to_bytes(3, 'little') for i in frames)
    padding = b'\0' * (-(frame_start + len(data)) % 4)
    pool_start = frame_start + len(data) + len(padding)
    bones = b''.join(pool)
    header = struct.pack('<4si64sf6i', b'2LGA', 6, b'test', .64,
                         len(frames), frame_start, 1, pool_start, 104, pool_start + len(bones))
    return header + skeleton + data + padding + bones

def decoded(data):
    h = struct.unpack_from('<4si64sf6i', data)
    return [data[h[7] + int.from_bytes(data[h[5]+i*3:h[5]+i*3+3], 'little')*14:]
            [:14] for i in range(h[4])]

class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = None
        if (ROOT / 'tools/stance_library.py').exists():
            import stance_library
            cls.module = stance_library

    def importer(self):
        self.assertIsNotNone(self.module, 'Stance GLA importer has not been implemented')
        return self.module

    def test_append_relocates_pool_and_preserves_every_original_frame(self):
        m = self.importer()
        a, b, c = b'a'*14, b'b'*14, b'c'*14
        base = fixture([0, 1, 0], [a, b])
        donor = fixture([1, 0], [c, a])
        output, ranges = m.merge_gla(base, [(donor, 0, 2)])
        self.assertEqual(decoded(output), [a, b, a, a, c])
        self.assertEqual(ranges, [(3, 2)])
        self.assertEqual(output[100:108], base[100:108])
        self.assertEqual(output, m.merge_gla(base, [(donor, 0, 2)])[0])

    def test_different_skeleton_rejected(self):
        m = self.importer()
        with self.assertRaisesRegex(ValueError, 'skeleton'):
            m.merge_gla(fixture([0], [b'a'*14]), [(fixture([0], [b'a'*14], b'rig-two!'), 0, 1)])

    def test_bad_indices_and_clip_bounds_rejected(self):
        m = self.importer()
        good = fixture([0], [b'a'*14])
        for first, count in [(-1, 1), (0, 0), (1, 1), (0, 2)]:
            with self.assertRaises(ValueError): m.merge_gla(good, [(good, first, count)])
        with self.assertRaises(ValueError): m.merge_gla(fixture([1], [b'a'*14]), [])
        with self.assertRaises(ValueError): m.merge_gla(good[:-1], [])

if __name__ == '__main__': unittest.main()
