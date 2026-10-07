"""Read-only, version-locked proposal and city-linked durability coverage.

This is a diagnostic snapshot, not a replication or game execution adapter.
No debugger, remote calls, writes or thread suspension are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from game_reader import GameReader, DATA_POINTER_RVA

PROPOSAL_TABLE = 0x7EF08
PROPOSAL_COUNT = 31
HANDLERS = (
    'None', 'DevelopmentUp', 'SecurityUp', 'Investment', 'Conscription',
    'SpecialTraining', 'Exploit', 'Requisition', 'RepairEndurance',
    'SecurityDown', 'MoraleUp', 'MoraleDown', 'RecoveryWoundedSoldier',
    'BuyFood', 'SellFood', 'RecomendPerson', 'Banquet', 'CurePerson',
    'FreePrisoner', 'NormalyFriend', 'StunEnemy', 'ConfusionEnemy',
    'BurnEnemy', 'ExtinguishFireFriend', 'FillupSoldier',
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def decode_proposal(raw, slot):
    if len(raw) != 0x30 or not 0 <= slot < PROPOSAL_COUNT:
        raise ValueError('Unsupported proposal record length or slot')
    kind = struct.unpack_from('<H', raw, 0x10)[0]
    person = struct.unpack_from('<H', raw, 0x14)[0]
    if kind >= len(HANDLERS) or person >= 6000:
        raise ValueError('Proposal field outside the supported range')
    return {'slot': slot, 'type_id': kind, 'handler': HANDLERS[kind],
            'flag_12': raw[0x12], 'person_id': person,
            'parameter_words': list(struct.unpack_from('<5I', raw, 0x18)),
            # Retain unknown bytes and padding; no claim that these are portable.
            'payload_10_30_hex': raw[0x10:0x30].hex(), 'raw_00_30_hex': raw.hex()}


def coverage_hashes(data):
    """Keep local player context separate from common-world durability.

    The payload hash retains unknown bytes: a match is useful evidence, but a
    mismatch may need semantic analysis. It is not a final network wire format.
    """
    return {
        'player_bound_proposal_payload_sha256': digest({
            'player_context': data['context']['player'],
            'date': data['context']['date'],
            'ordered_slots': [(r['slot'], r['payload_10_30_hex']) for r in data['proposals']]}),
        'city_linked_durability_sha256': digest(data['city_linked_objects']),
    }


class ProposalStateReader(GameReader):
    def capture_once(self):
        context = self.snapshot()
        if not context['in_player_strategy']:
            raise RuntimeError('Capture at a paused player planning screen')
        m = self.memory
        root = self.pointer(m.base + DATA_POINTER_RVA)
        world = self.pointer(root + 0x85130)
        self.require_type(world, 'CWorldData')
        proposals = []
        for slot in range(PROPOSAL_COUNT):
            address = self.pointer(root + PROPOSAL_TABLE + slot * 8)
            self.require_type(address, 'CProposalData')
            row = decode_proposal(m.read(address, 0x30), slot)
            proposals.append(row)
            if row['type_id']:
                person = self.pointer(root + 0x148 + row['person_id'] * 8)
                self.require_type(person, 'CPersonData')
                if int.from_bytes(m.read(person + 0x10, 2), 'little') != row['person_id']:
                    raise RuntimeError('Proposal person id disagrees with table index')
        cities = []
        for city_id in range(52):
            city = self.pointer(root + 0xDAA8 + city_id * 8)
            self.require_type(city, 'CCityData')
            if int.from_bytes(m.read(city + 0x10, 2), 'little') != city_id:
                raise RuntimeError('City id disagrees with table index')
            object_id = int.from_bytes(m.read(city + 0x4E, 2), 'little')
            # Follow the native getter's out-of-range fallback, but retain source.
            table_id = object_id if object_id <= 3000 else 0
            obj = self.pointer(root + 0x6D808 + table_id * 8)
            self.require_type(obj, 'CObjectData')
            cities.append({'city_id': city_id, 'object_id_from_city_4e': object_id,
                           'resolved_object_table_id': table_id,
                           'endurance_object_14': int.from_bytes(m.read(obj + 0x14, 2), 'little')})
        result = {'schema': 'san14.proposal-durability-diagnostic.v1', 'mode': 'read-only-live-game',
                  'context': context, 'proposals': proposals, 'city_linked_objects': cities,
                  'random_global_18eb8b0': int.from_bytes(m.read(m.base + 0x18EB8B0, 4), 'little'),
                  'world_450_460_hex': m.read(world + 0x450, 16).hex(),
                  'nonempty_proposal_count': sum(r['type_id'] != 0 for r in proposals),
                  'scope': 'Current native proposal bank, tagged with observed local player context; '
                           '52 city-table links to object+14 only. No full-world, proposal ownership, '
                           'atomic boundary, cross-client equality or replication proof.'}
        if context != self.snapshot() or root != self.pointer(m.base + DATA_POINTER_RVA):
            raise RuntimeError('Game context changed during capture')
        result['hashes'] = coverage_hashes(result)
        return result

    def capture(self):
        first = self.capture_once()
        if first != self.capture_once():
            raise RuntimeError('Covered state changed during repeated reads')
        first['validation'] = 'Executable SHA256, RTTI, bounds, record identity and two equal reads; not atomic'
        return first


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise RuntimeError('Refusing to overwrite evidence')
    reader = ProposalStateReader()
    try:
        result = reader.capture()
    finally:
        reader.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'date': result['context']['date'], 'player': result['context']['player'],
                      'proposals': result['nonempty_proposal_count'],
                      'city_links': len(result['city_linked_objects']), 'hashes': result['hashes']},
                     ensure_ascii=True))


if __name__ == '__main__':
    main()
