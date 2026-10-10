"""Explicit three-checkpoint successor: same-day bootstrap plus two turn ends.
Dedicated three-save native runtime required; no installer is supplied.
Protocol-only: no native permission, game date write, or implicit simulation.
Constructors below are narrow explicit successors of frozen exact-type ports.
"""
from __future__ import annotations
from copy import deepcopy
import secrets
import threading
import time
from typing import Callable
from checkpoint_fresh_save_packet import DecodedArtifact
from authoritative_sync import (PeriodCoordinator, CheckpointPackage, CheckpointReceiver,
    scope_from_room, digest, hexid, integer, next_node, validate_manifest, require)
from room_session import Room
from checkpoint_room_lifecycle import CheckpointRoom
from checkpoint_room_artifacts import CheckpointArtifactService as OldArtifactService
from checkpoint_three_save_binding import ThreeFreshSaveBinding as OldBinding, LocalWorldObservation, _u64
from b_warm_projection import TrustedProjection as OldProjection, need
from b_warm_remote_completion import RemoteCompletionRoom, key_check
import b_warm_world as world


class BootstrapCoordinator(PeriodCoordinator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bootstrap_checkpoint = None
        self.bootstrap_completed = False
        self.initial_node = deepcopy(self.node)

    def begin_bootstrap(self):
        with self.lock:
            require(self.period == 1 and self.phase == 'PLANNING' and
                self.bootstrap_checkpoint is None and not self.bootstrap_completed and
                not self.applied_receipts and self.connected == {'A', 'B'} and
                not self.ready and not any(self.inflight.values()) and self.event is None and
                self.node == self.initial_node and self.reports['A'] == self.reports['B'] and
                self.reports['A']['sequence'] == 0 and
                self.reports['A']['prefix_sha256'] == digest(self.scope),
                'Bootstrap requires unchanged initial zero-command boundary')
            self.seal = dict(id=secrets.token_hex(16), epoch=self.epoch,
                period=self.period, **deepcopy(self.reports['A']))
            self.phase = 'BOOTSTRAP_EXPORT'
            return deepcopy(self.seal)

    def seal_inputs(self):
        with self.lock:
            require(self.bootstrap_completed, 'Formal initial loaded receipt is required')
            return super().seal_inputs()

    def offer_checkpoint(self, source_player, manifest):
        with self.lock:
            if self.bootstrap_completed:
                return super().offer_checkpoint(source_player, manifest)
            require(source_player == 'A', 'Only A publishes bootstrap')
            validate_manifest(manifest)
            require(self.phase == 'BOOTSTRAP_EXPORT' and self.period == 1 and
                self.bootstrap_checkpoint is None and not self.applied_receipts and
                self.connected == {'A', 'B'} and self.event is None and
                not any(self.inflight.values()), 'Bootstrap already attempted or unavailable')
            require(manifest['scope_sha256'] == digest(self.scope) and
                manifest['epoch'] == self.epoch and manifest['period'] == self.period and
                manifest['state_contract'] == self.state_contract and
                manifest['cut'] == {k:self.seal[k] for k in ('sequence','prefix_sha256')} and
                manifest['node'] == self.node == self.initial_node,
                'Bootstrap must preserve actual initial date and sealed context')
            self.manifest = deepcopy(manifest)
            self.checkpoint_id = digest(manifest)
            self.bootstrap_checkpoint = self.checkpoint_id
            self.phase = 'RECONCILING'
            self.bytes_received = False
            self.load_intent = None
            return self.checkpoint_id

    def loaded(self, *args, **kwargs):
        with self.lock:
            result = super().loaded(*args, **kwargs)
            if self.bootstrap_checkpoint in self.applied_receipts:
                self.bootstrap_completed = True
            return result

    def native_binding(self, native_epoch_base):
        """Local Runtime epoch != random wire epoch != fixed native room_epoch.
        Call after begin_bootstrap, or after the genuine next input seal/begin.
        The native controller supports exactly these three checkpoint generations.
        """
        with self.lock:
            require(type(native_epoch_base) is int and 0 < native_epoch_base < 2**64-2,
                'Three native epoch values required')
            require(self.period in (1,2,3) and self.connected == {'A','B'} and self.event is None and
                not any(self.inflight.values()) and type(self.seal) is dict and
                self.seal['epoch'] == self.epoch and self.seal['period'] == self.period,
                'Current sealed native context required')
            initial = self.period == 1
            require((initial and self.phase == 'BOOTSTRAP_EXPORT' and not self.bootstrap_completed) or
                (not initial and self.phase == 'RUNNING' and self.bootstrap_completed),
                'No native binding before authenticated bootstrap completion/input sealing')
            descriptor = dict(schema='san14.three-checkpoint-native-binding.v1',
                scope=deepcopy(self.scope), epoch=self.epoch, period=self.period,
                attachments=deepcopy(self.attachments), node=deepcopy(self.node),
                seal=deepcopy(self.seal), stage='INITIAL_SNAPSHOT' if initial else 'TURN_END')
            return dict(generation=self.period, period=self.period,
                epoch=native_epoch_base+self.period-1, input_digest=digest(descriptor),
                node=deepcopy(self.node) if initial else next_node(self.node),
                descriptor=descriptor)


class _ArtifactService(OldArtifactService):
    def __init__(self, room, coordinator, package, *, lifetime=30, clock=time.monotonic):
        require(isinstance(room, Room) and type(coordinator) is BootstrapCoordinator and
                type(package) is CheckpointPackage, 'Trusted room/coordinator/package required')
        require(type(lifetime) in (int,float) and 1 <= lifetime <= 60, 'Bounded ticket lifetime required')
        self.room = room
        self.coordinator = coordinator
        self.lock = threading.RLock()
        self.clock = clock
        self.lifetime = lifetime
        self.chunks = {}
        self.tickets = {}
        self.channels = {}
        self.ticket_count = 0
        self.closed = False
        # Capture the offered boundary and verify the immutable download copy
        # under the same lock order as issuance/authentication/chunk delivery.
        # The caller may construct directly, without install_offered_checkpoint.
        with room.lock, coordinator.lock:
            self.manifest = package.manifest
            self.checkpoint_id = package.checkpoint_id
            self.scope = scope_from_room(room)
            self.connections = {p: row['connection'] for p,row in room.players.items()}
            self._current()
            receiver = CheckpointReceiver(self.manifest, self.checkpoint_id, self.scope,
                self.manifest['epoch'], self.manifest['period'], self.manifest['cut'])
            for chunk in package.chunks():
                receiver.accept(chunk)
                self.chunks[(chunk['part'], chunk['index'])] = deepcopy(chunk)
            receiver.verified_parts()
            self._current()


class _Projection(OldProjection):
    def __init__(self, coordinator, *, host_sampler, guest_sampler, verify_held,
                 guest_before, native_load, source_kind):
        need(type(coordinator) is BootstrapCoordinator and coordinator.state_contract == world.CONTRACT,
             'Explicit exact partial state_contract required')
        need(source_kind in ('LOCAL_NATIVE_PROVIDER', 'FIXTURE_ONLY'), 'Explicit local provenance required')
        need(all(callable(f) for f in (host_sampler, guest_sampler, verify_held, guest_before, native_load)),
             'Trusted local callbacks required; no received JSON permits')
        self.coordinator = coordinator
        self.host_sampler, self.guest_sampler = host_sampler, guest_sampler
        self.verify_held, self.guest_before, self.native_load = verify_held, guest_before, native_load
        self.source_kind = source_kind
        self.held_reason = None
        self._lock = threading.RLock()


class BootstrapRoom(RemoteCompletionRoom):
    def bind_coordinator(self, coordinator):
        """Bind at initial planning, so even a pre-first-save disconnect is seen."""
        require(type(coordinator) is BootstrapCoordinator,'Trusted coordinator required')
        with self.lock, coordinator.lock:
            require(self._coordinator is None and not self._closed and self._held is None,
                    'Coordinator already bound or room unavailable')
            require(coordinator.phase=='PLANNING' and coordinator.period==1 and
                coordinator.connected=={'A','B'} and coordinator.scope==scope_from_room(self),
                'Initial planning room boundary required')
            self._coordinator=coordinator
            self._scope=deepcopy(coordinator.scope)
            self._connections={p:r['connection'] for p,r in self.players.items()}
            self._attachments=deepcopy(coordinator.attachments)
            self._initial=dict(epoch=coordinator.epoch,period=coordinator.period,
                node=deepcopy(coordinator.node),attachments=deepcopy(coordinator.attachments))

    def install_offered_checkpoint(self, coordinator, package):
        """Trusted host publication, never a network action or a load receipt."""
        require(type(coordinator) is BootstrapCoordinator and type(package) is CheckpointPackage,
                'Trusted coordinator/package required')
        with self.lock, coordinator.lock:
            self._bound(coordinator)
            if self.artifacts is None:
                m=package.manifest
                require(m['epoch']==self._initial['epoch'] and m['period']==self._initial['period'] and
                    m['node']==self._initial['node'] and coordinator.bootstrap_checkpoint==package.checkpoint_id and
                    coordinator.attachments==self._initial['attachments'],
                    'Initial checkpoint skipped or initial native attachment changed')
            else:
                if package.checkpoint_id == self.artifacts.checkpoint_id:
                    # Idempotent publication must not renew tickets or reset quota.
                    with self.artifacts.lock:self.artifacts._current()
                    return self.artifacts
                self._next_checkpoint(coordinator,package)
            candidate = _ArtifactService(self,coordinator,package)
            # Candidate fully hashes its pinned copy before any old owner retires.
            previous = self.artifacts
            if previous is not None:previous.close()
            self.artifacts = candidate
            self._warm_ack = None
            self._coordinator = coordinator
            self._scope = deepcopy(candidate.scope)
            self._connections = dict(candidate.connections)
            self._attachments = deepcopy(coordinator.attachments)
            self._generation += 1
            self.download_endpoint._retire_old()
            return candidate

    def enroll_adapter(self, key, *, host_sampler, verify_held, host_receipt_key, source_kind):
        """A's trusted launcher only, after both control seats are bound.

        Provision the same key privately to the B retained owner. There is no
        network enrollment/key exchange or reconnect/restart recovery here.
        """
        with self.lock:
            key_check(key)
            need(self._remote is None and self._coordinator is not None, 'Adapter already enrolled/no coordinator')
            need(callable(host_receipt_key), 'Current owned A receipt key callback required')
            c = self._coordinator
            helper = _Projection(c, host_sampler=host_sampler, guest_sampler=lambda *_: None,
                verify_held=verify_held, guest_before=lambda: None, native_load=lambda _: None, source_kind=source_kind)
            self._remote = dict(key=key, helper=helper, host_key=host_receipt_key,
                connection=self.players['B']['connection'], rows={}, held=None)


class BootstrapFreshSaveBinding(OldBinding):
    def __init__(self, room: BootstrapRoom, coordinator: BootstrapCoordinator, *,
                 native_room_id: bytes, native_room_epoch: int,
                 artifact_reader: Callable[[int], DecodedArtifact],
                 source_kind: str):
        require(isinstance(room, BootstrapRoom) and type(coordinator) is BootstrapCoordinator,
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

    def _capture_boundary(self):
        c = self.coordinator
        self.room._bound(c)
        require(scope_from_room(self.room) == self._scope == c.scope and
                c.state_contract == self._state_contract and
                c.attachments['A'] == self._host_attachment,
                'Room scope, host attachment or state contract changed')
        require(((c.period == 1 and not c.bootstrap_completed and c.phase == 'BOOTSTRAP_EXPORT') or (c.bootstrap_completed and c.phase == 'RUNNING')) and c.event is None and c.connected == {'A', 'B'},
                'No running authority at a settled export boundary')
        require(type(c.seal) is dict and c.seal.get('epoch') == c.epoch and
                c.seal.get('period') == c.period and hexid(c.seal.get('id'), 32) and
                integer(c.seal.get('sequence')) and hexid(c.seal.get('prefix_sha256')),
                'No current sealed command prefix')
        require(not any(c.inflight.values()), 'Commands are still pending')
        return dict(scope=deepcopy(self._scope), epoch=c.epoch, period=c.period,
            cut={k: c.seal[k] for k in ('sequence', 'prefix_sha256')},
            seal=deepcopy(c.seal), node=deepcopy(c.node) if c.period == 1 else next_node(c.node),
            attachments=deepcopy(c.attachments), state_contract=c.state_contract,
            connections={p: row['connection'] for p, row in self.room.players.items()})

    def validate_context(self):
        """Read-only check of exact bound Room, connections and export boundary."""
        with self.room.lock, self.coordinator.lock:
            self._available()
            return deepcopy(self._capture_boundary())


def host_observation(binding, *, reader, read_birth, verify_held, source_ruler, expected_node=None):
    """Existing full two-table sampler, with explicit initial/successor date.
    Requires the retained strong boundary provider; this function is not one.
    """
    need(type(binding) is BootstrapFreshSaveBinding, 'Exact bootstrap binding required')
    need(callable(read_birth) and callable(verify_held) and verify_held() is True,
         'Native boundary is not held')
    boundary = binding.validate_context()
    scope, node = boundary['scope'], boundary['node']
    with binding.coordinator.lock:
        current_node = deepcopy(binding.coordinator.node)
    if expected_node is not None:
        need(expected_node == current_node or expected_node == node, 'Observation date outside current/export boundary')
        node = deepcopy(expected_node)
    need(boundary['state_contract'] == world.CONTRACT and
         scope['profile']['game_sha256'] == world.objects.GAME_SHA256, 'Declared projection/build differs')
    world.integer(source_ruler, high=6000)
    force = scope['bindings']['A']['force_id']
    expected = (node['year'], node['month'], node['day'], force, source_ruler)
    reads = world.Reads(reader.memory.read)
    before = world.context(reader, reads, read_birth, expected)
    payload = world.payload_pass(reader, reads, before['root'])
    middle = world.context(reader, reads, read_birth, expected)
    again = world.payload_pass(reader, reads, before['root'])
    after = world.context(reader, reads, read_birth, expected)
    need(before == middle == after and payload == again, 'Observed A projection changed')
    need(verify_held() is True and binding.validate_context() == boundary, 'Held protocol boundary changed')
    with binding.coordinator.lock:
        need(binding.coordinator.node == current_node, 'Current protocol node changed during observation')
    return LocalWorldObservation(boundary['attachments']['A'], node['year'], node['month'], node['day'],
        force, source_ruler, world.CONTRACT, digest(world.shared(node,payload)), True)
