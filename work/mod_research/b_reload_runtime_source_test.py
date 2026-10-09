"""Bounded disk-RVA parser checks only; no installed files or processes."""
import struct
import unittest
from b_reload_runtime_source_check import PeFile


def image():
    data = bytearray(0x500)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<HHIIIHH', data, 0x84, 0x8664, 1, 0, 0, 0, 240, 0)
    struct.pack_into('<H', data, 0x98, 0x20b)
    struct.pack_into('<I', data, 0x98+16, 0x1000)
    struct.pack_into('<I', data, 0x98+56, 0x2000)
    struct.pack_into('<IIII', data, 0x188+8, 0x200, 0x1000, 0x100, 0x300)
    struct.pack_into('<I', data, 0x188+36, 0x60000020)
    data[0x310:0x314] = b'test'
    return data


class MappingTests(unittest.TestCase):
    def test_disk_offset_is_not_rva(self):
        self.assertEqual(PeFile(image()).read(0x1010, 4), (b'test', 0x310, 0x60000020))

    def test_reject_virtual_tail_and_truncation(self):
        with self.assertRaisesRegex(ValueError, 'no disk bytes'):
            PeFile(image()).read(0x1100, 4)
        with self.assertRaisesRegex(ValueError, 'overflow'):
            PeFile(image()[:0x350])

    def test_reject_ambiguous_sections(self):
        data = image()
        struct.pack_into('<H', data, 0x86, 2)
        data[0x1b0:0x1d8] = data[0x188:0x1b0]
        with self.assertRaisesRegex(ValueError, 'unique section'):
            PeFile(data).read(0x1010, 4)


if __name__ == '__main__':
    unittest.main()
