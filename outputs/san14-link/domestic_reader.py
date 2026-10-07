"""Read-only domestic drafts derived from static analysis, not execution support.

Supports city-based reward, merchant and officer-move UI layouts in the locked
build. Real UI parameter correlation is still pending. Unsupported foothold
types fail closed rather than borrowing a city layout.
"""
import argparse
import json
from pathlib import Path
import struct
from game_reader import GameReader, DATA_POINTER_RVA
from sortie_reader import text_name

PERSON_LIST_VTABLE_RVA = 0x123F448
# The backing pointer pool is shared with other ptr_list<T> types. The specific
# list vtable and every element's CPersonData RTTI must both be checked.
PERSON_POOL_ENABLED_RVA = 0x201D3A8
PERSON_POOL_HEADS_RVA = 0x201D3B0
PERSON_POOL_COUNTS_RVA = 0x201D3C8
PERSON_POOL_CAPACITY_RVA = 0x201D3E0
SUPPORTED_STATES = {
    'CStrategyRewardState': 'reward',
    'CStrategyMerchantState': 'merchant',
    'CStrategyMoveState': 'officer_move',
}


class DomesticDecoder:
    """Only calls a reader's read/type/snapshot methods; has no write API."""
    def __init__(self, reader):
        self.reader = reader
        self.memory = reader.memory
        self.reads = []
        self.root = self.ptr(self.memory.base + DATA_POINTER_RVA)
        self.require_type(self.root, 'CSan14Data')

    def read(self, address, length):
        data = self.memory.read(address, length)
        if len(data) != length:
            raise RuntimeError('Short memory read')
        self.reads.append((address, data))
        return data

    def uint(self, address, width=4):
        return int.from_bytes(self.read(address, width), 'little')

    def ptr(self, address, nullable=False):
        value = self.uint(address, 8)
        if value == 0 and nullable:
            return 0
        self.check_pointer(value)
        return value

    @staticmethod
    def check_pointer(value):
        if not 0x10000 <= value < 0x7FFFFFFFFFFF or value % 8:
            raise RuntimeError('Invalid or unaligned object pointer')

    def require_type(self, address, name):
        self.check_pointer(address)
        self.read(address, 8)  # Include vtable identity in consistency sampling.
        self.reader.require_type(address, name)

    def district(self, identity):
        if not 1 <= identity <= 51:
            raise RuntimeError('Unsupported district ID')
        address = self.ptr(self.root + 0xDE40 + identity * 8)
        self.require_type(address, 'CDistrictData')
        data = self.read(address + 0x10, 0x18)
        if not 1 <= data[0] <= 51:
            raise RuntimeError('District has no supported owner')
        return {'id': identity, 'force_id': data[0],
                'leader_id': struct.unpack_from('<H', data, 2)[0],
                'action_points': data[4]}

    def district_at(self, address):
        for identity in range(1, 52):
            if self.ptr(self.root + 0xDE40 + identity * 8) == address:
                return self.district(identity)
        raise RuntimeError('District pointer does not belong to its object table')

    def person_at(self, address):
        self.require_type(address, 'CPersonData')
        data = self.read(address + 0x10, 0x188)
        identity = struct.unpack_from('<H', data)[0]
        if not 1 <= identity < 6000 or self.ptr(self.root + 0x148 + identity * 8) != address:
            raise RuntimeError('Officer identity/table mismatch')
        district = self.district(data[0x108])
        return {'id': identity, 'name': text_name(data[2:20]) + text_name(data[20:38]),
                'district_id': district['id'], 'force_id': district['force_id'],
                'location_id': struct.unpack_from('<H', data, 0x10A)[0],
                'loyalty_raw': data[0x110],
                'status_flags_raw': struct.unpack_from('<H', data, 0x186)[0]}

    def person_list(self, address):
        if self.uint(address, 8) != self.memory.base + PERSON_LIST_VTABLE_RVA:
            raise RuntimeError('Unsupported person-list implementation')
        handle = self.ptr(address + 8, nullable=True)
        if not handle:
            return []
        base = self.memory.base
        if not self.uint(base + PERSON_POOL_ENABLED_RVA, 8):
            raise RuntimeError('Person-list pool is not initialized')
        slot = self.uint(handle)
        capacity = self.uint(base + PERSON_POOL_CAPACITY_RVA)
        if not 0 < capacity <= 0x20000 or not 0 <= slot < min(capacity, 0x14000):
            raise RuntimeError('Person-list handle is outside the supported pool')
        heads = self.ptr(base + PERSON_POOL_HEADS_RVA)
        counts = self.ptr(base + PERSON_POOL_COUNTS_RVA)
        count = self.uint(counts + slot * 8, 8)
        if count > 6000:
            raise RuntimeError('Unreasonable officer count')
        node = self.ptr(heads + slot * 8, nullable=True)
        visited, identities, people = set(), set(), []
        while node:
            if node in visited or len(visited) >= count:
                raise RuntimeError('Cyclic list or count mismatch')
            visited.add(node)
            person, next_node = struct.unpack('<QQ', self.read(node, 16))
            row = self.person_at(person)
            if row['id'] in identities:
                raise RuntimeError('Duplicate officer in draft')
            identities.add(row['id'])
            people.append(row)
            if next_node:
                self.check_pointer(next_node)
            node = next_node
        if len(people) != count:
            raise RuntimeError('Truncated person list')
        return people

    def city_at(self, address):
        self.require_type(address, 'CCityData')
        data = self.read(address + 0x10, 0xBC)
        identity = struct.unpack_from('<H', data)[0]
        if not 1 <= identity <= 51 or self.ptr(self.root + 0xDAA8 + identity * 8) != address:
            raise RuntimeError('City identity/table mismatch')
        district = self.district(data[0x20])
        return {'id': identity, 'name': text_name(data[2:10]),
                'foothold_id': struct.unpack_from('<H', data, 0x3E)[0],
                'district_id': district['id'], 'force_id': district['force_id'],
                'gold': struct.unpack_from('<I', data, 0x24)[0],
                'food': struct.unpack_from('<I', data, 0x28)[0],
                'garrison': struct.unpack_from('<I', data, 0x2C)[0],
                'trade_rate_raw': data[0xB8], 'trade_flags_raw': data[0xB9]}

    def city_for_foothold(self, identity):
        for city_id in range(1, 52):
            address = self.ptr(self.root + 0xDAA8 + city_id * 8)
            if self.uint(address + 0x4E, 2) == identity:
                return self.city_at(address)
        raise RuntimeError('Funding foothold is not a supported city')

    def hex_id(self, address):
        self.require_type(address, 'CHexData')
        first = self.ptr(self.root + 0xDFE0)
        distance = address - first
        if distance < 0 or distance % 0x20 or distance // 0x20 >= 48400:
            raise RuntimeError('Hex pointer is outside the supported layout')
        identity = distance // 0x20
        if self.ptr(self.root + 0xDFE0 + identity * 8) != address:
            raise RuntimeError('Hex table mismatch')
        return identity

    def decode(self, state_name, state):
        self.require_type(state, state_name)
        kind = SUPPORTED_STATES[state_name]
        list_offset = 0x478 if kind == 'officer_move' else 0x480
        officers = self.person_list(state + list_offset)
        missing = [] if officers else ['officer_ids']
        context = self.ptr(state + 0x470)
        if kind == 'reward':
            district = self.district_at(context)
            leader = self.person_at(self.ptr(self.root + 0x148 + district['leader_id'] * 8))
            source = self.city_for_foothold(leader['location_id'])
            command = {'kind': kind, 'force_id': district['force_id'],
                       'district_id': district['id'], 'funding_city_id': source['id'],
                       'officer_ids': [person['id'] for person in officers]}
            layout = self.ptr(state + 0x478)
        else:
            source = self.city_at(context)
            district = self.district(source['district_id'])
            command = {'kind': kind, 'force_id': source['force_id'],
                       'source_city_id': source['id'],
                       'officer_ids': [person['id'] for person in officers]}
            if kind == 'merchant':
                quantity, direction = struct.unpack('<ii', self.read(state + 0x490, 8))
                if quantity < 0 or direction not in (0, 1):
                    raise RuntimeError('Unsupported merchant quantity/direction')
                if quantity == 0:
                    missing.append('food_quantity')
                command.update(food_quantity=quantity, direction='buy_food' if direction else 'sell_food')
                layout = self.ptr(state + 0x478)
            else:
                origin = self.ptr(state + 0x488, nullable=True)
                target = self.ptr(state + 0x490, nullable=True)
                command['origin_hex_id'] = self.hex_id(origin) if origin else None
                destination = self.city_at(target) if target else None
                command['destination_city_id'] = destination['id'] if destination else None
                if origin == 0:
                    missing.append('origin_hex_id')
                if target == 0:
                    missing.append('destination_city_id')
                layout = self.ptr(state + 0x498)
        event_code = self.uint(layout + 0x170)
        ownership = (source['force_id'] == district['force_id']
                     and all(person['force_id'] == district['force_id'] for person in officers))
        if kind == 'officer_move' and destination:
            ownership = ownership and destination['force_id'] == district['force_id']
        return {'draft_available': True, 'state_name': state_name,
                'ui_event_code_raw': event_code, 'command_preview': command,
                'source_city': source, 'district': district, 'officers': officers,
                'missing_fields': missing, 'basic_ownership_matches': ownership,
                'legality_verified': False, 'replay_supported': False,
                'evidence_level': 'static-layout-derived; real UI correlation pending'}

    def verify_stable(self):
        if any(self.memory.read(address, len(data)) != data for address, data in self.reads):
            raise RuntimeError('Draft changed during sampling; retry while the screen is stable')


class DomesticReader(GameReader):
    def capture(self):
        before = self.snapshot()
        states = self.state_objects()
        candidates = [(name, address) for name, address in states if name in SUPPORTED_STATES]
        result = {'schema': 'san14.domestic-draft.v1', 'mode': 'read-only-live-game',
                  'exe_sha256': self.sha256, 'date': before['date'], 'player': before['player'],
                  'state_stack': before['state_stack'], 'applied_to_game': False}
        if not candidates:
            result.update(draft_available=False, replay_supported=False,
                          reason='No supported domestic draft is open')
        else:
            decoder = DomesticDecoder(self)
            result.update(decoder.decode(*candidates[-1]))
            result['belongs_to_local_player'] = result['command_preview']['force_id'] == before['player']['force_id']
            decoder.verify_stable()
        if self.snapshot() != before or self.state_objects() != states:
            raise RuntimeError('Game state changed during sampling')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    reader = DomesticReader()
    try:
        result = reader.capture()
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(text + '\n', encoding='utf-8')
        print(text)
    finally:
        reader.close()


if __name__ == '__main__':
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
