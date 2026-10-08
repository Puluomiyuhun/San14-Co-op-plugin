"""Current Room context -> local rule Config, including a real remote B reader.

The network exports protocol context only. It neither installs rules nor creates
a load intent/world receipt/Ready permission. Remote checks are snapshots, NOT
a distributed lock. A trusted native owner must retain execution/input exclusion
throughout restore/load/rebind and supply its own process identity/hold ports.
Frozen Room, protocol and rule lifecycle implementations are not modified.
"""
from copy import deepcopy
import ctypes as C
import struct
import threading

from checkpoint_ready_barrier import ReadyBarrierRoom
from checkpoint_room_lifecycle import CheckpointRoom
from checkpoint_room_progress import ProgressRoom
from checkpoint_room_client import RoomConnection
from checkpoint_room_artifacts import RoomError, SyncError, require
from authoritative_sync import (canonical, digest, hexid, integer, scope_from_room,
    validate_scope, validate_manifest, validate_node, next_node)
from human_rules_activation_room import Config, GAME_SHA, rules
from human_rules_world_lifecycle import NextWorldRequest, WorldGeneration
from checkpoint_journal import CheckpointJournal


FAULT_REASONS = {'NATIVE_CONTEXT_FAILED', 'RULES_REBIND_FAILED', 'LOCAL_GUARD_LOST'}


def _none(callback, *args):
    require(callback(*args) is None, 'Trusted check must return exactly None or raise')


def context_from_room(room, side, checkpoint_id):
    """Called under the real local Room/coordinator locks, never a shadow Room."""
    require(type(room) in (CheckpointRoom, ProgressRoom, ReadyBarrierRoom, RulesContextRoom),
            'Known local checkpoint Room required')
    require(side in ('A', 'B') and (checkpoint_id is None or hexid(checkpoint_id)), 'Bad context target')
    with room.lock:
        c = room._coordinator
        require(c is not None, 'No planning coordinator')
        with c.lock:
            room._bound(c)
            require(c.connected == {'A', 'B'} and all(r['confirmed'] for r in room.players.values()),
                    'Both confirmed control seats required')
            scope = scope_from_room(room)
            require(scope == c.scope, 'Coordinator scope changed')
            checkpoint = None
            if checkpoint_id is None:
                require(c.phase == 'PLANNING', 'Initial context requires planning')
            else:
                require(c.phase == 'RECONCILING' and room.artifacts is not None and
                        c.checkpoint_id == room.artifacts.checkpoint_id == checkpoint_id and
                        c.manifest == room.artifacts.manifest, 'Checkpoint context no longer current')
                checkpoint = dict(id=checkpoint_id, manifest=deepcopy(c.manifest), generation=room._generation)
            value = dict(schema='san14.rules-checkpoint-context.v1', player=side, scope=scope,
                coordinator=dict(epoch=c.epoch, period=c.period, phase=c.phase, node=deepcopy(c.node),
                    state_contract=c.state_contract, attachments=deepcopy(c.attachments),
                    cut=None if c.seal is None else {k: c.seal[k] for k in ('sequence', 'prefix_sha256')}),
                checkpoint=checkpoint,
                control_binding_sha256=digest({p: r['connection'] for p, r in room.players.items()}))
            validate_context(value, side, room.manifest['profile'], checkpoint_id)
            return value


def validate_context(value, side, profile, checkpoint_id):
    require(type(value) is dict and set(value) == {'schema', 'player', 'scope', 'coordinator',
        'checkpoint', 'control_binding_sha256'}, 'Bad context fields')
    require(value['schema'] == 'san14.rules-checkpoint-context.v1' and value['player'] == side and
            hexid(value['control_binding_sha256']), 'Wrong context seat/version')
    scope = value['scope']; validate_scope(scope)
    require(scope['profile'] == profile and profile['game_sha256'] == GAME_SHA, 'Unexpected authenticated profile')
    c = value['coordinator']
    require(type(c) is dict and set(c) == {'epoch', 'period', 'phase', 'node', 'state_contract',
            'attachments', 'cut'} and hexid(c['epoch'], 32) and integer(c['period'], 1), 'Bad period context')
    validate_node(c['node'])
    require(type(c['state_contract']) is str and 1 <= len(c['state_contract']) <= 200 and
            type(c['attachments']) is dict and set(c['attachments']) == {'A', 'B'} and
            all(hexid(v, 32) for v in c['attachments'].values()) and
            c['attachments']['A'] != c['attachments']['B'], 'Invalid state contract/attachments')
    if checkpoint_id is None:
        require(value['checkpoint'] is None and c['phase'] == 'PLANNING', 'Not initial planning context')
    else:
        p = value['checkpoint']
        require(type(p) is dict and set(p) == {'id', 'manifest', 'generation'} and
                p['id'] == checkpoint_id and integer(p['generation'], 1), 'Bad checkpoint context')
        m = p['manifest']; validate_manifest(m)
        require(c['phase'] == 'RECONCILING' and digest(m) == checkpoint_id and
                m['scope_sha256'] == digest(scope) and m['epoch'] == c['epoch'] and
                m['period'] == c['period'] and m['state_contract'] == c['state_contract'] and
                m['node'] == next_node(c['node']) and m['cut'] == c['cut'], 'Checkpoint lineage changed')


def _retire(room):
    room.close_checkpoints()
    require(room.checkpoint_status()['closed'] is True and
            room.checkpoint_status()['download_available'] is False and
            room.download_endpoint.status()['active_connection_owners'] == 0,
            'Room/download revocation not confirmed')


class RulesContextRoom(ReadyBarrierRoom):
    """Read-only context and terminal fault request, retaining native Ready gate."""
    def __init__(self, manifest, **kwargs):
        super().__init__(manifest, **kwargs)
        self._rules_contexts = {}

    def handle(self, player, connection_id, request):
        action = request.get('action') if type(request) is dict else None
        if action not in ('rules_context', 'rules_context_fault'):
            return super().handle(player, connection_id, request)
        try:
            with self.lock:
                require(player in self.players and self.players[player]['connection'] == connection_id,
                        'Current authenticated control seat required')
                if action == 'rules_context':
                    require(set(request) == {'action', 'checkpoint_id', 'expected_context_sha256'} and
                            (request['expected_context_sha256'] is None or hexid(request['expected_context_sha256'])),
                            'Bad context request')
                    value = context_from_room(self, player, request['checkpoint_id'])
                    token = digest(value)
                    expected = request['expected_context_sha256']
                    if expected is not None:
                        require(self._rules_contexts.get(player) == (connection_id, expected, request['checkpoint_id']) and
                                token == expected, 'Pinned context changed; original fault identity retained')
                    else:
                        self._rules_contexts[player] = (connection_id, token, request['checkpoint_id'])
                    return dict(ok=True, context=value, context_sha256=token, native_permission=False)
                require(set(request) == {'action', 'checkpoint_id', 'context_sha256', 'reason'} and
                        type(request['reason']) is str and request['reason'] in FAULT_REASONS,
                        'Bad context fault request')
                require(self._rules_contexts.get(player) ==
                        (connection_id, request['context_sha256'], request['checkpoint_id']), 'Unknown context fault owner')
                # A fault is terminal, not the ordinary pre-load rules restore.
                try:
                    _retire(self)
                    return dict(ok=True, protocol_revocation_confirmed=True, native_pause_confirmed=False)
                except BaseException as exc:
                    return dict(ok=False, protocol_revocation_confirmed=False,
                                native_pause_confirmed=False, cleanup_error=type(exc).__name__)
        except (RoomError, SyncError, TypeError, ValueError) as exc:
            return dict(ok=False, error=str(exc), applied_to_game=False)


class ContextSource:
    """Immutable context with a current reader, not a long-lived permission."""
    def __init__(self, value, *, current, retire, room_lock=None):
        self._encoded = canonical(value)
        self._current, self._retire = current, retire
        self._lock = threading.RLock()
        self.room_lock = room_lock
        self.outer_lock = room_lock if room_lock is not None else threading.RLock()
        self.held = False
        self.revocation_confirmed = False
        self.revocation_error = None

    @property
    def value(self):
        import json
        return json.loads(self._encoded)

    def check(self):
        with self.outer_lock, self._lock:
            require(not self.held, 'Rules context is held; no reuse')
            require(canonical(self._current()) == self._encoded, 'Pinned rules context changed')

    def hold(self, reason):
        with self.outer_lock, self._lock:
            if self.held:
                return
            self.held = True
            try:
                _none(self._retire, reason)
                self.revocation_confirmed = True
            except BaseException as exc:
                self.revocation_error = type(exc).__name__ + ': ' + str(exc)


def local_context(room, side, checkpoint_id=None):
    value = context_from_room(room, side, checkpoint_id)
    def retire(reason):
        with room.lock:
            _retire(room)
    return ContextSource(value, current=lambda: context_from_room(room, side, checkpoint_id),
                         retire=retire, room_lock=room.lock)


def remote_context(connection, expected_profile, checkpoint_id=None):
    """Use this computer's authenticated control connection; never an A object.

    expected_profile is the exact greeting profile fixed by the local connector.
    Do not take it from the newly returned snapshot as its own trust anchor.
    """
    require(type(connection) is RoomConnection, 'Retained authenticated RoomConnection required')
    profile = deepcopy(expected_profile)
    side = connection.player_id
    require(side in ('A', 'B'), 'Bad authenticated seat')
    pinned = None
    def current():
        require(connection.status()['transport_open'] is True, 'Control connection unavailable')
        reply = connection.request(dict(action='rules_context', checkpoint_id=checkpoint_id,
                                        expected_context_sha256=pinned))
        require(reply.get('ok') is True and reply.get('native_permission') is False,
                'Context request rejected')
        value = reply.get('context')
        validate_context(value, side, profile, checkpoint_id)
        require(reply.get('context_sha256') == digest(value), 'Context digest differs')
        return value
    value = current()
    pinned = digest(value)
    def retire(reason):
        reply = connection.request(dict(action='rules_context_fault', checkpoint_id=checkpoint_id,
            context_sha256=digest(value), reason=reason))
        require(reply.get('ok') is True and reply.get('protocol_revocation_confirmed') is True and
                reply.get('native_pause_confirmed') is False, 'Remote protocol revocation not confirmed')
    return ContextSource(value, current=current, retire=retire)


class NativeRulesBinding:
    """Current native reads tied to one protocol snapshot, never native proof by JSON.

    identity_check and guard_check are owned local native ports. They must remain
    valid across the entire outer operation; these point checks are not a fence.
    on_local_hold must preserve that fence even when remote fault delivery fails.
    Reader, process identity, scheduler exclusion and load completion are supplied
    by the production owner; this module discovers no process and installs nothing.
    """
    def __init__(self, source, settings, *, image, read, identity_check, guard_check, on_local_hold):
        require(type(source) is ContextSource and type(image) is int and image >= 65536 and
                all(callable(f) for f in (read, identity_check, guard_check, on_local_hold)),
                'Explicit trusted local ports required')
        require(type(settings) is dict and settings == rules(settings.get('native_income_key5'),
                settings.get('native_world_option8')) and
                digest(settings) == source.value['scope']['profile']['rules_sha256'], 'Rules content/hash differ')
        self.source, self.settings, self.image = source, deepcopy(settings), image
        self._read, self._identity, self._guard, self._hold = read, identity_check, guard_check, on_local_hold
        self._lock = threading.RLock()
        self._outer = source.outer_lock
        self.held_reason = self.local_hold_error = None
        self.adoption_cleanup = []

    def _checked(self, operation):
        with self._outer, self._lock:
            require(self.held_reason is None, 'Native rules binding already held')
            try:
                _none(self._identity); _none(self._guard); self.source.check()
                result = operation()
                _none(self._identity); _none(self._guard); self.source.check()
                return result
            except BaseException as exc:
                self.held_reason = type(exc).__name__ + ': ' + str(exc)
                try:
                    _none(self._hold, self.held_reason)
                except BaseException as hold_exc:
                    self.local_hold_error = type(hold_exc).__name__ + ': ' + str(hold_exc)
                self.source.hold('NATIVE_CONTEXT_FAILED')
                raise

    def _config(self):
        def value(address, fmt):
            size = struct.calcsize(fmt)
            raw = self._read(address, size)
            require(type(raw) is bytes and len(raw) == size, 'Incomplete local native field')
            return struct.unpack(fmt, raw)[0]
        image = self.image
        root = value(image + 0x1FCA1E0, '<Q')
        require(root >= 65536, 'Invalid root')
        world = value(root + 0x85130, '<Q')
        require(world >= 65536, 'Invalid world')
        require(value(image + 0x1FD0C5C, '<i') not in (0, -1), 'Settings not initialized')
        scope = self.source.value['scope']
        c = Config(version=1, size=C.sizeof(Config), image=image, root=root, world=world)
        for field, raw in [('room', bytes.fromhex(scope['room_id'])),
                ('epoch', bytes.fromhex(scope['binding_epoch'])),
                ('rules_digest', bytes.fromhex(scope['profile']['rules_sha256']))]:
            getattr(c, field)[:] = raw
        for i, side in enumerate(('A', 'B')):
            c.force[i] = scope['bindings'][side]['force_id']
            c.main_district[i] = scope['bindings'][side]['main_district_id']
        c.viewer = value(world + 0x3A, '<B')
        c.year, c.month, c.day = value(world + 0x34, '<H'), value(world + 0x36, '<B'), value(world + 0x37, '<B')
        c.income_key5 = value(image + 0x18EB628, '<I')
        c.world_option8 = (value(world + 0x16A8, '<I') >> 8) & 1
        require(c.viewer == scope['bindings'][self.source.value['player']]['force_id'] and
                c.income_key5 == self.settings['native_income_key5'] and
                c.world_option8 == self.settings['native_world_option8'], 'Local viewer/settings differ')
        validate_node(dict(year=c.year, month=c.month, day=c.day, phase='PLANNING_BOUNDARY'))
        require(value(image + 0x1FCA1E0, '<Q') == root and value(root + 0x85130, '<Q') == world,
                'World changed during native read')
        return bytes(c)

    def export_current(self, world=None):
        """ResidentPort callback; it independently compares the returned Config."""
        return self._checked(self._config)

    def adopt_context(self, source, *, loaded_world=None, new_attachment=None):
        """Explicit ordinary phase handoff, not a rules reset or Ready action.

        PLANNING -> same-period RECONCILING lets an installed module's existing
        callbacks restore against the current checkpoint. For the subsequent
        PLANNING, the trusted outer owner supplies its already loaded current
        WorldGeneration and new local attachment; this method neither creates
        nor commits their world receipt. Never silently repin on failed checks.
        """
        with self._outer, self._lock:
            require(self.held_reason is None, 'Native rules binding already held')
            same_owner = False
            try:
                require(type(source) is ContextSource and source is not self.source and not source.held and
                        not self.source.held, 'Fresh explicit context required')
                old, new = self.source.value, source.value
                require(all(old[k] == new[k] for k in ('player', 'scope', 'control_binding_sha256')),
                        'Room/control identity cannot be adopted')
                require(source.room_lock is self.source.room_lock, 'Cannot change local Room lock owner')
                same_owner = True
                _none(self._identity); _none(self._guard); source.check()
                before, after = old['coordinator'], new['coordinator']
                require(before['state_contract'] == after['state_contract'], 'Coverage contract changed')
                if before['phase'] == 'PLANNING' and after['phase'] == 'RECONCILING':
                    require(loaded_world is None and new_attachment is None and
                            all(before[k] == after[k] for k in ('epoch', 'period', 'node', 'attachments')),
                            'Checkpoint handoff skipped or changed native attachments')
                elif before['phase'] == 'RECONCILING' and after['phase'] == 'PLANNING':
                    require(type(loaded_world) is WorldGeneration and old['checkpoint'] is not None and
                            loaded_world.checkpoint == old['checkpoint']['id'] and
                            hexid(new_attachment, 32) and new_attachment not in before['attachments'].values() and
                            after['attachments'] == {'A': before['attachments']['A'], 'B': new_attachment} and
                            after['period'] == before['period'] + 1 and after['epoch'] != before['epoch'] and
                            after['node'] == old['checkpoint']['manifest']['node'] and
                            after['cut'] == old['checkpoint']['manifest']['cut'], 'Unverified next planning lineage')
                    raw = self._config(); c = Config.from_buffer_copy(raw)
                    require(raw == loaded_world.config and (c.year, c.month, c.day) ==
                            tuple(after['node'][k] for k in ('year', 'month', 'day')),
                            'Current native world differs from supplied loaded world')
                else:
                    raise RoomError('Unsupported context transition; do not skip a phase')
                source.check(); _none(self._identity); _none(self._guard)
                self.source = source
            except BaseException as exc:
                self.held_reason = type(exc).__name__ + ': ' + str(exc)
                try: _none(self._hold, self.held_reason)
                except BaseException as hold_exc:
                    self.local_hold_error = type(hold_exc).__name__ + ': ' + str(hold_exc)
                # The new source owns the latest issued network identity. Hold
                # both without releasing either; retain cleanup uncertainty.
                if same_owner:
                    source.hold('NATIVE_CONTEXT_FAILED')
                    self.adoption_cleanup.append(dict(source='candidate', confirmed=source.revocation_confirmed,
                                                       error=source.revocation_error))
                self.source.hold('NATIVE_CONTEXT_FAILED')
                self.adoption_cleanup.append(dict(source='previous', confirmed=self.source.revocation_confirmed,
                                                   error=self.source.revocation_error))
                raise

    def check_scope(self, world):
        def check():
            require(type(world) is WorldGeneration, 'Typed local world required')
            c = Config.from_buffer_copy(world.config); scope = self.source.value['scope']
            require(c.image == self.image and bytes(c.room).hex() == scope['room_id'] and
                    bytes(c.epoch).hex() == scope['binding_epoch'] and
                    bytes(c.rules_digest).hex() == scope['profile']['rules_sha256'] and
                    list(c.force) == [scope['bindings'][p]['force_id'] for p in ('A', 'B')] and
                    list(c.main_district) == [scope['bindings'][p]['main_district_id'] for p in ('A', 'B')] and
                    c.viewer == scope['bindings'][self.source.value['player']]['force_id'] and
                    c.income_key5 == self.settings['native_income_key5'] and
                    c.world_option8 == self.settings['native_world_option8'], 'Stale native rules binding')
        return self._checked(check)

    def next_world_request(self, generation, journal):
        """Logical target only. Leaves durable STAGED/INTENT and Room unchanged."""
        def request():
            value = self.source.value; p = value['checkpoint']
            require(value['player'] == 'B' and p is not None and type(journal) is CheckpointJournal,
                    'Pinned guest checkpoint and local journal required')
            identity = journal.identity
            require(identity == dict(schema='san14.checkpoint-journal.v1', local_player='B',
                    checkpoint_id=p['id'], manifest=p['manifest'], scope=value['scope'],
                    attachments=value['coordinator']['attachments']), 'Journal/context differ')
            require(journal.status()['status'] in ('STAGED', 'INTENT'), 'Journal not staged')
            journal.verified_parts()
            node = p['manifest']['node']
            return NextWorldRequest(generation, p['id'], bytes.fromhex(value['scope']['binding_epoch']),
                                    node['year'], node['month'], node['day'])
        return self._checked(request)

    def observe_loaded(self, request):
        """Caller invokes AFTER real load completion; never invokes a loader here."""
        def observe():
            p = self.source.value['checkpoint']
            require(type(request) is NextWorldRequest and p is not None and request.checkpoint == p['id'] and
                    request.epoch.hex() == self.source.value['scope']['binding_epoch'] and
                    (request.year, request.month, request.day) == tuple(p['manifest']['node'][k]
                        for k in ('year', 'month', 'day')), 'Wrong logical target')
            raw = self._config(); c = Config.from_buffer_copy(raw)
            require((c.year, c.month, c.day) == (request.year, request.month, request.day), 'Loaded date differs')
            return WorldGeneration(request.generation, request.checkpoint, raw)
        return self._checked(observe)

    def status(self):
        return dict(held_reason=self.held_reason, local_hold_error=self.local_hold_error,
            protocol_revocation_confirmed=self.source.revocation_confirmed,
            protocol_revocation_error=self.source.revocation_error,
            adoption_cleanup=deepcopy(self.adoption_cleanup),
            remote_context_is_snapshot=True, native_fence_verified=False,
            native_load_started=False, full_world_verified=False, ready=False)
