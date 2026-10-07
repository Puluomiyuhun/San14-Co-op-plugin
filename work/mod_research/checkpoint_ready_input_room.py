"""Room-side wiring for the controlled three-consumer input smoke only.

Native control is the trusted local host port to Gate::Request/Disconnect and
its real combined Gate/Dispatcher snapshots. It is not a packet deserializer.
Even perfect subset counters cannot supply ReadyBarrierRoom's complete hold.
"""
from checkpoint_ready_barrier import NativeReadyAction
from checkpoint_planning_hold_room_adapter import input_digest


class RestrictedReadyInputBridge:
    def __init__(self, room, player, native):
        self.room, self.player, self.native = room, player, native
        self.action = None

    def begin(self):
        if self.action is not None:
            raise RuntimeError('A local action is already claimed')
        self.action = self.room.take_native_action(self.player)
        if type(self.action) is not NativeReadyAction or input_digest(self.action.binding) != self.native.input_binding_digest:
            self.stop()
            raise RuntimeError('Wrong room, round, connection or attachment')
        # This accepts a control request only. It is never execution evidence.
        if self.native.request(self.action.operation, self.action.generation) is not True:
            self.stop()
            raise RuntimeError('Native combined input request refused')
        return self.inspect()

    def inspect(self):
        if self.action is None:
            raise RuntimeError('No claimed action')
        value = self.native.snapshot()
        if value['gate']['action'] != self.action.generation:
            self.stop()
            raise RuntimeError('Stale native action')
        return dict(operation=self.action.operation, generation=self.action.generation,
                    native=value, restricted_smoke_only=True,
                    room_ready_eligible=False, full_input_hold=False,
                    remaining='Dynamic child UI callbacks, posted messages, other states and physical release are not fully covered.')

    def acknowledge_ready(self):
        # Unconditional refusal, including reports altered to claim full=True.
        # Revoke native replay/gate authority before faulting the room.
        self.stop()
        raise RuntimeError('Three-consumer smoke cannot acknowledge complete room Ready')

    def stop(self):
        self.native.disconnect()
        if self.action is not None:
            self.room.native_fault(self.action)
