"""One guest checkpoint transition; dependency-injected, no game access.

Uses the existing durable journal, room gate and validated visual helper client.
NativePort is deliberately an unimplemented trusted adapter boundary. Bytes read,
Title identity and a captured frame are not full-world or native-input proof.
The controller must be the room's admission point: MapWaitGate LIVE by itself
does not mean native input release has been acknowledged.
"""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import secrets
import sys
import threading
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'outputs' / 'san14-link'))
from checkpoint_presentation import MapWaitGate
from checkpoint_visual_client import TargetBinding, require, hexid
from checkpoint_visual_client_bridge import GateVisualBridge


@dataclass(frozen=True)
class Context:
    attempt: str
    presentation: str
    checkpoint_id: str
    state_contract: str


@dataclass(frozen=True)
class InputHold:
    context: Context
    lease: str
    attachment: str
    input_blocked: bool


@dataclass(frozen=True)
class WorldObservation:
    lease: str
    host: dict
    guest: dict
    input_blocked: bool
    full_world_verified: bool
    state_contract: str
    # Same QPC/100ns clock used by WGC. Only meaningful at restored planning map.
    planning_ready_time: int = 0


@dataclass(frozen=True)
class LoadProgress:
    context: Context
    lease: str
    state: str  # PENDING, COMPLETE, FAILED or UNCERTAIN; COMPLETE needs full receipt.
    receipt: dict | None = None


@dataclass(frozen=True)
class InputRelease:
    context: Context
    lease: str
    grant_token: str
    attachment: str
    released: bool


class NativePort(Protocol):
    """Trusted in-process/IPC adapter, not provided by this offline module.

    hold_input must actually prevent native orders/advance across reload, even
    if the controller crashes. start_load must consume permit once durably and
    retain all observers after uncertain publication. COMPLETE requires native
    planning, identity, full semantic world verification, not a file hash alone.
    All callbacks are serialized by the controller; no automatic load retries.
    """
    provenance: str
    def hold_input(self, context: Context, target: TargetBinding) -> InputHold: ...
    def observe(self, hold: InputHold) -> WorldObservation: ...
    def start_load(self, context: Context, permit: dict, parts: dict, hold: InputHold) -> None: ...
    def poll_load(self, hold: InputHold) -> LoadProgress: ...
    # Reassert this lease's input barrier if release was ambiguous; keep load
    # and identity observers alive. Must not initiate another load or detach.
    def hold_and_retain_observers(self, hold: InputHold) -> None: ...
    # Must implement NeutralInputGate's release semantics: fresh neutral/drained
    # cycle AFTER reveal, no held physical keys/buttons, unknown devices or queued
    # input; revalidate room epoch/connection, identity and world at release.
    # Returning this dataclass is not an implementation of those requirements.
    def release_input(self, hold: InputHold, grant: dict) -> InputRelease: ...


class GuestTransition:
    def __init__(self, gate, visual, native, *, allow_fixture_native=False):
        require(type(gate) is MapWaitGate, 'Existing checkpoint gate required')
        require(type(visual) is GateVisualBridge, 'Validated visual bridge required')
        require(type(allow_fixture_native) is bool, 'Explicit fixture mode required')
        require(getattr(native, 'provenance', None) == 'ROOT_TRUSTED_NATIVE_ADAPTER' or
                (allow_fixture_native and getattr(native, 'provenance', None) == 'FIXTURE_ONLY'),
                'Trusted native adapter missing; fixtures require explicit opt-in')
        self.gate, self.visual, self.native = gate, visual, native
        self.context = Context(secrets.token_hex(16), gate.nonce,
            gate.identity['checkpoint_id'], gate.coordinator.state_contract)
        self.lock = threading.RLock()
        self.phase = 'NEW'
        self.hold = None
        self.permit = None
        self.start_dispatched = False
        self.input_released = False
        self.reason = ''
        self.cleanup_errors = []
        self.last_progress = None

    def _room_current(self):
        c = self.gate.coordinator
        with self.gate.lock, c.lock:
            require(c.connected == {'A', 'B'}, 'A player disconnected')
            if self.gate.phase == 'LIVE':
                require(self.gate.status()['accept_planning_intents'], 'Released room changed')
            else:
                self.gate._boundary()

    def _observe(self, *, restored=False):
        self._room_current()
        obs = self.native.observe(self.hold)
        require(type(obs) is WorldObservation and obs.lease == self.hold.lease and
                obs.input_blocked is True and obs.full_world_verified is True and
                obs.state_contract == self.context.state_contract, 'Native world/input evidence missing')
        require(type(obs.host) is dict and type(obs.guest) is dict, 'World observations required')
        if restored:
            require(type(obs.planning_ready_time) is int and obs.planning_ready_time > 0,
                    'Fresh native planning boundary required')
        self._room_current()
        return obs

    def _hold(self, reason):
        """Never unload observers, reveal pixels, release input or retry a load."""
        self.phase, self.reason = 'HELD', reason
        self.gate.hold(reason)
        if self.hold is not None:
            try:
                self.native.hold_and_retain_observers(self.hold)
            except Exception as error:
                self.cleanup_errors.append('hold_and_retain_observers: ' + type(error).__name__)
        try:
            self.visual.client.hold(reason)
        except Exception as error:
            self.cleanup_errors.append('visual_hold: ' + type(error).__name__)

    def start(self, target):
        with self.lock:
            # A duplicate caller must not destroy a valid ongoing transition.
            require(self.phase == 'NEW', 'This transition has already been consumed')
            self.phase = 'STARTING'
            try:
                require(type(target) is TargetBinding, 'Explicit bound target required')
                target.validate()
                self._room_current()
                require(target.attachment == self.gate.identity['attachments']['B'],
                        'Wrong guest attachment')
                # Do not reacquire/reload after restart from an ambiguous intent.
                require(self.gate.journal.status()['status'] == 'STAGED',
                        'Checkpoint is not a fresh staged load')
                parts = self.gate.journal.verified_parts()
                self.hold = self.native.hold_input(self.context, target)
                require(type(self.hold) is InputHold and self.hold.context == self.context and
                        self.hold.attachment == target.attachment and hexid(self.hold.lease) and
                        self.hold.input_blocked is True, 'Native input hold not acknowledged')
                self.visual.client.bind(target)
                cover = self.visual.client.cover()
                self.visual.accept_cover(self.gate, cover)
                obs = self._observe()
                self.permit = self.gate.reserve_load(deepcopy(obs.host), deepcopy(obs.guest))
                # Durable INTENT exists before entering native code. Any exception
                # from this point is ambiguous and cannot grant a second attempt.
                self.start_dispatched = True
                self.native.start_load(self.context, deepcopy(self.permit), parts, self.hold)
                self.phase = 'LOADING'
                return self.status()
            except BaseException:
                self._hold('GUEST_TRANSITION_START_UNCONFIRMED')
                raise

    def _progress(self):
        p = self.native.poll_load(self.hold)
        require(type(p) is LoadProgress and p.context == self.context and
                p.lease == self.hold.lease and p.state in ('PENDING','COMPLETE','FAILED','UNCERTAIN'),
                'Stale or foreign native progress')
        self.last_progress = deepcopy(p)
        return p

    def poll(self):
        """One bounded poll. No timer, game discovery, or implicit background work."""
        with self.lock:
            require(self.phase in ('LOADING','HELD','LIVE'), 'Transition has not started')
            if self.phase == 'HELD':
                # Retain useful late outcomes for diagnostics, without accepting
                # gameplay or treating late completion as automatic recovery.
                if self.start_dispatched:
                    try:
                        self._progress()
                    except Exception as error:
                        self.cleanup_errors.append('late_observation: ' + type(error).__name__)
                return self.status()
            if self.phase == 'LIVE':
                return self.status()
            try:
                self._room_current()
                self.visual.client.ping()
                progress = self._progress()
                if progress.state == 'PENDING':
                    return self.status()
                require(progress.state == 'COMPLETE' and type(progress.receipt) is dict,
                        'Native load failed or its outcome is uncertain')
                obs = self._observe(restored=True)
                self.gate.journal.complete(deepcopy(progress.receipt))
                self.gate.world_restored(deepcopy(obs.host), deepcopy(obs.guest))
                prepared = self.visual.client.prepare(new_attachment=self.gate.new_attachment,
                                                       after_time=obs.planning_ready_time)
                self.visual.accept_prepared(self.gate, prepared)
                # Reacquire host/guest world observations after capture, not the
                # receipt obtained before a potentially long renderer wait.
                fresh = self._observe(restored=True)
                require(fresh.planning_ready_time <= prepared.capture_time,
                        'Native map changed after captured frame')
                grant = self.gate.begin_reveal(deepcopy(fresh.host), deepcopy(fresh.guest))
                revealed = self.visual.reveal(self.gate, grant)
                # Revealing can wait on another process. Check native worlds
                # again before authorizing any input release.
                release_world = self._observe(restored=True)
                self.gate._fresh_world(release_world.host, release_world.guest)
                require(release_world.planning_ready_time <= prepared.capture_time,
                        'Native map changed during reveal')
                self.visual.client.assert_current(revealed, ('REVEALED',))
                released = self.native.release_input(self.hold, deepcopy(grant))
                require(type(released) is InputRelease and released.context == self.context and
                        released.lease == self.hold.lease and released.grant_token == grant['token'] and
                        released.attachment == grant['attachment'] and released.released is True,
                        'Native input release not acknowledged')
                self._room_current()
                self.visual.client.assert_current(revealed, ('REVEALED',))
                self.input_released = True
                self.phase = 'LIVE'
                return self.status()
            except BaseException:
                self._hold('GUEST_TRANSITION_COMPLETION_UNCONFIRMED')
                raise

    def require_local_planning(self, epoch, attachment):
        """Room submissions must use this combined gate, not coordinator.phase."""
        with self.lock, self.gate.lock, self.gate.coordinator.lock:
            require(self.status()['accept_planning_intents'] and
                    epoch == self.gate.coordinator.epoch and
                    attachment == self.gate.new_attachment, 'Local planning remains blocked')

    def set_local_ready(self, value):
        with self.lock, self.gate.lock, self.gate.coordinator.lock:
            c = self.gate.coordinator
            self.require_local_planning(c.epoch, c.attachments['B'])
            return c.set_ready('B', c.epoch, value)

    def status(self):
        with self.lock:
            admission = (self.phase == 'LIVE' and self.input_released and
                         self.gate.status()['accept_planning_intents'] and
                         self.visual.client.fault is None)
            return {'phase': self.phase, 'accept_planning_intents': admission,
                    'attempt': self.context.attempt, 'checkpoint_id': self.context.checkpoint_id,
                    'native_start_dispatched': self.start_dispatched,
                    'native_input_release_acknowledged': self.input_released,
                    # After a completed transition the outer room monitor owns
                    # a fresh native gate on disconnect/surface failure. Merely
                    # returning admission=False does not block physical input.
                    'fresh_native_gate_required': self.phase == 'LIVE' and not admission,
                    'diagnostic_hold_reason': self.reason,
                    'late_native_state': self.last_progress.state if self.last_progress else None,
                    'cleanup_errors': list(self.cleanup_errors),
                    'native_gameplay_enabled': False,
                    'live_native_adapter_implemented': False}
