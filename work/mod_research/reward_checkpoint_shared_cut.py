"""Paired reward prefix -> SAME observed-room checkpoint cut (finite evidence).

Successor of reward_checkpoint_gate. No alternate coordinator, seal bypass,
native owner, input fence, native retry or world-contract relabeling is created.
"""
from copy import deepcopy
import secrets

from authoritative_sync import digest, scope_from_room
from reward_checkpoint_gate import CheckpointGate
from reward_checkpoint_observer import CutObserver, validate_body, unpack, key_check, ACTION, COVERAGE
from reward_observed_context import CONTRACT, need
import execution_journal as journal
import b_warm_world as world


class SharedCutGate(CheckpointGate):
    def __init__(self, room, coordinator, flow, host_observer, *, guest_cut_key):
        need(type(host_observer) is CutObserver and host_observer.replica is flow.host,
             'Cut observer must retain this exact host replica/reader')
        key_check(guest_cut_key)
        with flow.lock, room.lock, coordinator.lock:
            need(coordinator.state_contract == world.CONTRACT and
                 coordinator.reports['A'] == coordinator.reports['B'], 'Equal prior checkpoint cut required')
            self.base = deepcopy(coordinator.reports['A'])
            self.observer = host_observer; self._cut_key = guest_cut_key
            self.finished = set(); self.challenge = None; self.guest_sample = None
            super().__init__(room, coordinator, flow)

    def retire_drained(self):
        raise ValueError('Shared-cut gate requires prepare_cut and close_drained; no zero-cut fallback')

    def _rows(self):
        with self.flow.db() as db:
            return [dict(r) for r in db.execute('SELECT * FROM requests ORDER BY ordinal')]

    def _still_collecting(self):
        need(self.state in ('ACTIVE', 'COLLECTING'), 'Shared cut retired or held')
        try:
            self._validate_current()
            need(self.coordinator.reports == {'A': self.base, 'B': self.base}, 'Prior checkpoint cut changed')
        except BaseException as exc:
            self._hold(exc); raise

    def handle(self, player, connection, request):
        try:
            with self.lock, self.room.lock, self.coordinator.lock:
                need(type(request) is dict and player in self.room.players and
                     self.room.players[player]['connection'] == connection, 'Current authenticated seat required')
                action = request.get('action')
                if action == 'reward_next' and self.state in ('COLLECTING', 'RETIRED_SHARED_CUT'):
                    # A status read and the following consume call are separate
                    # RPCs. Closure may happen between them. Return an empty
                    # read without reviving the old command/report epoch.
                    c, b = self.coordinator, self.binding
                    self.room._bound(c); self.flow._envelope(request, set())
                    need(player == 'B' and c.connected == {'A', 'B'} and
                         c.scope == b['scope'] == scope_from_room(self.room) and
                         c.epoch == b['checkpoint_epoch'] and c.period == b['checkpoint_period'] and
                         c.attachments == b['attachments'] and c.node == b['node'] and
                         c.phase in ('PLANNING', 'SEALED', 'RUNNING'),
                         'Closed queue read belongs to a stale room')
                    return dict(ok=True, intent=None, planning_closed=True, native_gameplay_enabled=False)
                if action == 'reward_cut_status':
                    need(set(request) == {'action'}, 'Exact cut status request required')
                    return dict(ok=True, state=self.state, finished=sorted(self.finished),
                        challenge=deepcopy(self.challenge), receipt=(None if self.receipt is None else
                        {k: deepcopy(self.receipt[k]) for k in
                         ('schema', 'cut', 'proof_sha256', 'checkpoint_cut_installed')}),
                        native_gameplay_enabled=False)
                if action == 'reward_cut_prepare':
                    self._still_collecting()
                    need(set(request) == {'action', 'epoch'} and request['epoch'] == self.binding['checkpoint_epoch'],
                         'Exact current planning epoch required')
                    self.finished.add(player)
                    return dict(ok=True, finished=sorted(self.finished), native_gameplay_enabled=False)
                if action == ACTION:
                    self._still_collecting()
                    need(player == 'B' and self.state == 'COLLECTING' and self.challenge is not None,
                         'Guest observation requires a drained challenge')
                    try:
                        body = validate_body(unpack(self._cut_key, request), self.challenge, 'B')
                        need(self.guest_sample is None or self.guest_sample == body, 'Conflicting cut observation')
                        self.guest_sample = deepcopy(body)
                    except BaseException as exc:
                        self._hold(exc); raise
                    return dict(ok=True, challenge_sha256=digest(self.challenge), native_gameplay_enabled=False)
                if action == 'reward_submit':
                    need(player not in self.finished, 'Player finished input; remote applications may still drain')
                if isinstance(action, str) and action.startswith('reward_') and self.state == 'COLLECTING':
                    raise ValueError('Reward command/report epoch sealed for cut sampling')
                return super().handle(player, connection, request)
        except (ValueError, TypeError, KeyError, RuntimeError) as exc:
            return dict(ok=False, error=str(exc), native_gameplay_enabled=False)

    def prepare_cut(self):
        """Trusted owner: None while either player is still issuing/draining input."""
        with self.lock, self.room.lock, self.coordinator.lock:
            self._still_collecting()
            if self.challenge is not None:
                return deepcopy(self.challenge)
            rows = self._rows()
            if self.finished != {'A', 'B'} or self.flow.last_guest is None or not all(
                    r['status'] in ('PAIRED', 'REJECTED') for r in rows):
                return None
            try:
                host = self.flow.host.report(); guest = deepcopy(self.flow.last_guest)
                journal.compare_applied_prefixes(self.flow.scope, host['sequence'], {'A': host, 'B': guest})
                need(sum(r['status'] == 'PAIRED' for r in rows) == host['sequence'],
                     'Journal count differs from paired authority queue')
                self.challenge = dict(schema='san14.reward-cut-challenge.v1', id=secrets.token_hex(16),
                    binding=deepcopy(self.binding), base=deepcopy(self.base),
                    reward_scope=deepcopy(self.flow.scope), reports=dict(A=host, B=guest))
                self.state = 'COLLECTING'
                return deepcopy(self.challenge)
            except BaseException as exc:
                self._hold(exc); raise

    def close_drained(self):
        """Installs a real cumulative command count; never marks either seat Ready."""
        with self.lock, self.room.lock, self.coordinator.lock:
            self._still_collecting()
            if self.challenge is None or self.guest_sample is None:
                return None
            try:
                challenge = self.challenge
                host = validate_body(self.observer.capture(challenge), challenge, 'A')
                guest = validate_body(self.guest_sample, challenge, 'B')
                need(host['reward_projection'] == guest['reward_projection'], 'Reward field projections differ')
                comparison = world.compare(host['world_sample'], guest['world_sample'])
                need(comparison['result'] == 'PARTIAL_MATCH', 'Current world table projections differ')
                count = host['reward_report']['sequence']; total = self.base['sequence'] + count
                descriptor = dict(schema='san14.reward-checkpoint-command-cut.v1',
                    binding=deepcopy(self.binding), previous=deepcopy(self.base), sequence=total,
                    reward_sequence=count, reward_contract=CONTRACT,
                    reward_scope_sha256=digest(self.flow.scope),
                    reward_prefix_sha256=host['reward_report']['prefix_sha256'],
                    reward_projection_sha256=host['reward_report']['state_sha256'],
                    checkpoint_contract=world.CONTRACT,
                    checkpoint_world_sha256=host['world_sample']['partial_sha256'])
                prefix = digest(descriptor) if count else self.base['prefix_sha256']
                target = dict(sequence=total, prefix_sha256=prefix,
                              world_sha256=host['world_sample']['partial_sha256'])
                need(count > 0 or target == self.base, 'No-command state changed; cannot invent a command')
                proof = dict(schema='san14.reward-checkpoint-shared-cut.v1', binding=deepcopy(self.binding),
                    descriptor=descriptor, cut=target, challenge=deepcopy(challenge),
                    host_observation=host, guest_observation=guest, comparison=comparison,
                    checkpoint_cut_installed=True, ready_authorized=False, save_authorized=False,
                    native_gameplay_enabled=False, **COVERAGE)
                # All fallible observations precede mutation. Any later failure
                # is terminal and keeps the room HELD, including a half report.
                for seat in ('A', 'B'):
                    self.coordinator.applied_prefix(seat, self.binding['checkpoint_epoch'],
                        total, prefix, target['world_sha256'], self.binding['attachments'][seat])
                self.flow.retire('Paired reward epoch permanently incorporated into checkpoint cut')
                for seat in ('A', 'B'):
                    self.coordinator.set_pending(seat, self.binding['checkpoint_epoch'], set())
                self.state = 'RETIRED_SHARED_CUT'
                proof['proof_sha256'] = digest(proof); self.receipt = deepcopy(proof)
                return deepcopy(proof)
            except BaseException as exc:
                self._hold(exc); raise

    def assert_sealed(self, seal):
        """Validate existing original coordinator permission; never create it."""
        with self.lock, self.room.lock, self.coordinator.lock:
            c = self.coordinator; b = self.binding
            need(self.state == 'RETIRED_SHARED_CUT' and self.receipt is not None and
                 self.room._reward_checkpoint_gate is self and self.room._coordinator is c and
                 c.scope == b['scope'] == scope_from_room(self.room) and c.epoch == b['checkpoint_epoch'] and
                 c.period == b['checkpoint_period'] and c.attachments == b['attachments'] and c.node == b['node'] and
                 c.state_contract == world.CONTRACT and c.connected == {'A', 'B'} and c.event is None and
                 c.phase in ('SEALED', 'RUNNING') and not any(c.inflight.values()) and
                 c.ready == {'A', 'B'} and seal == c.seal and type(seal) is dict and
                 seal['epoch'] == c.epoch and seal['period'] == c.period and
                 {k: seal[k] for k in self.receipt['cut']} == self.receipt['cut'] and
                 c.reports == {'A': self.receipt['cut'], 'B': self.receipt['cut']},
                 'No current paired reward planning seal')
            return deepcopy(self.receipt)

    def observe_sealed(self, node):
        """Current same-reader pre-RequestNext check; finite human-idle semantics."""
        with self.lock, self.room.lock, self.coordinator.lock:
            try:
                self.assert_sealed(self.coordinator.seal)
                need(node == self.binding['node'], 'Sealed date changed')
                observation, sample = self.observer.local_observation(self.challenge,
                    self.challenge['reports']['A'])
                need(sample['world_sample']['partial_sha256'] == self.receipt['cut']['world_sha256'],
                     'Host world changed after shared cut')
                return observation
            except BaseException as exc:
                self._hold(exc); raise
