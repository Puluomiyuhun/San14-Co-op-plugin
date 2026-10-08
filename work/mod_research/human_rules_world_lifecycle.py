"""Trusted local orchestration of one world replacement; never a Room RPC.

The caller must retain a real execution fence across the entire call. Restore
means the existing external publisher's six-source operation, NOT native Revoke
(which permanently faults the old module). Each world needs a fresh resident
activation instance. No module is reset/unloaded, and no Ready is granted here.
"""
from dataclasses import dataclass
import ctypes as C
import hashlib
import threading

from human_rules_activation_room import Config


class LifecycleError(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise LifecycleError(message)


def check_port(callback, *args):
    """Checks raise on failure and return exactly None on success, never bool."""
    need(callback(*args) is None, 'Trusted check must return None on success or raise on failure')


class Site(C.Structure):
    _fields_ = [('address', C.c_uint64), ('destination', C.c_uint64),
                ('original_target', C.c_uint64), ('patch_size', C.c_uint32),
                ('profile_size', C.c_uint32), ('protection', C.c_uint32),
                ('reserved', C.c_uint32), ('expected', C.c_ubyte * 128),
                ('replacement', C.c_ubyte * 16)]


class Descriptor(C.Structure):
    _fields_ = [('magic', C.c_uint64), ('version', C.c_uint32),
                ('size', C.c_uint32), ('pid', C.c_uint32), ('fixture', C.c_uint32),
                ('birth', C.c_uint64), ('image', C.c_uint64),
                ('module', C.c_uint64), ('allocation', C.c_uint64),
                ('nonce', C.c_ubyte * 32), ('sites', Site * 6),
                ('site_count', C.c_uint32), ('policy_enabled', C.c_uint32),
                ('preparation_state', C.c_int32), ('reserved', C.c_uint32)]


@dataclass(frozen=True)
class WorldGeneration:
    generation: int
    checkpoint: str
    config: bytes

    def __post_init__(self):
        need(type(self.generation) is int and 1 <= self.generation < 2**63,
             'Invalid local world generation')
        need(type(self.checkpoint) is str and len(self.checkpoint) == 64 and
             all(c in '0123456789abcdef' for c in self.checkpoint), 'Invalid checkpoint identity')
        need(type(self.config) is bytes and len(self.config) == C.sizeof(Config), 'Exact Config required')
        c = Config.from_buffer_copy(self.config)
        need(c.version == 1 and c.size == C.sizeof(Config), 'Unknown Config version')
        need(c.image and c.root and c.world and any(c.room) and any(c.epoch) and
             any(c.rules_digest), 'Missing native or room identity')
        need(1 <= c.force[0] <= 51 and 1 <= c.force[1] <= 51 and c.force[0] != c.force[1] and
             1 <= c.main_district[0] <= 51 and 1 <= c.main_district[1] <= 51 and
             c.main_district[0] != c.main_district[1] and c.viewer in c.force,
             'Invalid human identity')
        need(1 <= c.year <= 65535 and 1 <= c.month <= 12 and c.day in (1, 11, 21) and
             c.income_key5 <= 3 and c.world_option8 <= 1, 'Invalid date/settings')


@dataclass(frozen=True)
class NextWorldRequest:
    """Logical load target only; new root/world addresses do not yet exist."""
    generation: int
    checkpoint: str
    epoch: bytes
    year: int
    month: int
    day: int

    def __post_init__(self):
        need(type(self.generation) is int and 1 <= self.generation < 2**63, 'Invalid requested generation')
        need(type(self.checkpoint) is str and len(self.checkpoint) == 64 and
             all(c in '0123456789abcdef' for c in self.checkpoint), 'Invalid requested checkpoint')
        need(type(self.epoch) is bytes and len(self.epoch) == 16 and any(self.epoch), 'Invalid requested epoch')
        need(type(self.year) is int and 1 <= self.year <= 65535 and
             type(self.month) is int and 1 <= self.month <= 12 and
             type(self.day) is int and self.day in (1, 11, 21), 'Invalid requested date')


@dataclass(frozen=True)
class ModuleIdentity:
    pid: int
    birth: int
    module: int
    descriptor: int
    nonce: bytes
    stage_sha256: str
    state_rva: int
    binding_rva: int
    # (instruction RVA, exact bytes, active counter RVA), build-time fixed profile.
    counters: tuple
    source_kind: str

    def __post_init__(self):
        need(type(self.pid) is int and self.pid > 0 and type(self.birth) is int and self.birth > 0,
             'Missing process identity')
        need(self.module >= 65536 and self.descriptor >= self.module and self.state_rva > 0 and
             self.binding_rva > 0 and type(self.nonce) is bytes and len(self.nonce) == 32 and
             any(self.nonce), 'Invalid module identity')
        need(len(self.stage_sha256) == 64 and all(c in '0123456789abcdef' for c in self.stage_sha256),
             'Missing pinned stage hash')
        need(type(self.counters) is tuple and len(self.counters) == 2 and all(
            type(r) is tuple and len(r) == 3 and type(r[0]) is int and r[0] > 0 and
            type(r[1]) is bytes and 1 <= len(r[1]) <= 16 and type(r[2]) is int and r[2] > 0
            for r in self.counters), 'Exact AI and income counter anchors required')
        need(self.source_kind in ('OWNED_FIXTURE', 'LOCAL_NATIVE_PROVIDER'), 'Unknown provider kind')


class ResidentPort:
    """Bind trusted retained process/reader/publisher ports, never JSON receipts.

    identity_check must validate the still-live pinned process handle and stage
    file/module identity. publisher(operation) must invoke the approved external
    publisher with this exact process, descriptor, nonce, DLL and Config file.
    export_current must use a current native reader (for Room use export_config),
    not return a cached Config. check_scope must hold/validate the local Room scope.
    identity_check/check_scope succeed by returning exactly None and must raise
    on failure; booleans are rejected. These trusted in-process dependencies do not turn
    an arbitrary callback or serialized report into native attestation.
    """
    def __init__(self, world, module, *, read, identity_check, publisher,
                 export_current, check_scope):
        need(type(world) is WorldGeneration and type(module) is ModuleIdentity, 'Typed local binding required')
        need(all(callable(f) for f in (read, identity_check, publisher, export_current, check_scope)),
             'Missing trusted local port')
        self.world, self.module = world, module
        self._read, self._identity, self._publisher = read, identity_check, publisher
        self._export, self._scope = export_current, check_scope
        self._descriptor = None
        self.retired = False
        self.events = []

    def _take(self, address, count):
        raw = self._read(address, count)
        need(type(raw) is bytes and len(raw) == count, 'Incomplete native read')
        return raw

    def _current(self, allow_date_advance):
        raw = self._export(self.world)
        need(type(raw) is bytes and len(raw) == C.sizeof(Config), 'Missing current native Config')
        if allow_date_advance:
            actual, bound = Config.from_buffer_copy(raw), Config.from_buffer_copy(self.world.config)
            need(1 <= actual.year <= 65535 and 1 <= actual.month <= 12 and actual.day in (1, 11, 21) and
                 (actual.year, actual.month, actual.day) >= (bound.year, bound.month, bound.day),
                 'Invalid/backward current date')
            actual.year, actual.month, actual.day = bound.year, bound.month, bound.day
            raw = bytes(actual)
        need(raw == self.world.config, 'Current reader disagrees with world binding')

    def observe(self, installed, *, allow_date_advance=False):
        need(not self.retired, 'Retired module cannot be reused')
        check_port(self._identity, self.module)
        check_port(self._scope, self.world)
        self._current(allow_date_advance)
        m = self.module
        need(self._take(m.module + m.state_rva, 4) == (4).to_bytes(4, 'little'),
             'Activation is not Sealed; Revoke is not a normal restore')
        raw = self._take(m.descriptor, C.sizeof(Descriptor))
        d = Descriptor.from_buffer_copy(raw)
        c = Config.from_buffer_copy(self.world.config)
        need(d.magic == 0x31544753524C5548 and d.version == 1 and d.size == C.sizeof(Descriptor) and
             d.pid == m.pid and d.birth == m.birth and d.image == c.image and d.module == m.module and
             bytes(d.nonce) == m.nonce and d.site_count == 6 and d.policy_enabled == 1 and
             d.preparation_state == 2 and d.reserved == 0 and d.allocation and
             d.fixture == int(m.source_kind == 'OWNED_FIXTURE'), 'Descriptor identity mismatch')
        if self._descriptor is None:
            self._descriptor = raw
        need(self._descriptor == raw, 'Resident descriptor changed')
        need(self._take(m.module + m.binding_rva, C.sizeof(Config)) == self.world.config,
             'Native activation bound to another world')
        addresses = []
        for s in d.sites:
            need(s.reserved == 0 and s.protection == 0x20 and 1 <= s.patch_size <= 16 and
                 s.patch_size <= s.profile_size <= 128 and c.image <= s.address < c.image + 0x2238000,
                 'Invalid six-source descriptor')
            expected = bytes(s.expected[:s.profile_size])
            if installed:
                expected = bytes(s.replacement[:s.patch_size]) + expected[s.patch_size:]
            need(self._take(s.address, s.profile_size) == expected, 'Actual source bytes disagree')
            addresses.append(s.address)
        need(len(set(addresses)) == 6, 'Repeated source address')
        for instruction, expected, counter in m.counters:
            need(self._take(m.module + instruction, len(expected)) == expected, 'Active-counter profile mismatch')
            need(self._take(m.module + counter, 8) == bytes(8), 'Native call still active; do not load')
        need(self._take(m.descriptor, C.sizeof(Descriptor)) == raw and
             self._take(m.module + m.binding_rva, C.sizeof(Config)) == self.world.config and
             self._take(m.module + m.state_rva, 4) == (4).to_bytes(4, 'little'), 'Native binding changed during readback')
        check_port(self._identity, m)
        check_port(self._scope, self.world)
        self._current(allow_date_advance)
        result = dict(generation=self.world.generation, checkpoint=self.world.checkpoint,
                      module=m.module, config_sha256=hashlib.sha256(self.world.config).hexdigest(),
                      six_source_mask=63, active_ai=0, active_income=0, installed=installed,
                      evidence='CURRENT_NATIVE_READBACK', source_kind=m.source_kind)
        self.events.append(result)
        return result

    def _publish(self, operation):
        self.observe(operation == 'restore', allow_date_advance=operation == 'restore')
        code, report = self._publisher(operation)
        expected = 'RESTORED' if operation == 'restore' else 'INSTALLED_HUMAN_RULES'
        need(code == 0 and type(report) is dict and report.get('status') == expected and
             report.get('attached') is True and report.get('detached') is True and
             report.get('held_create_process_event') is True and report.get('uncertain') is False and
             report.get('written_mask') == 63 and report.get('rolled_mask') == 0 and
             type(report.get('threads_checked')) is int and report['threads_checked'] > 0 and
             report.get('fixture_build') is (self.module.source_kind == 'OWNED_FIXTURE'),
             'Publisher did not prove all sources and debugger detached; retain owner, do not kill publisher')
        result = self.observe(operation == 'install', allow_date_advance=operation == 'restore')
        return dict(operation=operation, publisher=dict(report), readback=result)

    def restore(self):
        return self._publish('restore')

    def install(self):
        return self._publish('install')


class WorldLifecycle:
    """Coordinate exact world generations while a trusted external fence is held.

    guard_check must prove execution/input exclusion throughout restore/load/
    rebind, not merely pause the Room protocol. on_hold must retain that exclusion
    and revoke network readiness/download authority. Both return exactly None on
    success or raise on failure; booleans are rejected. No default no-op is supplied.
    This component never releases a fence, calls Revoke, resets a DLL or sets Ready.
    load follows the same exact-None/raise contract. observe_loaded samples the
    unknown new native pointers after load and returns WorldGeneration; prepare
    then creates and returns ResidentPort. The caller never predicts addresses.
    """
    def __init__(self, current, *, guard_check, on_hold):
        need(type(current) is ResidentPort and callable(guard_check) and callable(on_hold),
             'Trusted native lifecycle ports required')
        self.current = current
        self._guard, self._on_hold = guard_check, on_hold
        self._lock = threading.RLock()
        self.phase = 'ACTIVE'
        self.held_reason = None
        self.hold_error = None
        self.history = []
        self.retained = [current]
        self._used_modules = {current.module.module}
        self._used_nonces = {current.module.nonce}

    def replace(self, request, *, load, observe_loaded, prepare):
        with self._lock:
            need(self.phase == 'ACTIVE', 'Lifecycle already consumed or held')
            try:
                need(type(request) is NextWorldRequest and all(callable(f) for f in (load, observe_loaded, prepare)),
                     'Missing trusted next-generation ports')
                old = self.current
                need(request.generation == old.world.generation + 1 and
                     request.checkpoint != old.world.checkpoint, 'Stale/repeated world generation')
                before = Config.from_buffer_copy(old.world.config)
                check_port(self._guard)
                self.phase = 'RESTORING'
                self.history.append(old.restore())
                check_port(self._guard)
                # Retiring never unloads native code; callbacks stay fenced off.
                old.retired = True
                self.phase = 'LOAD_ALLOWED'
                self.history.append(dict(operation='LOAD_ALLOWED', generation=request.generation))
                check_port(self._guard)
                self.phase = 'LOADING'
                check_port(load, request)
                check_port(self._guard)
                self.phase = 'OBSERVING_LOADED_WORLD'
                expected = observe_loaded(request)
                need(type(expected) is WorldGeneration and expected.generation == request.generation and
                     expected.checkpoint == request.checkpoint, 'Observed another world generation/checkpoint')
                after = Config.from_buffer_copy(expected.config)
                need(bytes(after.epoch) == request.epoch and
                     (after.year, after.month, after.day) == (request.year, request.month, request.day),
                     'Observed world does not match requested epoch/date')
                need(before.image == after.image and bytes(before.room) == bytes(after.room) and
                     bytes(before.rules_digest) == bytes(after.rules_digest) and list(before.force) == list(after.force) and
                     before.viewer == after.viewer and before.income_key5 == after.income_key5 and
                     before.world_option8 == after.world_option8, 'Changed process/game/room/human identity/settings')
                check_port(self._guard)
                self.history.append(dict(operation='WORLD_OBSERVED_AFTER_LOAD', generation=expected.generation,
                    root=after.root, world=after.world, evidence='TRUSTED_LOCAL_OBSERVER'))
                self.phase = 'REBINDING'
                new = prepare(expected)
                need(type(new) is ResidentPort, 'Missing resident prepared module')
                self.retained.append(new)
                need(new.world == expected, 'Prepared another world generation')
                need(new.module.pid == old.module.pid and new.module.birth == old.module.birth and
                     new.module.source_kind == old.module.source_kind and
                     new.module.module not in self._used_modules and new.module.nonce not in self._used_nonces,
                     'Fresh resident module instance required; same DLL reset is forbidden')
                self._used_modules.add(new.module.module)
                self._used_nonces.add(new.module.nonce)
                check_port(self._guard)
                self.history.append(new.install())
                check_port(self._guard)
                self.current = new
                self.phase = 'ACTIVE'
                return dict(phase='RULES_REBOUND', generation=expected.generation,
                            checkpoint=expected.checkpoint, ready=False, fence_released=False,
                            full_world_verified=False, source_kind=new.module.source_kind)
            except BaseException as exc:
                self.phase = 'HELD'
                self.held_reason = type(exc).__name__ + ': ' + str(exc)
                try:
                    check_port(self._on_hold, self.held_reason)
                except BaseException as hold_exc:
                    self.hold_error = type(hold_exc).__name__ + ': ' + str(hold_exc)
                raise

    def status(self):
        return dict(phase=self.phase, held_reason=self.held_reason, hold_error=self.hold_error,
                    retained_modules=len(self.retained), ready=False, fence_released=False,
                    full_world_verified=False)


assert C.sizeof(Site) == 184
assert C.sizeof(Descriptor) == 1208
