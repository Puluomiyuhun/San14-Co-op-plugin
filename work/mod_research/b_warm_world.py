"""Two audited table projections + date, never a full-world or Ready receipt.

Accepts an already attached read-only GameReader; no discovery, process opening,
native calls, file hashing, or game writes. Pointer equality is only a sampling
stability check, not an allocation-lifetime proof or scheduling exclusion.
"""
from copy import deepcopy
import hashlib
import struct

import checkpoint_world_coverage_extension_schema as objects
import checkpoint_world_next_table_schema as forces
from b_warm_profile_contract import validate_profile
from checkpoint_world_object_capture import Reads
from authoritative_sync import canonical, digest, hexid, validate_scope, validate_node

CONTRACT = 'san14.partial-world.object3001-force52-date.v1'
PLAN = ['CRootState', 'CMotorGameState', 'CGameState', 'CStrategyState', 'CUserStrategyState']
TABLES = (
    ('objects', objects.ROOT_OFFSET, objects.SLOT_COUNT, 0x129FDF0, 0x216140, objects.FIELDS),
    ('forces', forces.ROOT_OFFSET, forces.SLOT_COUNT, 0x129FE58, 0x214EC0, forces.FIELD_LAYOUT),
)


def require(ok, text):
    if not ok: raise ValueError(text)


def integer(value, low=1, high=2**64):
    require(type(value) is int and low <= value < high, 'Invalid bounded identity')


def node(profile):
    return dict(year=profile.loaded.year, month=profile.loaded.month, day=profile.loaded.day,
                phase='PLANNING_BOUNDARY')


def context(reader, reads, read_birth, expected):
    require(reader.sha256 == objects.GAME_SHA256, 'Unapproved game build')
    integer(reader.pid, high=2**32)
    base = reader.memory.base
    root = reads.pointer(base+0x1FCA1E0)
    world = reads.pointer(root+0x85130)
    reader.require_type(root, 'CSan14Data'); reader.require_type(world, 'CWorldData')
    snapshot = reader.snapshot()
    require(snapshot['exe_sha256'] == objects.GAME_SHA256 and snapshot['pid'] == reader.pid,
            'Reader attachment changed')
    require(tuple(snapshot['date'][k] for k in ('year', 'month', 'day')) == expected[:3] and
            (snapshot['player']['force_id'], snapshot['player']['ruler_id']) == expected[3:],
            'Date/viewer does not match this profile side')
    states = reader.state_objects()
    require([name for name, address in states] == snapshot['state_stack'] == PLAN and
            len(set(address for name, address in states)) == 5, 'Not five distinct planning objects')
    birth = read_birth(); integer(birth)
    # Recheck the world identity and direct date/viewer bytes independently of
    # GameReader.snapshot's decoded fields; its player label is not shared data.
    date = reads.read(world+0x34, 8)
    require(struct.unpack_from('<HBB', date) == expected[:3] and date[6] == expected[3], 'World date/viewer changed')
    return dict(pid=reader.pid, birth=birth, base=base, root=root, world=world,
                states=states, snapshot=snapshot)


def payload_pass(reader, reads, root):
    output = {}
    for name, offset, count, vtable, serializer, layout in TABLES:
        base = reader.memory.base
        require(reads.pointer(base+vtable+0x28) == base+serializer, 'Audited serializer slot differs')
        table = reads.read(root+offset, count*8)
        pointers = struct.unpack('<'+'Q'*count, table)
        require(len(set(pointers)) == count, 'Physical slots alias')
        width = max(off+size for off, size in layout)
        records = []
        for address in pointers:
            require(0x10000 <= address < 0x7fffffffffff-width and address % 8 == 0, 'Invalid table pointer')
            raw = reads.read(address, width)
            require(struct.unpack_from('<Q', raw)[0] == base+vtable, 'Table object vtable differs')
            records.append(b''.join(raw[off:off+size] for off, size in layout))
        reads.read(root+offset, count*8)
        output[name] = b''.join(records)
    # Existing exact-length schemas keep every physical slot, including zero
    # and inactive slots. No address/unknown-byte masking is performed.
    objects.ObjectTablePayload(output['objects'])
    forces.ForceTablePayload(output['forces'])
    return output


def shared(node_value, payload):
    return dict(contract=CONTRACT, game_sha256=objects.GAME_SHA256, date=deepcopy(node_value),
                object_schema=objects.SCHEMA, force_schema=forces.SCHEMA,
                object_payload=payload['objects'].hex(), force_payload=payload['forces'].hex())


def sample(reader, *, scope, epoch, period, profile, side, receipt_key, read_birth):
    """Read both complete projections twice; caller retains its native evidence.

    read_birth is the trusted local process-creation-time reader. receipt_key is
    the caller's accepted Save/load evidence digest, merely bound here, never
    interpreted as authority. Repeated reads cannot prove an atomic snapshot.
    """
    validate_scope(scope); validate_profile(profile)
    require(scope['profile']['game_sha256'] == objects.GAME_SHA256, 'Room build differs')
    require(hexid(epoch, 32) and int(epoch, 16) and hexid(receipt_key) and int(receipt_key, 16), 'Missing context binding')
    integer(period, high=2**53)
    require(side in ('A', 'B') and callable(read_birth), 'Explicit side/birth reader required')
    viewer = profile.source if side == 'A' else profile.target
    require(scope['bindings'][side] == dict(force_id=viewer.force, main_district_id=viewer.district), 'Viewer scope differs')
    expected = (profile.loaded.year, profile.loaded.month, profile.loaded.day, viewer.force, viewer.ruler)
    reads = Reads(reader.memory.read)
    before = context(reader, reads, read_birth, expected)
    payload = payload_pass(reader, reads, before['root'])
    middle = context(reader, reads, read_birth, expected)
    again = payload_pass(reader, reads, before['root'])
    after = context(reader, reads, read_birth, expected)
    require(before == middle == after and payload == again, 'Observed native context/payload changed')
    value = shared(node(profile), payload)
    return dict(schema='san14.warm-partial-world.v1', shared=value, partial_sha256=digest(value),
                binding=dict(scope_sha256=digest(scope), epoch=epoch, period=period,
                             profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(), side=side,
                             receipt_key=receipt_key, pid=before['pid'], birth=before['birth'],
                             viewer_force=viewer.force, viewer_ruler=viewer.ruler),
                local_context=before, physical_slots=dict(objects=objects.SLOT_COUNT, forces=forces.SLOT_COUNT),
                repeated_reads_equal=True, complete_selected_tables=True,
                atomic_world_snapshot=False, full_world_verified=False, loaded_authorized=False, ready_authorized=False)


def validate_sample(value):
    require(type(value) is dict and value.get('schema') == 'san14.warm-partial-world.v1', 'Wrong observation')
    require(all(value.get(k) is False for k in ('atomic_world_snapshot', 'full_world_verified', 'loaded_authorized', 'ready_authorized')),
            'Unsupported authority claim')
    require(value.get('repeated_reads_equal') is True and value.get('complete_selected_tables') is True,
            'Incomplete partial witness')
    s = value['shared']; validate_node(s['date'])
    require(set(s) == {'contract', 'game_sha256', 'date', 'object_schema', 'force_schema', 'object_payload', 'force_payload'} and
            (s['contract'], s['game_sha256'], s['object_schema'], s['force_schema']) ==
            (CONTRACT, objects.GAME_SHA256, objects.SCHEMA, forces.SCHEMA), 'Partial contract differs')
    require(type(s['object_payload']) is str and type(s['force_payload']) is str and
            len(s['object_payload']) == objects.TABLE_PAYLOAD_SIZE*2 and
            len(s['force_payload']) == forces.TABLE_PAYLOAD_SIZE*2, 'Payload coverage differs')
    payload = dict(objects=bytes.fromhex(s['object_payload']), forces=bytes.fromhex(s['force_payload']))
    objects.ObjectTablePayload(payload['objects']); forces.ForceTablePayload(payload['forces'])
    require(s == shared(s['date'], payload) and digest(s) == value['partial_sha256'], 'Partial digest differs')
    b = value['binding']
    require(set(b) == {'scope_sha256', 'epoch', 'period', 'profile_sha256', 'side', 'receipt_key', 'pid', 'birth', 'viewer_force', 'viewer_ruler'}, 'Binding fields differ')
    for key in ('scope_sha256', 'profile_sha256', 'receipt_key'): require(hexid(b[key]) and int(b[key], 16), 'Missing binding digest')
    require(hexid(b['epoch'], 32) and int(b['epoch'], 16) and b['side'] in ('A', 'B'), 'Invalid epoch/side')
    integer(b['period'], high=2**53); integer(b['pid'], high=2**32); integer(b['birth'])
    integer(b['viewer_force'], high=52); integer(b['viewer_ruler'], high=6000)
    require(value['physical_slots'] == dict(objects=objects.SLOT_COUNT, forces=forces.SLOT_COUNT), 'Slot inventory differs')
    return payload


def compare(left, right, *, max_examples=32):
    """Compare only this named projection; a match never invokes loaded()."""
    integer(max_examples, low=0, high=1001)
    a, b = validate_sample(left), validate_sample(right)
    require(left['binding']['side'] == 'A' and right['binding']['side'] == 'B', 'Need A then B observations')
    for key in ('scope_sha256', 'epoch', 'period', 'profile_sha256'):
        require(left['binding'][key] == right['binding'][key], 'Foreign observation '+key)
    require(left['shared']['date'] == right['shared']['date'], 'Different planning date')
    differences = []; changed_bytes = 0; changed_slots = {}
    for name, _, count, _, _, layout in TABLES:
        offsets = [offset+i for offset, width in layout for i in range(width)]
        width = len(offsets); slots = set()
        for pos, (x, y) in enumerate(zip(a[name], b[name])):
            if x != y:
                changed_bytes += 1; slot = pos//width; slots.add(slot)
                if len(differences) < max_examples:
                    differences.append(dict(table=name, physical_slot=slot, offset=offsets[pos % width], before=x, after=y))
        changed_slots[name] = len(slots)
    return dict(result='PARTIAL_MATCH' if not changed_bytes else 'PARTIAL_DIFFERENCE', contract=CONTRACT,
                partial_hashes=[left['partial_sha256'], right['partial_sha256']], changed_bytes=changed_bytes,
                changed_slots=changed_slots, differences=differences, full_world_verified=False,
                atomic_world_snapshot=False, loaded_authorized=False, ready_authorized=False,
                excluded_domains=['persons', 'armies', 'cities', 'districts', 'hexes', 'tasks', 'RNG',
                                  'events', 'diplomacy dependencies', 'policies and traits', 'other world fields'])
