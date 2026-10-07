"""CObjectData ordinary-archive payload schema, not a full-world validator.

Inputs are explicit bytes/physical-slot records, never a game process or a full
encoded .s14 file. See native replay evidence before adapting a capture source.
"""
from dataclasses import dataclass
import hashlib
import json
import struct

GAME_SHA256 = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
IMAGE_SHA256 = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
SCHEMA = 'san14.cobjectdata.serialized-fields.v1'
ROOT_OFFSET = 0x6D808
SLOT_COUNT = 3001
TABLE_TAG = 8
FIELDS = ((0x10, 2), (0x12, 1), (0x13, 1), (0x14, 2), (0x16, 1), (0x17, 1))
PAYLOAD_SIZE = 8
TABLE_PAYLOAD_SIZE = SLOT_COUNT * PAYLOAD_SIZE
FRAMED_SIZE = TABLE_PAYLOAD_SIZE + 8


class CoverageError(ValueError):
    pass


def require(ok, message):
    if not ok: raise CoverageError(message)


@dataclass(frozen=True)
class ObjectTablePayload:
    """All physical slots in order, including sentinel/inactive slots.

    Completeness here means this one serialized table's byte coverage only.
    No whole-file placement, provenance, time/phase or world equality follows.
    """
    ordered_payload: bytes

    def __post_init__(self):
        require(type(self.ordered_payload) is bytes and len(self.ordered_payload) == TABLE_PAYLOAD_SIZE,
                'exact_3001_slot_payload_required')

    @property
    def digest(self):
        return hashlib.sha256(SCHEMA.encode('ascii') + b'\0' +
            struct.pack('<II', ROOT_OFFSET, SLOT_COUNT) + self.ordered_payload).hexdigest()

    def records(self):
        return {f'object_slot:{i}': self.ordered_payload[i*8:(i+1)*8] for i in range(SLOT_COUNT)}

    def frame(self):
        return struct.pack('<I', SLOT_COUNT) + self.ordered_payload + struct.pack('<I', TABLE_TAG)

    def evidence(self):
        return {'schema': SCHEMA, 'root_offset': ROOT_OFFSET, 'physical_slots': SLOT_COUNT,
            'field_ranges': [{'offset': o, 'length': n} for o, n in FIELDS],
            'payload_bytes': TABLE_PAYLOAD_SIZE, 'ordered_payload_sha256': self.digest,
            'stable_locator': 'physical_slot_index_0_to_3000_not_semantic_id',
            'all_this_table_serialized_bytes_present': True,
            'all_object_business_semantics_known': False, 'full_world_verified': False,
            'game_access': False, 'current_world_provenance_verified': False,
            'authorize_load_or_ready': False}


def validate_payload_records(records, *, game_build_sha256, archive_mode=0, auxiliary_flag=0):
    """Validate complete slot coverage; never compare only intersecting IDs.

    Each value is exactly the eight object bytes at offsets10..17. Physical
    slot order is retained. Offset14 is the previously traced durability word;
    all other values remain opaque, including the offset10 word.
    """
    require(game_build_sha256 == GAME_SHA256, 'unsupported_game_build')
    require(type(archive_mode) is int and archive_mode in (0, 1), 'unsupported_archive_mode')
    require(type(auxiliary_flag) is int and auxiliary_flag == 0, 'nonordinary_archive_not_covered')
    require(type(records) is dict and len(records) == SLOT_COUNT and
            all(type(i) is int for i in records) and set(records) == set(range(SLOT_COUNT)),
            'missing_extra_or_noninteger_physical_slot')
    require(all(type(raw) is bytes and len(raw) == PAYLOAD_SIZE for raw in records.values()),
            'wrong_object_payload_length')
    return ObjectTablePayload(b''.join(records[i] for i in range(SLOT_COUNT)))


def decode_native_table_frame(raw, *, game_build_sha256, auxiliary_flag=0):
    """Decode an already isolated native table frame, NOT an encoded save file.

    Strict count/length/tag checks intentionally exceed the native loop's
    count handling. A caller must independently identify this table boundary.
    """
    require(game_build_sha256 == GAME_SHA256, 'unsupported_game_build')
    require(type(auxiliary_flag) is int and auxiliary_flag == 0, 'nonordinary_archive_not_covered')
    require(type(raw) is bytes and len(raw) == FRAMED_SIZE, 'wrong_native_table_frame_length')
    require(struct.unpack_from('<I', raw)[0] == SLOT_COUNT, 'wrong_native_table_count')
    require(struct.unpack_from('<I', raw, len(raw)-4)[0] == TABLE_TAG, 'wrong_native_table_tag')
    return ObjectTablePayload(raw[4:-4])


def compare_payloads(left, right):
    require(type(left) is ObjectTablePayload and type(right) is ObjectTablePayload, 'validated_tables_required')
    changed = []
    for i in range(SLOT_COUNT):
        a, b = left.ordered_payload[i*8:(i+1)*8], right.ordered_payload[i*8:(i+1)*8]
        if a != b:
            changed.append({'physical_slot': i, 'changed_object_offsets':
                            [0x10+j for j in range(8) if a[j] != b[j]]})
    return {'schema': SCHEMA, 'all_this_table_payloads_equal': not changed,
        'compared_slots': SLOT_COUNT, 'compared_payload_bytes': TABLE_PAYLOAD_SIZE,
        'changed_slots': changed, 'full_world_verified': False, 'authorize_load_or_ready': False}
