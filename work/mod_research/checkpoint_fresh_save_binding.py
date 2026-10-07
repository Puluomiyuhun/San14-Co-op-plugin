"""Trusted local fresh-save bytes -> existing room checkpoint publication.

There is deliberately no network handler, process discovery, native Submit,
Ready transition or guest-load call here. The configured artifact reader must
belong to the retained local native owner. A decoded packet proves structure
and hashes, not the identity of its sender. Never bind this reader to client
JSON, an arbitrary uploaded file, or a historical replay archive.

The caller must maintain real input/write exclusion while saving and observing
the settled world. Equal observations here are not an input lock or complete
world coverage. The current native driver supports only two requests.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Callable, Mapping

from checkpoint_fresh_save_packet import DecodedArtifact
from checkpoint_room_lifecycle import CheckpointRoom
from authoritative_sync import (CheckpointPackage, PeriodCoordinator, canonical,
    digest, hexid, integer, next_node, scope_from_room, sha, validate_node)


class FreshSaveBindingError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise FreshSaveBindingError(reason)


def _u64(value, *, nonzero=False):
    return type(value) is int and (1 if nonzero else 0) <= value < 2**64


@dataclass(frozen=True)
class LocalWorldObservation:
    """A trusted local observation; constructing this is not native evidence.

    world_sha256 describes exactly state_contract's coverage, never an implied
    hash of all game memory. In tests the binding source_kind is FIXTURE_ONLY.
    """
    attachment: str
    year: int
    month: int
    day: int
    force: int
    ruler: int
    state_contract: str
    world_sha256: str
    safe_boundary: bool

    def value(self):
        return dict(attachment=self.attachment,
            node=dict(year=self.year, month=self.month, day=self.day,
                      phase='PLANNING_BOUNDARY'),
            force=self.force, ruler=self.ruler, state_contract=self.state_contract,
            world_sha256=self.world_sha256, safe_boundary=self.safe_boundary)


@dataclass(frozen=True)
class SaveReservation:
    """Native request data only. Does not itself authorize or submit a save."""
    generation: int
    binding_sha256: str
    request: Mapping


class FreshSaveBinding:
    """One retained local owner, one room, at most two immutable reservations.

    Construct after CheckpointRoom.bind_coordinator at initial planning.
    reserve() captures the post-simulation settled boundary before Submit.
    The trusted owner submits reservation.request, then publish() obtains its
    CopyArtifact export through the configured local reader. The stable native
    room_epoch is NOT PeriodCoordinator.epoch, which rotates every period.

    Any uncertain completion or changed captured boundary latches HELD. There
    is no recovery/reset, no request replay and no coordinator rollback here.
    """
    def __init__(self, room: CheckpointRoom, coordinator: PeriodCoordinator, *,
                 native_room_id: bytes, native_room_epoch: int,
                 artifact_reader: Callable[[int], DecodedArtifact],
                 source_kind: str):
        require(isinstance(room, CheckpointRoom) and type(coordinator) is PeriodCoordinator,
                'Trusted checkpoint room/coordinator required')
        require(type(native_room_id) is bytes and len(native_room_id) == 32 and
                any(native_room_id), 'Native room id must be nonzero bytes32')
        require(_u64(native_room_epoch, nonzero=True), 'Native room epoch must be nonzero uint64')
        require(callable(artifact_reader), 'A retained local artifact reader is required')
        require(source_kind in ('FIXTURE_ONLY', 'LOCAL_NATIVE_PROVIDER'), 'Unknown local provider kind')
        self.room, self.coordinator = room, coordinator
        self._native_room_id, self._native_room_epoch = native_room_id, native_room_epoch
        self._reader, self._source_kind = artifact_reader, source_kind
        self._held = None
        self._publication_cleanup = None
        self._records = {}
        with room.lock, coordinator.lock:
            room._bound(coordinator)
            require(coordinator.phase == 'PLANNING' and coordinator.period == 1 and
                    coordinator.connected == {'A', 'B'}, 'Bind before the first simulation')
            self._scope = deepcopy(scope_from_room(room))
            require(self._scope == coordinator.scope, 'Coordinator room scope differs')
            self._host_attachment = coordinator.attachments['A']
            self._state_contract = coordinator.state_contract

    def _available(self):
        require(self._held is None, 'Fresh save binding held: ' + str(self._held))

    def _capture_boundary(self):
        c = self.coordinator
        self.room._bound(c)
        require(scope_from_room(self.room) == self._scope == c.scope and
                c.state_contract == self._state_contract and
                c.attachments['A'] == self._host_attachment,
                'Room scope, host attachment or state contract changed')
        require(c.phase == 'RUNNING' and c.event is None and c.connected == {'A', 'B'},
                'No running authority at a settled export boundary')
        require(type(c.seal) is dict and c.seal.get('epoch') == c.epoch and
                c.seal.get('period') == c.period and hexid(c.seal.get('id'), 32) and
                integer(c.seal.get('sequence')) and hexid(c.seal.get('prefix_sha256')),
                'No current sealed command prefix')
        require(not any(c.inflight.values()), 'Commands are still pending')
        return dict(scope=deepcopy(self._scope), epoch=c.epoch, period=c.period,
            cut={k: c.seal[k] for k in ('sequence', 'prefix_sha256')},
            seal=deepcopy(c.seal), node=next_node(c.node),
            attachments=deepcopy(c.attachments), state_contract=c.state_contract,
            connections={p: row['connection'] for p, row in self.room.players.items()})

    def _observation(self, observation, boundary):
        require(type(observation) is LocalWorldObservation,
                'Independent trusted local world observation is required')
        v = observation.value()
        validate_node(v['node'])
        require(v['attachment'] == boundary['attachments']['A'] and
                hexid(v['attachment'], 32) and v['node'] == boundary['node'] and
                v['state_contract'] == boundary['state_contract'] and
                hexid(v['world_sha256']) and v['safe_boundary'] is True and
                type(v['force']) is int and v['force'] == self._scope['bindings']['A']['force_id'] and
                type(v['ruler']) is int and 0 <= v['ruler'] < 1000,
                'World observation does not describe this settled host boundary')
        return v

    def reserve(self, generation: int, filename: str,
                observation: LocalWorldObservation) -> SaveReservation:
        """Freeze full protocol context before the caller's native Submit.

        Reservation consumes this local generation even if a later native
        Submit fails. It never retries a native request or reuses its filename.
        """
        with self.room.lock, self.coordinator.lock:
            self._available()
            require(_u64(generation, nonzero=True) and generation not in self._records,
                    'Invalid or already reserved save generation')
            require(type(filename) is str and re.fullmatch(r'mp[0-9a-f]{8}\.s14', filename),
                    'Native save filename must be mp + eight lowercase hex digits + .s14')
            require(len(self._records) < 2, 'This retained native owner supports only two saves')
            require(all(r['stage'] == 'PUBLISHED' for r in self._records.values()),
                    'A previous export remains pending or uncertain')
            boundary = self._capture_boundary()
            world = self._observation(observation, boundary)
            if self._records:
                previous = next(reversed(self._records.values()))
                require(generation > previous['request']['generation'] and
                        filename != previous['request']['filename'] and
                        boundary['period'] == previous['boundary']['period'] + 1 and
                        boundary['epoch'] != previous['boundary']['epoch'],
                        'Save generation, filename or period was reused/skipped')
            else:
                require(boundary['period'] == 1, 'Initial save period was skipped')
            q = dict(generation=generation, room_epoch=self._native_room_epoch,
                period=boundary['period'], cut=boundary['cut']['sequence'], room_id=self._native_room_id,
                year=world['node']['year'], month=world['node']['month'], day=world['node']['day'],
                force=world['force'], ruler=world['ruler'], reserved=0, filename=filename)
            descriptor = dict(schema='san14.fresh-save-room-binding.v1', boundary=boundary,
                native_request={**q, 'room_id': q['room_id'].hex()},
                source_kind=self._source_kind, observation=world)
            binding_sha = digest(descriptor)
            self._records[generation] = dict(stage='RESERVED', request=q, boundary=boundary,
                observation=world, descriptor=descriptor, binding_sha256=binding_sha,
                ordinal=len(self._records) + 1, package=None)
            return SaveReservation(generation, binding_sha, MappingProxyType(dict(q)))

    def _artifact(self, artifact, record):
        require(type(artifact) is DecodedArtifact, 'Only the configured local packet decoder output is accepted')
        require(type(artifact.request) is MappingProxyType and type(artifact.report) is MappingProxyType,
                'Artifact request and report must be immutable mappings')
        q, r = dict(artifact.request), dict(artifact.report)
        require(set(q) == set(record['request']) and q == record['request'],
                'Native artifact belongs to another request/boundary')
        for name, expected in record['request'].items():
            require(type(q[name]) is type(expected), 'Native request field type differs: ' + name)
        numbers = ('status', 'error', 'generation', 'active', 'entries', 'exits', 'abnormal',
            'first_call', 'last_call', 'save_state', 'intents', 'flushed', 'binds', 'queues',
            'phase_mask', 'worker_started', 'worker_joined', 'native_success', 'finalizer_returned',
            'return_matched', 'original_returned', 'stop_after_commit', 'executor_thread', 'completed_requests')
        flags = ('full_world', 'room_ready', 'file_bytes_verified')
        require(set(r) == set(numbers + flags) and all(_u64(r[k]) for k in numbers) and
                all(type(r[k]) is bool for k in flags), 'Malformed native completion report')
        require(r['status'] == 5 and r['generation'] == q['generation'] and
                all(r[k] == 0 for k in ('error', 'active', 'abnormal', 'stop_after_commit')) and
                all(r[k] == 1 for k in ('intents', 'flushed', 'binds', 'queues', 'worker_started',
                    'worker_joined', 'native_success', 'finalizer_returned', 'return_matched')) and
                r['phase_mask'] == 31 and r['entries'] == r['exits'] >= r['original_returned'] >= 7 and
                0 < r['first_call'] < r['last_call'] and r['save_state'] > 0 and r['executor_thread'] > 0 and
                r['completed_requests'] == record['ordinal'] and
                r['file_bytes_verified'] is True and r['full_world'] is False and r['room_ready'] is False,
                'Native save did not complete cleanly for this retained generation')
        require(type(artifact.data) is bytes and 0 < len(artifact.data) <= 16 * 1024 * 1024 and
                hexid(artifact.sha256) and sha(artifact.data) == artifact.sha256,
                'Retained native save bytes do not match their hash')
        return q, r

    def _hold(self, record, reason):
        self._held = reason
        if record is not None:
            record['stage'] = 'HELD'
        self._revoke_downloads()

    def _revoke_downloads(self):
        """Retire possibly published bytes; never claim success after an error."""
        self._publication_cleanup = dict(attempted=True, closed=False, error=None)
        try:
            self.room.close_checkpoints()
            require(self.room.checkpoint_status()['closed'] is True and
                    self.room.checkpoint_status()['download_available'] is False and
                    self.room.download_endpoint.status()['active_connection_owners'] == 0,
                    'Checkpoint download retirement is not confirmed')
            self._publication_cleanup['closed'] = True
        except BaseException as exc:
            self._publication_cleanup['error'] = type(exc).__name__

    def hold(self, reason: str):
        """Stop publication and retire downloads after local uncertainty.

        This does not stop the native owner or undo a guest load. The caller
        must inspect publication_cleanup, including any unconfirmed retirement.
        """
        require(type(reason) is str and 1 <= len(reason) <= 120, 'Bad hold reason')
        with self.room.lock, self.coordinator.lock:
            self._hold(None, reason)

    def publish(self, generation: int,
                observe_world: Callable[[], LocalWorldObservation]) -> CheckpointPackage:
        """Copy a completed local artifact and publish through the existing room.

        CopyArtifact may be idempotent, but uncertain publication is not retried
        here. Byte-download retries belong to the existing artifact endpoint.
        The configured reader is called without room locks, then all captured
        context is checked again before publishing. It must not submit a save.
        A fresh local world observation is requested AFTER copying the bytes;
        the caller must still maintain input/write exclusion through publish.
        """
        with self.room.lock, self.coordinator.lock:
            self._available()
            require(_u64(generation, nonzero=True) and generation in self._records,
                    'No such local save reservation')
            require(callable(observe_world), 'A fresh trusted local world observer is required')
            record = self._records[generation]
            require(record['stage'] == 'RESERVED', 'Export already attempted; do not retry publication')
            try:
                require(self._capture_boundary() == record['boundary'], 'Captured room boundary changed')
            except BaseException:
                self._hold(record, 'BOUNDARY_CHANGED_BEFORE_COPY')
                raise
            record['stage'] = 'COPYING'
        try:
            artifact = self._reader(generation)
            q, r = self._artifact(artifact, record)
            observation = observe_world()
        except BaseException:
            with self.room.lock, self.coordinator.lock:
                self._hold(record, 'ARTIFACT_COPY_OR_VALIDATION_FAILED')
            raise
        with self.room.lock, self.coordinator.lock:
            self._available()
            try:
                require(record['stage'] == 'COPYING' and self._capture_boundary() == record['boundary'],
                        'Captured boundary changed while obtaining local bytes')
                require(self._observation(observation, record['boundary']) == record['observation'],
                        'Host world changed during the save')
                # This is provenance plus the exact captured protocol binding,
                # not a new world/native-load permission or a filesystem path.
                adapter = dict(schema='san14.fresh-save-adapter.v1', source_kind=self._source_kind,
                    binding_sha256=record['binding_sha256'], binding=record['descriptor'],
                    native_request={**q, 'room_id': q['room_id'].hex()}, native_report=r,
                    artifact=dict(size=len(artifact.data), sha256=artifact.sha256),
                    current_host_observation=record['observation'],
                    full_world_verified=False, native_load_authorized=False,
                    native_gameplay_enabled=False, ready_authorized=False)
                b = record['boundary']
                package = CheckpointPackage(b['scope'], b['epoch'], b['period'], b['cut'], b['node'],
                    b['state_contract'], record['observation']['world_sha256'],
                    {'world.s14': artifact.data, 'adapter.json': canonical(adapter)}, source_player='A')
                self.coordinator.offer_checkpoint('A', package.manifest)
                self.room.install_offered_checkpoint(self.coordinator, package)
                record['package'], record['stage'] = package, 'PUBLISHED'
                return package
            except BaseException:
                # offer_checkpoint may already have advanced the coordinator.
                # Never roll it back or silently issue the native save again.
                self._hold(record, 'CHECKPOINT_PUBLICATION_FAILED')
                raise

    def status(self):
        with self.room.lock, self.coordinator.lock:
            return dict(source_kind=self._source_kind, held_reason=self._held,
                publication_cleanup=deepcopy(self._publication_cleanup),
                reservations=[dict(generation=g, stage=r['stage'], period=r['boundary']['period'],
                    binding_sha256=r['binding_sha256'],
                    checkpoint_id=r['package'].checkpoint_id if r['package'] else None)
                    for g, r in self._records.items()],
                remaining_reservations=2-len(self._records), native_submit_called=False,
                full_world_verified=False, native_load_authorized=False,
                native_gameplay_enabled=False, ready_authorized=False)
