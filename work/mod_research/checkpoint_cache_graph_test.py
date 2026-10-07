import struct
import unittest
from checkpoint_cache_graph import inspect_cache


class CacheGraphTests(unittest.TestCase):
    def setUp(self):
        self.mem = bytearray(0x10000)
        self.base = 0x100000
        self.cache = self.base
        self.heads = [self.base + 0x1000 + n * 0x100 for n in range(5)]
        for offset, head in zip([0x10, 0x400, 0x410, 0x420, 0x430], self.heads):
            self.q(self.cache + offset, head)
            self.q(head, head)
            self.q(head + 8, head)
        struct.pack_into('<i', self.mem, 0x3EC, -1)

    def q(self, address, value):
        struct.pack_into('<Q', self.mem, address - self.base, value)

    def read(self, address, size):
        return bytes(self.mem[address - self.base:address - self.base + size])

    def node(self, group=1, slot=0):
        node = self.base + 0x3000 + group * 0x200
        head = self.heads[group]
        offset = [0x10, 0x400, 0x410, 0x420, 0x430][group]
        self.q(head, node)
        self.q(head + 8, node)
        self.q(node, head)
        self.q(node + 8, head)
        self.q(self.cache + offset + 8, 1)
        text_at = node - self.base + 0x138
        self.mem[text_at:text_at + 12] = b'mppush01.s14'
        struct.pack_into('<QQ', self.mem, text_at + 16, 12, 15)
        if slot is not None:
            self.q(self.cache + 0x20 + slot * 8, node + 0x10)
        return node

    def test_empty(self):
        self.assertEqual(inspect_cache(self.read, self.cache)['owned_nodes'], 0)

    def test_all_five_owners(self):
        for n in range(5):
            self.node(n, n)
        self.assertEqual(inspect_cache(self.read, self.cache)['indexed_nodes'], 5)

    def test_unindexed_group_is_owned(self):
        self.node(slot=None)
        self.assertEqual(inspect_cache(self.read, self.cache)['unindexed_owned_nodes'], 1)

    def test_bad_graphs(self):
        mutations = [
            lambda n: self.q(n, n),
            lambda n: self.q(n + 8, n),
            lambda n: self.q(self.heads[1] + 8, self.heads[1]),
            lambda n: self.q(self.cache + 0x408, 2),
            lambda n: self.q(self.cache + 0x20, n + 8),
            lambda n: self.q(self.cache + 0x28, n + 16),
            lambda n: self.q(self.cache + 0x410, self.heads[1]),
            lambda n: self.q(n, self.heads[2]),
            lambda n: self.q(n + 0x150, 0),
            lambda n: self.q(self.heads[2], n),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.setUp()
                mutate(self.node())
                with self.assertRaises(ValueError):
                    inspect_cache(self.read, self.cache)

    def test_changing_header(self):
        calls = 0
        def read(address, size):
            nonlocal calls
            calls += 1
            if calls == 7:
                self.q(self.cache + 0x18, 1)
            return self.read(address, size)
        with self.assertRaisesRegex(ValueError, 'cache_changed'):
            inspect_cache(read, self.cache)

    def test_head_embedded_in_owned_payload(self):
        node = self.node()
        nested_head = node + 0x20
        self.q(self.cache + 0x410, nested_head)
        self.q(nested_head, nested_head)
        self.q(nested_head + 8, nested_head)
        with self.assertRaisesRegex(ValueError, 'overlapping_owner_storage'):
            inspect_cache(self.read, self.cache)

    def test_head_overlaps_manager(self):
        nested_head = self.cache + 0x200
        self.q(self.cache + 0x410, nested_head)
        self.q(nested_head, nested_head)
        self.q(nested_head + 8, nested_head)
        with self.assertRaisesRegex(ValueError, 'overlapping_owner_storage'):
            inspect_cache(self.read, self.cache)


if __name__ == '__main__':
    unittest.main()
