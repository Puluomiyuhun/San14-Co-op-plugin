"""Bound local A-owner named-pipe client; no game discovery or installation.

The owning launcher supplies a pinned server PID/birth and a private secret.
Submit is consumed before transport entry. Lost replies close the channel and
hold the bound room; there is no reconnect or Submit replay. Copy polling does
not resubmit native work. This module never asserts world/input completeness.
"""
from __future__ import annotations

import ctypes as C
from dataclasses import dataclass, field
import math
import re
import struct
import threading
import time
from types import MappingProxyType

from checkpoint_session_channel import WinPipeTransport
from checkpoint_fresh_save_packet import REQUEST as SAVE_REQUEST, REQUEST_FIELDS, decode_packet
from checkpoint_fresh_save_binding import SaveReservation

MAGIC = 0x31465341
VERSION = 1
PREFIX = struct.Struct('<IHHQ32s32s')
RESPONSE = struct.Struct('<IHHQII32s')
SNAPSHOT_PAYLOAD = struct.Struct('<10I2QI')
REQUEST_BYTES = PREFIX.size + SAVE_REQUEST.size
MAX_PAYLOAD = SNAPSHOT_PAYLOAD.size + 284 + 16 * 1024 * 1024
SNAPSHOT, SUBMIT, COPY, STOP = 1, 2, 3, 4
OK, NOT_READY, STOPPED = 0, 7, 8
SNAPSHOT_FIELDS = ('owner_error', 'initialized', 'armed', 'stopped', 'save_status',
    'save_error', 'completed_requests', 'binds', 'queues', 'user_subset_held',
    'generation', 'active_scopes', 'capabilities')
assert REQUEST_BYTES == 168 and RESPONSE.size == 56 and SNAPSHOT_PAYLOAD.size == 60


class ASaveChannelError(RuntimeError):
    pass


class ASaveOutcomeUnknown(ASaveChannelError):
    pass


def require(ok, reason):
    if not ok:
        raise ASaveChannelError(reason)


def _uint(value, bits=64, nonzero=False):
    return type(value) is int and (1 if nonzero else 0) <= value < 2**bits


@dataclass(frozen=True)
class Endpoint:
    pipe: str
    server_pid: int
    server_birth: int
    secret: bytes = field(repr=False)

    def validate(self):
        prefix = '\\\\.\\pipe\\san14-a-save-'
        require(type(self.pipe) is str and self.pipe.startswith(prefix) and
                re.fullmatch('[0-9a-f]{32}', self.pipe[len(prefix):]) is not None,
                'Explicit local A-save pipe required')
        require(_uint(self.server_pid, 32, True) and _uint(self.server_birth, 64, True),
                'Bound server PID/birth required')
        require(type(self.secret) is bytes and len(self.secret) == 32 and any(self.secret),
                'Private nonzero bytes32 secret required')


class ASavePipeTransport(WinPipeTransport):
    """Reuse verified Windows identity and cancellation code, with A framing.

    The frozen Guest transport's constructor calls Endpoint.validate and
    authenticates the kernel server PID/birth. Its _io drains cancellation or
    quarantines Python buffers. Only the fixed Guest exchange format changes.
    """
    def _read_exact(self, size, deadline):
        data = bytearray()
        while len(data) < size:
            buffer = C.create_string_buffer(min(65536, size-len(data)))
            received = self._io(False, buffer, len(buffer), deadline)
            data.extend(buffer.raw[:received])
        return bytes(data)

    def exchange(self, request, timeout):
        require(type(request) is bytes and len(request) == REQUEST_BYTES, 'Bad A request frame')
        deadline = time.monotonic() + timeout
        offset = 0
        while offset < len(request):
            raw = C.create_string_buffer(request[offset:])
            offset += self._io(True, raw, len(request)-offset, deadline)
        header = self._read_exact(RESPONSE.size, deadline)
        magic, version, _, _, _, size, _ = RESPONSE.unpack(header)
        require((magic, version) == (MAGIC, VERSION) and SNAPSHOT_PAYLOAD.size <= size <= MAX_PAYLOAD,
                'Invalid A response framing')
        return header + self._read_exact(size, deadline)


def request_bytes(value):
    """Encode the exact caller-reserved native Request, never arbitrary paths."""
    require(type(value) is MappingProxyType and set(value) == set(REQUEST_FIELDS),
            'Immutable complete native request required')
    q = dict(value)
    require(all(_uint(q[k], nonzero=k != 'cut') for k in ('generation', 'room_epoch', 'period', 'cut')) and
            type(q['room_id']) is bytes and len(q['room_id']) == 32 and any(q['room_id']),
            'Invalid native room/request identity')
    require(_uint(q['year'], 16, True) and q['year'] <= 9999 and _uint(q['ruler'], 16) and q['ruler'] < 1000 and
            type(q['month']) is int and 1 <= q['month'] <= 12 and
            type(q['day']) is int and q['day'] in (1, 11, 21) and
            type(q['force']) is int and 1 <= q['force'] <= 51 and type(q['reserved']) is int and q['reserved'] == 0,
            'Invalid native save boundary')
    require(type(q['filename']) is str and re.fullmatch(r'mp[0-9a-f]{8}\.s14', q['filename']) is not None,
            'Invalid native save basename')
    q['filename'] = q['filename'].encode('ascii') + b'\0\0'
    return SAVE_REQUEST.pack(*(q[k] for k in REQUEST_FIELDS))


class ASaveClient:
    def __init__(self, endpoint: Endpoint, *, on_fault, timeout=5.0,
                 transport_factory=ASavePipeTransport):
        require(type(endpoint) is Endpoint, 'Typed A-owner endpoint required')
        endpoint.validate()
        require(callable(on_fault), 'A bound room-hold callback is required')
        require(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 30,
                'Bounded A-owner timeout required')
        self.endpoint, self.timeout, self._on_fault = endpoint, float(timeout), on_fault
        self._lock = threading.RLock()
        self._transport = None
        self._sequence = 0
        self._submitted = {}
        self._fault = self._callback_error = None
        self._closed = self._quarantined = self._stop_requested = False
        self._last = None
        try:
            self._transport = transport_factory(endpoint)
        except BaseException:
            self._latch('A_IPC_CONNECT_FAILED')
            raise

    def _latch(self, reason):
        if self._fault is None:
            self._fault = reason
            try:
                self._on_fault(reason)
            except BaseException as exc:
                self._callback_error = type(exc).__name__
        if self._transport is not None:
            self._quarantined = bool(getattr(self._transport, 'quarantined', False))
            try:
                self._transport.close()
            except BaseException as exc:
                self._callback_error = self._callback_error or type(exc).__name__
                self._quarantined = True
            self._transport = None

    def _decode(self, raw, op, sequence, binding):
        require(type(raw) is bytes and len(raw) >= RESPONSE.size+SNAPSHOT_PAYLOAD.size,
                'Incomplete A-owner reply')
        magic, version, actual_op, actual_seq, status, size, actual_binding = RESPONSE.unpack_from(raw)
        require((magic, version, actual_op, actual_seq, actual_binding) ==
                (MAGIC, VERSION, op, sequence, binding), 'Stale or foreign A-owner reply')
        require(0 <= status <= STOPPED and SNAPSHOT_PAYLOAD.size <= size <= MAX_PAYLOAD and
                len(raw) == RESPONSE.size+size, 'Invalid A-owner reply size/status')
        values = SNAPSHOT_PAYLOAD.unpack_from(raw, RESPONSE.size)
        snap = dict(zip(SNAPSHOT_FIELDS, values))
        require(snap['capabilities'] == 0 and snap['save_status'] <= 8 and
                all(snap[k] in (0, 1) for k in ('initialized', 'armed', 'stopped', 'user_subset_held')) and
                snap['completed_requests'] <= 2, 'Unsupported A-owner snapshot')
        packet = raw[RESPONSE.size+SNAPSHOT_PAYLOAD.size:]
        require((op == COPY and status == OK and len(packet) > 284) or
                ((op != COPY or status != OK) and not packet), 'Unexpected A-owner payload')
        self._last = snap
        # Historical Artifact reports do not reflect a later Owner.Stop.
        # Every response supplies the current owner lifecycle separately.
        if snap['owner_error'] or snap['save_error'] or (snap['stopped'] and op != STOP):
            self._latch('A_IPC_OWNER_UNAVAILABLE')
            raise ASaveChannelError('A-owner is stopped or has failed')
        require(snap['initialized'] == 1 and snap['armed'] == 1, 'A-owner is not initialized/armed')
        if status == NOT_READY and op == COPY:
            return snap, None
        require(status == OK, 'A-owner rejected request')
        if op == STOP:
            require(snap['stopped'] == 1, 'Owner Stop was not observed')
        return snap, decode_packet(packet) if op == COPY else None

    def _request(self, op, binding=bytes(32), native_request=bytes(SAVE_REQUEST.size)):
        require(not self._closed and self._fault is None and self._transport is not None,
                'A-owner channel closed or uncertain; no reconnect/replay')
        self._sequence += 1
        seq = self._sequence
        raw = PREFIX.pack(MAGIC, VERSION, op, seq, self.endpoint.secret, binding) + native_request
        try:
            response = self._transport.exchange(raw, self.timeout)
            return self._decode(response, op, seq, binding)
        except BaseException:
            self._latch('A_IPC_OUTCOME_UNKNOWN')
            raise

    def snapshot(self):
        with self._lock:
            return dict(self._request(SNAPSHOT)[0])

    def submit(self, reservation: SaveReservation):
        with self._lock:
            require(type(reservation) is SaveReservation and not self._stop_requested,
                    'Caller-reserved save required; owner cannot be stopping')
            require(type(reservation.binding_sha256) is str and
                    re.fullmatch('[0-9a-f]{64}', reservation.binding_sha256) is not None,
                    'Full reservation binding hash required')
            request = request_bytes(reservation.request)
            generation = reservation.generation
            require(_uint(generation, nonzero=True) and generation == reservation.request['generation'] and
                    generation not in self._submitted and len(self._submitted) < 2,
                    'Submit generation already consumed or unsupported')
            binding = bytes.fromhex(reservation.binding_sha256)
            require(any(binding), 'Nonzero reservation binding hash required')
            # Before any I/O: a lost accepted reply cannot allow a second Submit.
            self._submitted[generation] = (binding, dict(reservation.request))
            snap, _ = self._request(SUBMIT, binding, request)
            if snap['generation'] != generation:
                self._latch('A_IPC_SUBMIT_BINDING_FAILED')
                raise ASaveChannelError('Submit reply belongs to another generation')
            return dict(snap)

    def copy(self, generation):
        with self._lock:
            require(_uint(generation, nonzero=True) and generation in self._submitted,
                    'Only a locally submitted generation can be copied')
            binding, expected = self._submitted[generation]
            request = struct.pack('<Q', generation) + bytes(SAVE_REQUEST.size-8)
            _, artifact = self._request(COPY, binding, request)
            if artifact is not None:
                try:
                    require(dict(artifact.request) == expected,
                            'CopyArtifact native request differs from the submitted reservation')
                    require(artifact.report['stop_after_commit'] == 0,
                            'CopyArtifact observed Stop after the irreversible save boundary')
                except BaseException:
                    self._latch('A_IPC_ARTIFACT_BINDING_FAILED')
                    raise
            return artifact

    def wait_artifact(self, generation, *, timeout=10.0):
        require(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 30,
                'Bounded artifact wait required')
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            artifact = self.copy(generation)
            if artifact is not None:
                return artifact
            time.sleep(.01)
        with self._lock:
            self._latch('A_IPC_ARTIFACT_TIMEOUT')
        raise ASaveOutcomeUnknown('A-owner artifact timed out; native Submit must not be replayed')

    def stop(self):
        with self._lock:
            require(not self._stop_requested, 'Stop already requested')
            self._stop_requested = True
            # Deliberate Stop must revoke any previously published download too.
            try:
                self._on_fault('A_IPC_STOP_REQUESTED')
            except BaseException as exc:
                self._callback_error = type(exc).__name__
            return dict(self._request(STOP)[0])

    def close(self):
        with self._lock:
            if not self._closed:
                self._latch('A_IPC_CHANNEL_CLOSED')
                self._closed = True
            return self.status()

    def status(self):
        with self._lock:
            return dict(sequence=self._sequence, submitted_generations=list(self._submitted),
                connected=self._transport is not None, closed=self._closed,
                fault=self._fault, callback_error=self._callback_error,
                io_quarantined=self._quarantined, stop_requested=self._stop_requested,
                owner_snapshot=dict(self._last) if self._last is not None else None,
                automatic_reconnect=False, automatic_submit_retry=False,
                native_gameplay_enabled=False, full_world_verified=False)
