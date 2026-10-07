"""Decode a retained A-owner export, without game calls or source attestation.

Even a well-formed packet is not proof that it came from SAN14. The local
coordinator must own and authenticate its producer, bind the request BEFORE
submission, and independently observe the current world. Never accept a peer's
packet as permission to publish, load, mark Ready, or assert full coverage.
"""
from dataclasses import dataclass
import hashlib
import re
import struct
from types import MappingProxyType
from typing import Mapping

MAGIC = b'S14FSV01'
HEADER_BYTES = 284
MAX_BYTES = 64 * 1024 * 1024
PREFIX = struct.Struct('<8sIIQ')
REQUEST = struct.Struct('<4Q32sHH4B16s')
REPORT = struct.Struct('<2I8Q17I')
REQUEST_FIELDS = ('generation', 'room_epoch', 'period', 'cut', 'room_id',
                  'year', 'ruler', 'month', 'day', 'force', 'reserved', 'filename')
REPORT_FIELDS = ('status', 'error', 'generation', 'active', 'entries', 'exits',
    'abnormal', 'first_call', 'last_call', 'save_state', 'intents', 'flushed',
    'binds', 'queues', 'phase_mask', 'worker_started', 'worker_joined',
    'native_success', 'finalizer_returned', 'return_matched', 'original_returned',
    'stop_after_commit', 'executor_thread', 'completed_requests',
    'full_world', 'room_ready', 'file_bytes_verified')
assert PREFIX.size + REQUEST.size + REPORT.size + 32 == HEADER_BYTES


class PacketError(ValueError):
    pass


def _require(ok, message):
    if not ok:
        raise PacketError(message)


@dataclass(frozen=True)
class DecodedArtifact:
    request: Mapping
    report: Mapping
    data: bytes
    sha256: str


def decode_packet(raw: bytes) -> DecodedArtifact:
    _require(type(raw) is bytes, 'Immutable local packet bytes required')
    _require(HEADER_BYTES < len(raw) <= HEADER_BYTES + MAX_BYTES, 'Invalid packet size')
    magic, version, header_size, size = PREFIX.unpack_from(raw)
    _require(magic == MAGIC and version == 1 and header_size == HEADER_BYTES,
             'Unsupported export packet format')
    _require(0 < size <= MAX_BYTES and len(raw) == HEADER_BYTES + size,
             'Truncated, oversized or trailing export bytes')
    q = dict(zip(REQUEST_FIELDS, REQUEST.unpack_from(raw, PREFIX.size)))
    _require(q['generation'] > 0 and q['room_epoch'] > 0 and q['period'] > 0
             and any(q['room_id']) and 1 <= q['year'] <= 9999
             and 1 <= q['month'] <= 12 and q['day'] in (1, 11, 21)
             and 1 <= q['force'] <= 51 and q['ruler'] < 1000 and q['reserved'] == 0,
             'Invalid saved request identity')
    _require(re.fullmatch(rb'mp[0-9a-f]{8}\.s14\x00\x00', q['filename']) is not None,
             'Invalid native save basename')
    q['filename'] = q['filename'][:-2].decode('ascii')
    r = dict(zip(REPORT_FIELDS, REPORT.unpack_from(raw, PREFIX.size + REQUEST.size)))
    _require(r['status'] == 5 and r['error'] == 0 and r['generation'] == q['generation']
             and r['active'] == r['abnormal'] == 0 and r['entries'] >= 7
             and r['entries'] == r['exits'] and 7 <= r['original_returned'] <= r['entries']
             and 0 < r['first_call'] < r['last_call'] and r['save_state'] > 0,
             'Native save has no complete balanced return')
    _require(all(r[k] == 1 for k in ('intents', 'flushed', 'binds', 'queues',
             'worker_started', 'worker_joined', 'native_success', 'finalizer_returned',
             'return_matched')) and r['phase_mask'] == 31 and r['stop_after_commit'] in (0, 1)
             and r['executor_thread'] > 0 and 1 <= r['completed_requests'] <= 2,
             'Native save lifecycle is incomplete')
    _require(r['full_world'] == r['room_ready'] == 0 and r['file_bytes_verified'] == 1,
             'Unsupported authority or unverified bytes')
    for name in ('full_world', 'room_ready', 'file_bytes_verified'):
        r[name] = bool(r[name])
    expected = raw[HEADER_BYTES - 32:HEADER_BYTES].hex()
    data = raw[HEADER_BYTES:]
    _require(hashlib.sha256(data).hexdigest() == expected, 'Native export hash mismatch')
    return DecodedArtifact(MappingProxyType(q), MappingProxyType(r), data, expected)
