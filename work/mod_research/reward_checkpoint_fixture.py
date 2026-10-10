"""Owned RAM: actual GameReader reward fields and both audited world tables.

Business reward execution, RTTI, process identity remain explicit doubles.
No native code/game access. Unlike the earlier gate fixture, both projections
read the SAME object layout and retained GameReader on each side.
"""
import struct

from reward_observed_fixture import World as RewardWorld
import b_warm_world as world


class World(RewardWorld):
    def __init__(self, viewer):
        super().__init__(viewer)
        self.tables = {}
        m = self.memory
        for name, offset, count, vt, serializer, layout in world.TABLES:
            width = max(off + size for off, size in layout)
            stride = (width + 0xff) & ~0xff
            start = self.obj('owned-' + name, count * stride)
            pointers = [start + i * stride for i in range(count)]
            self.tables[name] = pointers
            m.pack(self.root + offset, '<' + 'Q' * count, *pointers)
            m.pack(m.base + vt + 0x28, '<Q', m.base + serializer)
            for i, address in enumerate(pointers):
                if name == 'forces':
                    self.types[address] = 'CForceData'
                raw = bytearray((i * 37 + j * 11) % 256 for j in range(width))
                struct.pack_into('<Q', raw, 0, m.base + vt)
                if name == 'forces' and i in (2, 12):
                    struct.pack_into('<H', raw, 0x10, 952 if i == 2 else 666)
                m.put(address, raw)

    def copy_tables_to_bootstrap_double(self, reader):
        """Populate old load environment doubles with the identical initial bytes.

        The load/RAM environment remains an explicit double. This supplies the
        actual formal bootstrap projection instead of editing coordinator hashes.
        """
        for name, _, _, _, _, layout in world.TABLES:
            width = max(off + size for off, size in layout)
            for source, target in zip(self.tables[name], reader.objects[name]):
                reader.memory.put(target, self.memory.read(source, width))
