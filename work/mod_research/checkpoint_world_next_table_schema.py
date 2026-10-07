"""Exact ordinary version-92 CForceData serialized table, without game access.

Payload order is native serialization order, not a contiguous memory range.
All field meanings remain opaque here. This is no full-world/load authority.
"""
from dataclasses import dataclass
import hashlib
import struct

GAME_SHA256 = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
IMAGE_SHA256 = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
SCHEMA = 'san14.cforcedata.serialized-v92.v1'
ROOT_OFFSET = 0xDCA0
SLOT_COUNT = 52
TABLE_TAG = 4
ARCHIVE_VERSION = 92

# Every native Read/Write buffer width in execution order, including helper
# loops. Five 0x1E structures each store fourteen words and one byte; their
# final padding byte is not serialized by this method.
FIELD_LAYOUT = tuple(
    [(0x10, 2)] + [(p, 1) for p in range(0x13, 0x47)] +
    [(p, 1) for p in range(0x47, 0x4C)] + [(0x52, 2)] +
    [(0x54 + g*0x1E + off, width) for g in range(5)
        for off, width in ([(p, 2) for p in range(0, 0x1C, 2)] + [(0x1C, 1)])] +
    [(p, 1) for p in range(0xEA, 0x11E)] +
    [(p, 2) for p in range(0x120, 0x15E, 2)] +
    [(0x15E, 1), (0x168, 1), (0x16A, 2), (0x16C, 2), (0x12, 1),
     (0x4C, 2), (0x4E, 1), (0x4F, 1), (0x50, 1),
     (0x15F, 1), (0x160, 1), (0x161, 1), (0x162, 2), (0x164, 4),
     (0x170, 4), (0x176, 2), (0x179, 1), (0x178, 1), (0x174, 2)] +
    [(p, 1) for p in range(0x17A, 0x184)] +
    [(p, 2) for p in range(0x184, 0x18E, 2)] +
    [(p, 1) for p in range(0x18E, 0x195)]
)
RECORD_SIZE = sum(width for _, width in FIELD_LAYOUT)
TABLE_PAYLOAD_SIZE = RECORD_SIZE*SLOT_COUNT
FRAME_SIZE = TABLE_PAYLOAD_SIZE + 8
SERIALIZED_OFFSETS = tuple(p for off, width in FIELD_LAYOUT for p in range(off, off+width))
assert len(SERIALIZED_OFFSETS) == len(set(SERIALIZED_OFFSETS))


class CoverageError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CoverageError(message)


def _profile(game_build_sha256, archive_version, archive_mode, auxiliary_flag, transform_flag):
    require(type(game_build_sha256) is str and game_build_sha256 == GAME_SHA256, 'unsupported_build')
    require(type(archive_version) is int and archive_version == ARCHIVE_VERSION, 'unsupported_archive_version')
    require(type(archive_mode) is int and archive_mode in (0, 1), 'unsupported_archive_mode')
    require(type(auxiliary_flag) is int and auxiliary_flag == 0, 'unsupported_auxiliary_mode')
    require(type(transform_flag) is int and transform_flag == 0, 'unsupported_stream_transform')


@dataclass(frozen=True)
class ForceTablePayload:
    ordered_payload: bytes

    def __post_init__(self):
        require(type(self.ordered_payload) is bytes and len(self.ordered_payload) == TABLE_PAYLOAD_SIZE,
                'wrong_table_payload_size')

    @property
    def digest(self):
        return hashlib.sha256(SCHEMA.encode('ascii') + b'\x00' +
            struct.pack('<IIII', ROOT_OFFSET, SLOT_COUNT, ARCHIVE_VERSION, RECORD_SIZE) + self.ordered_payload).hexdigest()

    def records(self):
        return {f'force_slot:{i}': self.ordered_payload[i*RECORD_SIZE:(i+1)*RECORD_SIZE]
                for i in range(SLOT_COUNT)}

    def memory_segments(self):
        """Stable slot -> exact field (memory offset, bytes), native field order."""
        result = {}
        for slot, raw in self.records().items():
            at = 0; segments = []
            for offset, width in FIELD_LAYOUT:
                segments.append((offset, raw[at:at+width])); at += width
            result[slot] = tuple(segments)
        return result

    def frame(self):
        return struct.pack('<I', SLOT_COUNT) + self.ordered_payload + struct.pack('<I', TABLE_TAG)

    def evidence(self):
        return dict(schema=SCHEMA, game_build_sha256=GAME_SHA256, archive_version=ARCHIVE_VERSION,
            table='CForceData', root_offset=ROOT_OFFSET, physical_slots=SLOT_COUNT,
            record_serialized_bytes=RECORD_SIZE, field_layout=FIELD_LAYOUT,
            serialized_payload_bytes=TABLE_PAYLOAD_SIZE, isolated_native_frame_bytes=FRAME_SIZE,
            payload_sha256=self.digest, field_semantics='OPAQUE',
            archive_version_requires_external_provenance=True,
            stream_transform_flag=0, stream_transform_requires_external_provenance=True,
            memory_record_allocation_stride_verified=False, all_runtime_fields_classified=False,
            full_world_verified=False, current_world_provenance_verified=False,
            authorize_load_or_ready=False)


def validate_payload_records(records, *, game_build_sha256, archive_version, transform_flag,
                             archive_mode=0, auxiliary_flag=0):
    _profile(game_build_sha256, archive_version, archive_mode, auxiliary_flag, transform_flag)
    require(type(records) is dict and all(type(k) is int for k in records), 'invalid_physical_slot_keys')
    require(set(records) == set(range(SLOT_COUNT)), 'missing_or_extra_physical_slots')
    require(all(type(v) is bytes and len(v) == RECORD_SIZE for v in records.values()), 'wrong_record_payload')
    return ForceTablePayload(b''.join(records[i] for i in range(SLOT_COUNT)))


def decode_native_table_frame(frame, *, game_build_sha256, archive_version, transform_flag,
                              auxiliary_flag=0):
    _profile(game_build_sha256, archive_version, 1, auxiliary_flag, transform_flag)
    require(type(frame) is bytes and len(frame) == FRAME_SIZE, 'wrong_isolated_frame_extent')
    require(struct.unpack_from('<I', frame)[0] == SLOT_COUNT, 'wrong_physical_slot_count')
    require(struct.unpack_from('<I', frame, len(frame)-4)[0] == TABLE_TAG, 'wrong_table_tag')
    return ForceTablePayload(frame[4:-4])


def compare_payloads(left, right):
    require(type(left) is ForceTablePayload and type(right) is ForceTablePayload, 'wrong_payload_type')
    changed = []
    for slot in range(SLOT_COUNT):
        a = left.ordered_payload[slot*RECORD_SIZE:(slot+1)*RECORD_SIZE]
        b = right.ordered_payload[slot*RECORD_SIZE:(slot+1)*RECORD_SIZE]
        diff = [dict(object_offset=offset, before=a[i], after=b[i])
                for i, offset in enumerate(SERIALIZED_OFFSETS) if a[i] != b[i]]
        if diff:
            changed.append(dict(physical_slot=slot, changed_bytes=diff))
    return dict(schema=SCHEMA, observed_table_equal=not changed, changed_records=changed,
        compared_physical_slots=SLOT_COUNT, compared_payload_bytes=TABLE_PAYLOAD_SIZE,
        full_world_verified=False, current_world_provenance_verified=False, authorize_load_or_ready=False)
