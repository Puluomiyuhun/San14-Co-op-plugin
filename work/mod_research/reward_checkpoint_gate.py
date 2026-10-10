"""Same-room reward drain veto; no new coordinator or native permission.

The two frozen state contracts remain distinct. A nonempty completed reward
prefix retires into HELD until a successor establishes a common checkpoint cut.
It must never reopen the existing zero-command save/turn control.
"""
from copy import deepcopy
import secrets

from a_observed_room import ObservedRoom
from a_room_bootstrap_protocol import BootstrapCoordinator
from authoritative_sync import scope_from_room
from reward_observed_flow import ObservedRewardFlow
from reward_observed_context import need
import execution_journal as journal


class CheckpointGate:
    """Trusted local owner installs this as the room's control endpoint.

    Existing Room/Coordinator references also see actual pending tokens, so
    their original Ready/seal/reserve checks cannot bypass an active reward
    period. pump_one/retire_drained are local owner operations, not wire actions.
    Native serialization, input exclusion and device coverage remain external.
    """
    def __init__(self, room, coordinator, flow):
        need(type(room) is ObservedRoom and type(coordinator) is BootstrapCoordinator and
             isinstance(flow, ObservedRewardFlow) and flow.room is room,
             'Same actual observed Room, bootstrap coordinator and reward flow required')
        self.room, self.coordinator, self.flow = room, coordinator, flow
        self.lock = flow.lock  # Frozen flow uses flow -> room; never invert it.
        self.state = 'INITIALIZING'; self.receipt = None; self.reason = None
        self.tokens = {p:secrets.token_hex(16) for p in ('A','B')}
        with self.lock, room.lock, coordinator.lock:
            room._bound(coordinator)
            need(coordinator.bootstrap_completed and coordinator.phase == 'PLANNING' and
                 coordinator.connected == {'A','B'} and not coordinator.ready and
                 not any(coordinator.inflight.values()) and coordinator.event is None,
                 'Attach after formal bootstrap at an unused planning boundary')
            need(not hasattr(room, '_reward_checkpoint_gate'),
                 'Reward gate already attempted; old epoch is never reused')
            room_scope = scope_from_room(room)
            need(coordinator.scope == room_scope == flow.period.scope and
                 all(flow.scope[k] == room_scope[k] for k in ('room_id','binding_epoch','profile','bindings')),
                 'Reward room/profile/seat binding differs')
            need(flow.period.attachments == coordinator.attachments and
                 flow.period.node == coordinator.node and flow.period.phase == 'PLANNING' and
                 flow.period.connected == {'A','B'} and not flow.period.ready,
                 'Reward date or local attachment differs from checkpoint boundary')
            status = flow.status()
            need(status['request_count'] == 0 and status['halt'] is None and
                 status['host']['sequence'] == 0 and not status['host']['unknown_sequences'],
                 'Attach before admitting any reward command')
            self.binding = dict(scope=deepcopy(room_scope), checkpoint_epoch=coordinator.epoch,
                checkpoint_period=coordinator.period, attachments=deepcopy(coordinator.attachments),
                node=deepcopy(coordinator.node), checkpoint_contract=coordinator.state_contract,
                reward_scope=deepcopy(flow.scope), reward_epoch=flow.period.epoch)
            # Sticky owner claim. Any subsequent failure keeps the claim/evidence.
            room._reward_checkpoint_gate = self
            try:
                for p in ('A','B'):coordinator.set_pending(p,coordinator.epoch,{self.tokens[p]})
                self.state = 'ACTIVE'
            except BaseException as exc:
                self._hold(exc); raise

    def _current(self):
        need(self.state == 'ACTIVE', 'Reward epoch retired or held; no replay')
        try:self._validate_current()
        except BaseException as exc:
            self._hold(exc);raise

    def _validate_current(self):
        r,c,f,b = self.room,self.coordinator,self.flow,self.binding
        r._bound(c)
        need(r._reward_checkpoint_gate is self and c.scope == b['scope'] == scope_from_room(r) and
             c.epoch == b['checkpoint_epoch'] and c.period == b['checkpoint_period'] and
             c.attachments == b['attachments'] and c.node == b['node'] and
             c.state_contract == b['checkpoint_contract'] and c.phase == 'PLANNING' and
             c.connected == {'A','B'} and c.event is None and not c.ready,
             'Checkpoint boundary drifted; common recovery required')
        need(c.inflight == {p:{token} for p,token in self.tokens.items()},
             'Pending owner tokens changed; no implicit clearing')
        need(f.room is r and f.scope == b['reward_scope'] and f.period.epoch == b['reward_epoch'] and
             f.period.attachments == b['attachments'] and f.period.node == b['node'] and
             f.period.phase == 'PLANNING' and f.period.connected == {'A','B'} and not f.period.ready,
             'Reward epoch/attachment drifted')
        f._active()

    def _hold(self, reason):
        self.reason = self.reason or str(reason)
        self.state = 'HELD'
        c = self.coordinator
        c.ready.clear(); c.phase = 'HELD'
        # Do not clear pending, issue native cancellation, or claim native cleanup.
        try:self.flow.retire(self.reason)
        finally:
            if self.room.artifacts is not None:self.room.artifacts.close()
            self.room.download_endpoint._retire_old()

    def authenticate(self, *args):return self.room.authenticate(*args)

    def disconnect(self, player, connection):
        with self.lock, self.room.lock, self.coordinator.lock:
            if self.room.players.get(player,{}).get('connection') != connection:return
            try:self.flow.disconnect(player,connection)
            finally:self._hold('Authenticated room connection ended')

    def handle(self, player, connection, request):
        """Retain original seat authentication and both frozen wire protocols."""
        try:
            with self.lock, self.room.lock, self.coordinator.lock:
                need(type(request) is dict, 'Expected request object')
                need(player in self.room.players and self.room.players[player]['connection'] == connection,
                     'Current authenticated seat required')
                action = request.get('action')
                if isinstance(action,str) and action.startswith('reward_'):
                    self._current()
                    try:
                        result = self.flow.handle(player,connection,request)
                    finally:
                        if self.flow.status()['halt'] is not None:
                            self._hold('Reward queue held; checkpoint cannot proceed')
                    return result
                # Original period_ready itself sees the two pending tokens.
                # Its false request is harmless; no network action retires us.
                return self.room.handle(player,connection,request)
        except (ValueError,TypeError,KeyError,RuntimeError) as exc:
            return dict(ok=False,error=str(exc),native_gameplay_enabled=False)

    def pump_one(self):
        with self.lock, self.room.lock, self.coordinator.lock:
            self._current()
            try:
                return self.flow.pump_one()
            except BaseException as exc:
                self._hold(exc); raise

    def retire_drained(self):
        """Retire once, preserving actual paired receipts, not fabricated cut0.

        Pending work is an ordinary refusal, so its trusted consumers can finish.
        Context drift/unknown native effects remain terminal via their owners.
        """
        with self.lock, self.room.lock, self.coordinator.lock:
            self._current()
            with self.flow.db() as db:
                rows = [dict(r) for r in db.execute('SELECT * FROM requests ORDER BY ordinal')]
            need(all(r['status'] in ('PAIRED','REJECTED') for r in rows),
                 'Reward queued, dispatching or awaiting guest confirmation')
            need(self.flow.last_guest is not None, 'Guest initial observation not attested')
            try:
                host = self.flow.host.report(); guest = deepcopy(self.flow.last_guest)
                journal.compare_applied_prefixes(self.flow.scope,host['sequence'],{'A':host,'B':guest})
                proof = dict(schema='san14.reward-checkpoint-drain.v1',binding=deepcopy(self.binding),
                    host_report=host,guest_report=guest,
                    requests=[self.flow._public(r) for r in rows],
                    reward_sequence=host['sequence'],reward_prefix_sha256=host['prefix_sha256'],
                    reward_projection_sha256=host['state_sha256'],
                    checkpoint_cut_installed=False,save_authorized=False,
                    input_exclusion_proven=False,full_world_verified=False,native_gameplay_enabled=False)
                empty = host['sequence'] == 0
                self.flow.retire('Reward epoch drained and permanently retired')
                if empty:
                    for p in ('A','B'):
                        self.coordinator.set_pending(p,self.binding['checkpoint_epoch'],set())
                    self.state = 'RETIRED_EMPTY'
                else:
                    self.coordinator.ready.clear();self.coordinator.phase = 'HELD'
                    self.state = 'RETIRED_NEEDS_SHARED_CUT'
                proof['state'] = self.state
                proof['zero_command_control_may_continue'] = empty
                proof['proof_sha256'] = journal.digest(proof)
                self.receipt = deepcopy(proof)
                return proof
            except BaseException as exc:
                self._hold(exc); raise

    def status(self):
        with self.lock, self.room.lock, self.coordinator.lock:
            return dict(state=self.state,reason=self.reason,binding=deepcopy(self.binding),
                receipt=deepcopy(self.receipt),queue=self.flow.status(),
                checkpoint=self.coordinator.status(),native_gameplay_enabled=False)
