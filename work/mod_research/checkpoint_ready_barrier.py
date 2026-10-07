"""Room Ready intents gated by locally verified native input acknowledgements.

Successor room: uses the real ProgressRoom and PeriodCoordinator, but replaces
the old network-ready shortcut. No packet can supply an input/world receipt.
The trusted native adapter obtains a local action object, executes it on its
owned game boundary, then acknowledges it. No native adapter is installed here.
"""
from copy import deepcopy
from dataclasses import dataclass
import time

from checkpoint_room_progress import ProgressRoom
from checkpoint_room_artifacts import require, RoomError, SyncError
from authoritative_sync import canonical


@dataclass(frozen=True, eq=False)
class NativeReadyAction:
    """Process-local identity, never deserialized from a peer message."""
    player: str
    operation: str
    generation: int
    binding: bytes


class ReadyBarrierRoom(ProgressRoom):
    def __init__(self, manifest, *, clock=time.monotonic, acknowledgement_timeout=15):
        super().__init__(manifest)
        require(type(acknowledgement_timeout) in (int, float) and 1 <= acknowledgement_timeout <= 60,
                'Bad native acknowledgement timeout')
        self._ready_clock = clock
        self._ready_timeout = acknowledgement_timeout
        self._ready_epoch = None
        self._ready_generation = 0
        self._ready_rows = {}
        self._ready_failure = None
        self._ready_seal = None

    def bind_coordinator(self, coordinator):
        with self.lock:
            super().bind_coordinator(coordinator)
            self._reset_rows()

    def _reset_rows(self):
        self._ready_epoch = self._coordinator.epoch
        self._ready_seal = None
        self._ready_rows = {p: dict(desired=False, state='OPEN', action=None,
            deadline=None, receipt=None, hold_receipt=None, hold_action=None) for p in ('A', 'B')}

    def _planning(self):
        c = self._coordinator
        require(c is not None, 'No bound coordinator')
        self._bound(c)
        require(self._ready_failure is None and c.phase == 'PLANNING' and
                c.connected == {'A', 'B'} and c.epoch == self._ready_epoch,
                'Planning input handoff is not open')
        self._expire()
        require(self._ready_failure is None, 'Native acknowledgement timed out')
        return c

    def _binding(self, player):
        c = self._coordinator
        return dict(room_id=self.room_id, binding_epoch=self.binding_epoch,
            epoch=c.epoch, period=c.period, player=player,
            connection=self.players[player]['connection'], attachment=c.attachments[player],
            node=deepcopy(c.node), force=deepcopy(c.scope['bindings'][player]),
            applied_prefix=deepcopy(c.reports[player]))

    def _input_binding(self, player):
        # Holding LOCAL input must not reject later authorized remote replays.
        # The final applied prefix is checked separately by both DRAIN actions.
        binding = self._binding(player)
        del binding['applied_prefix']
        return binding

    def _action_binding(self, player, operation):
        return self._binding(player) if operation == 'DRAIN' else self._input_binding(player)

    def _issue(self, player, operation):
        self._ready_generation += 1
        action = NativeReadyAction(player, operation, self._ready_generation,
                                   canonical(self._action_binding(player, operation)))
        row = self._ready_rows[player]
        row.update(state=operation + '_PENDING', action=action, receipt=None,
                   deadline=self._ready_clock() + self._ready_timeout)
        return action

    def _fail(self, reason):
        if self._ready_failure is not None:
            return
        self._ready_failure = reason
        self._held = reason
        c = self._coordinator
        if c is not None:
            c.ready.clear()
            c.phase = 'HELD'
        # This is a stop REQUEST, not proof that an already running game stopped.
        for row in self._ready_rows.values():
            row.update(state='HELD_UNCONFIRMED', action=None, receipt=None, deadline=None,
                       hold_receipt=None, hold_action=None)
        if self.artifacts:
            self.artifacts.close()
            self.download_endpoint._retire_old()

    def _expire(self):
        if any(r['deadline'] is not None and self._ready_clock() >= r['deadline']
               for r in self._ready_rows.values()):
            self._fail('NATIVE_READY_ACK_TIMEOUT')

    def _request_ready(self, player, connection, request):
        require(set(request) == {'action', 'epoch', 'ready'} and type(request['ready']) is bool,
                'Invalid Ready intent')
        c = self._planning()
        require(player in self.players and self.players[player]['connection'] == connection and
                request['epoch'] == c.epoch, 'Stale/foreign Ready intent')
        row = self._ready_rows[player]
        require(row['state'] not in ('HOLD_APPLYING', 'RELEASE_APPLYING', 'DRAIN_APPLYING'),
                'Native action is executing; wait for its acknowledgement')
        if request['ready'] == row['desired']:
            return self.ready_status()
        require(row['state'] != 'RELEASE_PENDING', 'Wait until native input is released')
        require(not request['ready'] or not c.inflight[player], 'Own commands still pending')
        # Cancel can revoke unclaimed final-drain tickets, but cannot race an
        # adapter that is already inside its native boundary.
        require(not any(r['state'] == 'DRAIN_APPLYING' for r in self._ready_rows.values()),
                'Final native drain is executing; wait for its acknowledgement')
        for r in self._ready_rows.values():
            if r['state'] in ('DRAIN_PENDING', 'SEAL_READY'):
                r.update(state='READY_HELD', action=None, receipt=deepcopy(r['hold_receipt']), deadline=None)
        # Remove readiness BEFORE any asynchronous release can happen.
        c.set_ready(player, c.epoch, False)
        row['desired'] = request['ready']
        self._issue(player, 'HOLD' if row['desired'] else 'RELEASE')
        return self.ready_status()

    def take_native_action(self, player):
        """Trusted adapter only. Claim one action; no automatic retries."""
        with self.lock:
            c = self._coordinator
            require(c is not None, 'No bound coordinator')
            with c.lock:
                self._planning()
                require(player in self._ready_rows, 'Unknown player')
                row = self._ready_rows[player]
                require(row['state'] in ('HOLD_PENDING', 'RELEASE_PENDING', 'DRAIN_PENDING'), 'No unconsumed native action')
                action = row['action']
                if action.binding != canonical(self._action_binding(player, action.operation)):
                    self._fail('NATIVE_ACTION_BOUNDARY_CHANGED')
                    raise SyncError('Native action binding changed')
                row['state'] = action.operation + '_APPLYING'
                return action

    def acknowledge_native_action(self, action, observation):
        """Trusted verified adapter observation, NOT a JSON room endpoint.

        HOLD closes local input and drains local command creation, while still
        allowing ordered remote replay. DRAIN rechecks the held input and the
        final command/world prefix after both players hold. RELEASE must be
        ordered after readiness revocation. A caller dictionary
        by itself is not native evidence; live integration remains unavailable.
        """
        with self.lock:
            c = self._coordinator
            require(c is not None, 'No coordinator')
            with c.lock:
                try:
                    self._planning()
                    require(type(action) is NativeReadyAction and action.player in self._ready_rows,
                            'Local action identity required')
                    row = self._ready_rows[action.player]
                    require(row['action'] is action and row['state'] == action.operation + '_APPLYING',
                            'Stale/unclaimed native acknowledgement')
                    binding = self._action_binding(action.player, action.operation)
                    require(action.binding == canonical(binding), 'Game/commands changed during Ready')
                    expected = dict(binding=binding, generation=action.generation,
                        operation=action.operation, input_held=action.operation != 'RELEASE',
                        planning_boundary=True, pending_local_commands=0)
                    if action.operation == 'DRAIN':
                        expected['pending_replays'] = 0
                    require(type(observation) is dict and canonical(observation) == canonical(expected),
                            'Native input/command acknowledgement differs')
                    c.set_ready(action.player, c.epoch, action.operation != 'RELEASE')
                    state = dict(HOLD='READY_HELD', RELEASE='OPEN', DRAIN='SEAL_READY')[action.operation]
                    row.update(state=state, action=None,
                               deadline=None, receipt=deepcopy(observation))
                    if action.operation == 'HOLD':
                        row.update(hold_receipt=deepcopy(observation), hold_action=action)
                    elif action.operation == 'RELEASE':
                        row.update(hold_receipt=None, hold_action=None)
                    return self.ready_status()
                except (RoomError, SyncError, TypeError, ValueError):
                    self._fail('NATIVE_READY_ACK_UNCERTAIN')
                    raise

    def begin_ready_drain(self):
        """Trusted host adapter: request fresh final-prefix receipts, never time advance."""
        with self.lock:
            c = self._coordinator
            require(c is not None, 'No coordinator')
            with c.lock:
                self._planning()
                require(all(r['state'] == 'READY_HELD' for r in self._ready_rows.values()) and
                        c.ready == {'A', 'B'}, 'Both local input holds must be acknowledged')
                require(not any(c.inflight.values()) and c.reports['A'] == c.reports['B'],
                        'Wait for both applied command prefixes to drain')
                for player, row in self._ready_rows.items():
                    if canonical(row['hold_receipt']['binding']) != canonical(self._input_binding(player)):
                        self._fail('HELD_BOUNDARY_CHANGED')
                        raise SyncError('Held native attachment changed before final drain')
                for player in ('A', 'B'):
                    self._issue(player, 'DRAIN')
                return self.ready_status()

    def seal_ready_inputs(self):
        """Trusted host adapter: seal after both fresh final-drain receipts.

        Returns the existing coordinator permit. This method does not invoke
        begin_simulation, native game time, or release either player's input.
        """
        with self.lock:
            c = self._coordinator
            require(c is not None, 'No coordinator')
            with c.lock:
                self._planning()
                require(all(r['state'] == 'SEAL_READY' for r in self._ready_rows.values()),
                        'Both final native command drains must be acknowledged')
                for player, row in self._ready_rows.items():
                    if canonical(row['receipt']['binding']) != canonical(self._binding(player)):
                        self._fail('HELD_BOUNDARY_CHANGED')
                        raise SyncError('Held boundary changed before sealing')
                self._ready_seal = c.seal_inputs()
                return deepcopy(self._ready_seal)

    def native_fault(self, action):
        """An owned adapter cannot complete/maintain its action or input hold."""
        with self.lock:
            c = self._coordinator
            require(c is not None, 'No coordinator')
            with c.lock:
                require(type(action) is NativeReadyAction and action.player in self._ready_rows,
                        'Foreign native failure')
                row = self._ready_rows[action.player]
                require(row['action'] is action or row['hold_action'] is action, 'Foreign native failure')
                self._fail('NATIVE_READY_ADAPTER_FAILED')
                return self.ready_status()

    def ready_status(self):
        with self.lock:
            if self._coordinator is not None:
                with self._coordinator.lock:
                    self._expire()
            return dict(epoch=self._ready_epoch,
                players={p: dict(requested=r['desired'], state=r['state']) for p, r in self._ready_rows.items()},
                ready=sorted(self._coordinator.ready) if self._coordinator else [],
                held_reason=self._ready_failure, seal_created=self._ready_seal is not None,
                request_native_hold_all=self._ready_failure is not None,
                native_backend_connected=False, native_pause_confirmed=False,
                native_gameplay_enabled=False, native_simulation_started=False)

    def view(self, player):
        with self.lock:
            state = super().view(player)
            state['ready_barrier'] = self.ready_status()
            return state

    def handle(self, player, connection_id, request):
        if type(request) is dict and request.get('action') in ('period_ready', 'period_ready_status'):
            try:
                with self.lock:
                    c = self._coordinator
                    require(c is not None, 'No coordinator')
                    with c.lock:
                        require(player in self.players and self.players[player]['connection'] == connection_id,
                                'Invalid control connection')
                        if request['action'] == 'period_ready_status':
                            require(set(request) == {'action'}, 'Invalid Ready status request')
                            status = self.ready_status()
                        else:
                            status = self._request_ready(player, connection_id, request)
                        return dict(ok=True, ready_barrier=status, applied_to_game=False)
            except (RoomError, SyncError):
                return dict(ok=False, error='Ready request rejected; inspect current barrier status', applied_to_game=False)
        return super().handle(player, connection_id, request)

    def disconnect(self, player, connection_id):
        with self.lock:
            current = self.players.get(player, {}).get('connection') == connection_id
            super().disconnect(player, connection_id)
            if current and self._coordinator is not None:
                with self._coordinator.lock:
                    self._fail('CONTROL_CONNECTION_CHANGED')

    def close_checkpoints(self):
        with self.lock:
            if self._coordinator is not None:
                with self._coordinator.lock:
                    self._fail('ROOM_CLOSED')
            super().close_checkpoints()

    def adopt_verified_planning_epoch(self, release_observations):
        """Trusted post-load adapter only, AFTER existing world receipt commit.

        Both clients must acknowledge the new planning/input-release boundary.
        Old Ready intents cannot carry over to the next period. No loaded/world
        receipt is created or inferred by this method.
        """
        with self.lock:
            c = self._coordinator
            require(c is not None, 'No coordinator')
            with c.lock:
                self._bound(c)
                require(self._ready_failure is None and self._ready_seal is not None and
                        c.phase == 'PLANNING' and c.epoch != self._ready_epoch and
                        c.period == self._ready_seal['period'] + 1 and
                        self.artifacts is not None and self.artifacts.checkpoint_id in c.applied_receipts,
                        'No completed next-period world receipt')
                require(type(release_observations) is dict and set(release_observations) == {'A', 'B'},
                        'Both native release boundaries required')
                for player in ('A', 'B'):
                    require(canonical(release_observations[player]) == canonical(dict(
                        binding=self._binding(player), input_held=False, planning_boundary=True, pending_commands=0)),
                        'New planning/input release differs')
                self._reset_rows()
                return self.ready_status()
