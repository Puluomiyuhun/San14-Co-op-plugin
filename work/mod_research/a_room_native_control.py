"""Room-bound, once-only two-save control. No process discovery or game advance.

The caller owns approved native installation/cleanup, the room service, world
observer and its declared input boundary. This module does not supply a fence.
Only coordinator.loaded receipts release the first wait; diagnostic ACKs do not.
"""
from copy import deepcopy
import hashlib
import time

import a_save_runtime_contract as wire
import a_save_repeat_contract as repeat
from a_native_turn_start_control import repeat_state
from a_save_runtime_control import require
from authoritative_sync import digest


def prepare_from_room(prep, binding):
    """Return a copy BEFORE native Prepare; never patch an installed runtime."""
    c = binding.coordinator
    with binding.room.lock, c.lock:
        binding.validate_context()
        n = c.native_binding(prep.epoch)
        require(n['generation'] == n['period'] == 1, 'Initial bootstrap binding required')
        q = wire.Prepare.from_buffer_copy(bytes(prep))
        require(0 < q.epoch < 2**64-1, 'Native epoch cannot advance')
        require((q.year, q.month, q.day) == tuple(n['node'][k] for k in ('year','month','day')),
                'Native capture differs from room bootstrap date')
        require(q.force == c.scope['bindings']['A']['force_id'], 'Native capture is not room A')
        require(binding._native_room_id == bytes.fromhex(digest(c.scope)), 'Native room scope differs')
        wire.put_bytes(q.roomId, binding._native_room_id)
        q.nativeRoomEpoch = binding._native_room_epoch
        q.period, q.epoch = n['period'], n['epoch']
        wire.put_bytes(q.roomInputDigest, bytes.fromhex(n['input_digest']))
        return q


class RoomTurnControl:
    """One retained channel, two exports, two formal room completions.

    Construct the FreshSaveBinding with artifact_reader=this.copy_artifact.
    Returned bytes are the exact current channel result, never disk archives.
    Reusing this object after any attempt is rejected, including timeouts.
    """
    def __init__(self):
        self.started = False
        self._artifacts = {}
        self._copied = set()

    def copy_artifact(self, generation):
        require(self.started and generation in self._artifacts and generation not in self._copied,
                'Only this attempt\'s completed channel artifact may be published once')
        self._copied.add(generation)
        return self._artifacts[generation]

    def drive(self, channel, prep, filenames, call, keep, event, binding, observe_world,
              *, wait_seconds=600, clock=time.monotonic, pause=time.sleep):
        require(not self.started, 'Room control already attempted; retain evidence, do not replay')
        self.started = True
        try:
            return self._drive(channel, prep, filenames, call, keep, event, binding,
                               observe_world, wait_seconds, clock, pause)
        except BaseException:
            # No retry, native Stop, rollback or DLL unload is hidden here.
            # Owning launcher must perform its established uncertain-call cleanup.
            binding.hold('ROOM_NATIVE_CONTROL_FAILED')
            raise

    def _drive(self, channel, prep, filenames, call, keep, event, binding, observe_world,
               wait_seconds, clock, pause):
        require(type(wait_seconds) is int and 1 <= wait_seconds <= 1800, 'Bounded wait required')
        require(len(filenames) == 2 and filenames[0] != filenames[1], 'Two unique filenames required')
        require(binding._reader == self.copy_artifact, 'Binding must retain this exact artifact reader')
        c, room = binding.coordinator, binding.room
        require(bytes(prepare_from_room(prep, binding)) == bytes(prep),
                'Room preparation must be bound before installing the native runtime')
        scope = deepcopy(c.scope)
        host_attachment = c.attachments['A']

        def current():
            room._bound(c)
            require(c.connected == {'A','B'} and c.phase != 'HELD' and c.scope == scope
                    and c.attachments['A'] == host_attachment, 'Room disconnected, held or rebound')
            binding._available()

        def wait(predicate, label):
            deadline = clock() + wait_seconds
            while True:
                with room.lock, c.lock:
                    current()
                    if predicate():
                        return
                # Keeps the SAME authenticated native pipe alive while TLS is
                # served elsewhere. This is not a Ready or world assertion.
                channel.snapshot()
                require(clock() < deadline, label + ' timed out; keep terminal evidence')
                pause(.25)

        def loaded(package):
            m = package.manifest
            receipt = c.applied_receipts.get(package.checkpoint_id)
            if receipt is None:
                require(c.phase == 'RECONCILING' and c.checkpoint_id == package.checkpoint_id,
                        'Unconfirmed checkpoint left reconciliation')
                return False
            require(receipt['player'] == 'B' and receipt['epoch'] == m['epoch']
                    and receipt['checkpoint_id'] == package.checkpoint_id
                    and receipt['world_sha256'] == m['world_sha256']
                    and receipt['viewer_force'] == scope['bindings']['B']['force_id']
                    and receipt['attachment'] == c.attachments['B']
                    and receipt['intent'] == c.load_intent
                    and c.node == m['node'] and c.period == m['period'] + 1
                    and c.epoch != m['epoch'] and c.phase in ('PLANNING','SEALED','RUNNING'),
                    'Formal completion no longer matches this export')
            return True

        def save(generation):
            with room.lock, c.lock:
                current()
                export_node = binding.validate_context()['node']
                observation = lambda: observe_world(deepcopy(export_node))
                reservation = binding.reserve(generation, filenames[generation-1], observation())
            event('submit-' + str(generation), dict(binding_sha256=reservation.binding_sha256,
                                                    filename=filenames[generation-1]))
            channel.submit(reservation)
            artifact = channel.wait_artifact(generation, timeout=30)
            self._artifacts[generation] = artifact
            keep(generation, filenames[generation-1], artifact)
            package = binding.publish(generation, observation)
            event('await-b-' + str(generation), dict(checkpoint_id=package.checkpoint_id,
                                                     node=package.manifest['node']))
            wait(lambda: loaded(package), 'B formal completion')
            event('b-complete-' + str(generation), dict(checkpoint_id=package.checkpoint_id))
            return artifact, package

        initial_world = observe_world(deepcopy(c.node))
        first, first_package = save(1)

        def ready_for_turn():
            loaded(first_package)
            require(c.phase in ('PLANNING','SEALED','RUNNING'), 'Unexpected pre-turn room phase')
            if c.phase != 'RUNNING':
                return False
            # Narrow pilot allows no commands. Real set_ready/seal/begin must
            # come from the room owner, not be invented by this control loop.
            require(c.seal and c.seal['sequence'] == 0 and c.seal['prefix_sha256'] == digest(scope)
                    and not any(c.inflight.values()), 'This diagnostic does not execute new commands')
            return True

        event('await-room-turn', dict(bootstrap_checkpoint=first_package.checkpoint_id))
        wait(ready_for_turn, 'Room ready and sealed input')
        with room.lock, c.lock:
            current()
            require(observe_world(deepcopy(c.node)) == initial_world, 'A changed while waiting for bootstrap completion')
            n = c.native_binding(prep.epoch)
            require(n['generation'] == n['period'] == 2 and n['epoch'] == prep.epoch + 1,
                    'Room generation does not match native successor')
        command = repeat.envelope(repeat.Next, 'RequestNext', bytes(prep.nonce))
        q = command.request
        require(hashlib.sha256(first.data).hexdigest() == first.sha256, 'Previous bytes changed')
        q.previousGeneration, q.generation, q.period, q.epoch = 1, 2, n['period'], n['epoch']
        wire.put_bytes(q.previousSha256, bytes.fromhex(first.sha256))
        wire.put_bytes(q.inputDigest, bytes.fromhex(n['input_digest']))
        q.year, q.month, q.day = (n['node'][k] for k in ('year','month','day'))
        event('request-next', dict(native_binding=n, previous_sha256=first.sha256))
        response, _ = call('RequestNext', command)
        require(bytes(response.request) == bytes(command.request), 'Native response changed RequestNext')
        announced = False

        def native_returned():
            nonlocal announced
            require(c.native_binding(prep.epoch) == n, 'Sealed room changed during native turn')
            sample, _ = call('RepeatSnapshot')
            status = repeat_state(sample, command)
            if sample.state == 3 and not announced:
                event('running-await-human', dict(automatic_game_advance=False,
                    message='B开局加载已确认，房间已封口；现在可以正常推进一旬，不新增命令。'))
                announced = True
            return status['second_save_binding_ready']

        wait(native_returned, 'Native turn return')
        second, second_package = save(2)
        return dict(two_native_artifacts=True, formal_completions=2,
                    checkpoint_ids=[first_package.checkpoint_id, second_package.checkpoint_id],
                    running_observed=announced, game_advance_called=False,
                    full_world_verified=False, input_fence_provided=False,
                    two_game_ready=False, native_gameplay_enabled=False)
