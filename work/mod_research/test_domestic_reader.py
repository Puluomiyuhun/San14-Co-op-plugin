"""Offline decoder fixtures; never instantiate a live GameReader."""
from pathlib import Path
import json
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'outputs' / 'san14-link'))
from domestic_reader import (DomesticDecoder, DATA_POINTER_RVA, PERSON_LIST_VTABLE_RVA,
                             PERSON_POOL_ENABLED_RVA, PERSON_POOL_HEADS_RVA,
                             PERSON_POOL_COUNTS_RVA, PERSON_POOL_CAPACITY_RVA)


class MemoryFixture:
    def __init__(self, shift=0):
        self.base = 0x140000000 + shift
        self.regions = {}

    def allocate(self, address, length):
        self.regions[address] = bytearray(length)
        return address

    def region(self, address, length):
        for start, data in self.regions.items():
            if start <= address and address + length <= start + len(data):
                return data, address - start
        raise RuntimeError(f'Fixture read outside allocated memory: {address:#x}, {length}')

    def read(self, address, length):
        data, offset = self.region(address, length)
        return bytes(data[offset:offset + length])

    def write(self, address, data):
        region, offset = self.region(address, len(data))
        region[offset:offset + len(data)] = data

    def number(self, address, value, width=8):
        self.write(address, value.to_bytes(width, 'little'))


class Fixture:
    def __init__(self, kind='reward', shift=0):
        self.memory = MemoryFixture(shift)
        m = self.memory
        self.types = {}
        self.cursor = 0x300000000 + shift
        self.root = self.object('CSan14Data', 0x86000)
        m.allocate(m.base + DATA_POINTER_RVA, 8)
        m.number(m.base + DATA_POINTER_RVA, self.root)
        self.districts = {}
        for identity in range(1, 52):
            address = self.object('CDistrictData', 0x40)
            self.districts[identity] = address
            m.number(self.root + 0xDE40 + identity * 8, address)
            m.number(address + 0x10, 12 if identity == 11 else 1, 1)
            m.number(address + 0x12, 666, 2)
            m.number(address + 0x14, 18, 1)
        self.people = {}
        for identity, name in [(620, '张卫'), (666, '张鲁')]:
            address = self.object('CPersonData', 0x200)
            self.people[identity] = address
            m.number(self.root + 0x148 + identity * 8, address)
            m.number(address + 0x10, identity, 2)
            m.write(address + 0x12, name[0].encode('utf-16le'))
            m.write(address + 0x24, name[1:].encode('utf-16le'))
            m.number(address + 0x118, 11, 1)
            m.number(address + 0x11A, 19, 2)
            m.number(address + 0x120, 80, 1)
        self.cities = {}
        for identity in range(1, 52):
            address = self.object('CCityData', 0x100)
            self.cities[identity] = address
            m.number(self.root + 0xDAA8 + identity * 8, address)
            m.number(address + 0x10, identity, 2)
            m.write(address + 0x12, ('宛' if identity == 19 else '城').encode('utf-16le'))
            m.number(address + 0x30, 11, 1)
            m.number(address + 0x34, 10000, 4)
            m.number(address + 0x38, 30000, 4)
            m.number(address + 0x3C, 15204, 4)
            m.number(address + 0x4E, identity, 2)
            m.number(address + 0xC8, 30, 1)
        state_names = {'reward': 'CStrategyRewardState', 'merchant': 'CStrategyMerchantState',
                       'officer_move': 'CStrategyMoveState'}
        self.state_name = state_names[kind]
        self.state = self.object(self.state_name, 0x600)
        self.layout = self.object('FixtureLayout', 0x300)
        m.number(self.layout + 0x170, 0, 4)
        m.number(self.state + 0x470, self.districts[11] if kind == 'reward' else self.cities[19])
        m.number(self.state + (0x498 if kind == 'officer_move' else 0x478), self.layout)
        self.list_address = self.state + (0x478 if kind == 'officer_move' else 0x480)
        m.number(self.list_address, m.base + PERSON_LIST_VTABLE_RVA)
        self.handle = self.object('FixtureHandle', 8)
        m.number(self.handle, 1, 4)
        m.number(self.list_address + 8, self.handle)
        self.heads, self.counts = self.object('FixtureHeads', 16), self.object('FixtureCounts', 16)
        self.node1, self.node2 = self.object('FixtureNode', 16), self.object('FixtureNode', 16)
        m.number(self.node1, self.people[620])
        m.number(self.node1 + 8, self.node2)
        m.number(self.node2, self.people[666])
        m.number(self.node2 + 8, 0)
        m.number(self.heads + 8, self.node1)
        m.number(self.counts + 8, 2)
        for rva, value, width in [(PERSON_POOL_ENABLED_RVA, 1, 8),
                                  (PERSON_POOL_HEADS_RVA, self.heads, 8),
                                  (PERSON_POOL_COUNTS_RVA, self.counts, 8),
                                  (PERSON_POOL_CAPACITY_RVA, 2, 4)]:
            m.allocate(m.base + rva, width)
            m.number(m.base + rva, value, width)
        if kind == 'merchant':
            m.number(self.state + 0x490, 1000, 4)
            m.number(self.state + 0x494, 1, 4)
        elif kind == 'officer_move':
            first_hex = self.object('CHexData', 32 * 20)
            self.hex_address = first_hex + 32 * 19
            self.types[self.hex_address] = 'CHexData'
            m.number(self.root + 0xDFE0, first_hex)
            m.number(self.root + 0xDFE0 + 19 * 8, self.hex_address)
            m.number(self.state + 0x488, self.hex_address)
            m.number(self.state + 0x490, self.cities[21])

    def object(self, name, length):
        address = self.memory.allocate(self.cursor, length)
        self.types[address] = name
        self.cursor += (length + 0x107) & ~7
        return address

    def require_type(self, address, name):
        if self.types.get(address) != name:
            raise RuntimeError('Fixture RTTI mismatch')

    def capture(self):
        decoder = DomesticDecoder(self)
        result = decoder.decode(self.state_name, self.state)
        decoder.verify_stable()
        return result


class DecoderTests(unittest.TestCase):
    def test_reward_batch_is_semantic_ids(self):
        result = Fixture().capture()
        self.assertEqual(result['command_preview'], {
            'kind': 'reward', 'force_id': 12, 'district_id': 11,
            'funding_city_id': 19, 'officer_ids': [620, 666]})
        self.assertTrue(result['basic_ownership_matches'])
        self.assertFalse(result['legality_verified'])
        self.assertFalse(result['replay_supported'])

    def test_merchant_buy_and_sell(self):
        fixture = Fixture('merchant')
        self.assertEqual(fixture.capture()['command_preview']['direction'], 'buy_food')
        fixture.memory.number(fixture.state + 0x494, 0, 4)
        command = fixture.capture()['command_preview']
        self.assertEqual((command['direction'], command['food_quantity']), ('sell_food', 1000))

    def test_move_uses_hex_origin_and_city_target(self):
        command = Fixture('officer_move').capture()['command_preview']
        self.assertEqual((command['origin_hex_id'], command['destination_city_id']), (19, 21))

    def test_relocated_memory_gives_identical_output(self):
        for kind in ['reward', 'merchant', 'officer_move']:
            self.assertEqual(Fixture(kind).capture(), Fixture(kind, 0x1000000).capture())

    def test_foreign_officer_is_flagged(self):
        fixture = Fixture()
        fixture.memory.number(fixture.people[620] + 0x118, 1, 1)
        self.assertFalse(fixture.capture()['basic_ownership_matches'])

    def test_empty_selection_is_incomplete(self):
        fixture = Fixture()
        fixture.memory.number(fixture.list_address + 8, 0)
        self.assertEqual(fixture.capture()['missing_fields'], ['officer_ids'])

    def test_missing_move_destination(self):
        fixture = Fixture('officer_move')
        fixture.memory.number(fixture.state + 0x490, 0)
        self.assertIn('destination_city_id', fixture.capture()['missing_fields'])

    def test_cycle_rejected(self):
        fixture = Fixture()
        fixture.memory.number(fixture.node2 + 8, fixture.node1)
        with self.assertRaisesRegex(RuntimeError, 'Cyclic'):
            fixture.capture()

    def test_count_mismatch_rejected(self):
        fixture = Fixture()
        fixture.memory.number(fixture.counts + 8, 3)
        with self.assertRaisesRegex(RuntimeError, 'Truncated'):
            fixture.capture()

    def test_invalid_pool_slot_rejected(self):
        fixture = Fixture()
        fixture.memory.number(fixture.handle, 2, 4)
        with self.assertRaisesRegex(RuntimeError, 'outside'):
            fixture.capture()

    def test_duplicate_officer_rejected(self):
        fixture = Fixture()
        fixture.memory.number(fixture.node2, fixture.people[620])
        with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
            fixture.capture()

    def test_wrong_list_type_rejected(self):
        fixture = Fixture()
        fixture.memory.number(fixture.list_address, 0x12345678)
        with self.assertRaisesRegex(RuntimeError, 'list implementation'):
            fixture.capture()

    def test_city_element_in_shared_pointer_pool_rejected(self):
        fixture = Fixture()
        fixture.memory.number(fixture.node1, fixture.cities[19])
        with self.assertRaisesRegex(RuntimeError, 'RTTI mismatch'):
            fixture.capture()

    def test_bad_merchant_direction_rejected(self):
        fixture = Fixture('merchant')
        fixture.memory.number(fixture.state + 0x494, 2, 4)
        with self.assertRaisesRegex(RuntimeError, 'direction'):
            fixture.capture()

    def test_city_identity_mismatch_rejected(self):
        fixture = Fixture('merchant')
        fixture.memory.number(fixture.cities[19] + 0x10, 21, 2)
        with self.assertRaisesRegex(RuntimeError, 'identity/table'):
            fixture.capture()

    def test_torn_draft_rejected(self):
        fixture = Fixture()
        decoder = DomesticDecoder(fixture)
        decoder.decode(fixture.state_name, fixture.state)
        fixture.memory.number(fixture.people[620] + 0x120, 81, 1)
        with self.assertRaisesRegex(RuntimeError, 'changed during sampling'):
            decoder.verify_stable()


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DecoderTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (ROOT / 'domestic-decoder-fixture-results.json').write_text(json.dumps({
        'result': 'PASS' if result.wasSuccessful() else 'FAIL',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'mode': 'offline-synthetic-memory-fixtures', 'opened_game_process': False,
        'real_ui_parameter_correlation_verified': False,
    }, indent=2), encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
