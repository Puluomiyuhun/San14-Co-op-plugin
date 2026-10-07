"""Trusted local ReadyBarrierRoom-to-native subset interface; no network endpoint.

The supplied Context must already be bound on its actual owned game thread.
This module never creates/injects one, never fabricates full input receipts, and
cannot acknowledge ReadyBarrierRoom until the missing native coverage exists.
"""
import ctypes as C
from hashlib import sha256
import json
from checkpoint_ready_barrier import NativeReadyAction
from authoritative_sync import canonical


class NativeIdentity(C.Structure):
    _fields_=[('attempt',C.c_ubyte*16),('attachment',C.c_ubyte*16),('owner_generation',C.c_uint64)]
class NativeBinding(C.Structure):
    _fields_=[('native',NativeIdentity),('period',C.c_uint64),('epoch',C.c_uint64),('room_input_digest',C.c_ubyte*32)]
class NativeReport(C.Structure):
    _fields_=[('status',C.c_uint32),('phase',C.c_uint32)]+[(x,C.c_uint64) for x in (
        'action_generation','revision','boundary_call','neutral_cycle','local_entered','local_rejected','remote_entered','remote_rejected',
        'local_inflight','replay_inflight','last_replay_sequence','open_replay_tickets','cancellations','exceptions','native_returns')]+[(x,C.c_bool) for x in (
        'covered_local_gate_closed','covered_local_drained','covered_replays_drained','paired_planning_boundary','covered_operation_completed',
        'input_held','full_input_hold','physical_release_proven','room_ack_eligible','installed_in_game','game_threads_paused')]
assert C.sizeof(NativeBinding)==88 and C.sizeof(NativeReport)==144


def input_digest(action_binding):
    value=json.loads(action_binding) if isinstance(action_binding,bytes) else dict(action_binding)
    value.pop('applied_prefix',None)
    # Full room epoch/attachment/connection strings stay in this digest. Native
    # epoch below is a separate host generation value, never a truncated UUID.
    return sha256(canonical(value)).digest()


def make_native_binding(input_binding,*,attempt,attachment,owner_generation,native_epoch):
    if len(attempt)!=16 or len(attachment)!=16 or not any(attempt) or not any(attachment):raise ValueError('Exact locally bound 16-byte native IDs required')
    if type(owner_generation)is not int or not 0<owner_generation<2**64 or type(native_epoch)is not int or not 0<native_epoch<2**64:raise ValueError('Local native generation and epoch required')
    value=json.loads(input_binding) if isinstance(input_binding,bytes) else dict(input_binding)
    if type(value.get('period'))is not int or not 0<value['period']<2**64:raise ValueError('Native period out of range')
    result=NativeBinding();result.native.attempt[:]=attempt;result.native.attachment[:]=attachment
    result.native.owner_generation=owner_generation;result.period=value['period'];result.epoch=native_epoch
    result.room_input_digest[:]=input_digest(value);return result


class NativeControl:
    """Normally loaded local DLL and already-owned Context; control calls only."""
    def __init__(self,dll_path,context,binding):
        if type(binding)is not NativeBinding or not context:raise ValueError('Bound native context required')
        self.binding=NativeBinding.from_buffer_copy(binding);self.context=C.c_void_p(context)
        self.dll=C.CDLL(str(dll_path))
        self.dll.PlanningHoldRequest.argtypes=[C.c_void_p,C.POINTER(NativeBinding),C.c_uint32,C.c_uint64];self.dll.PlanningHoldRequest.restype=C.c_uint32
        self.dll.PlanningHoldSnapshot.argtypes=[C.c_void_p,C.POINTER(NativeReport)];self.dll.PlanningHoldSnapshot.restype=C.c_bool
        self.dll.PlanningHoldDisconnect.argtypes=[C.c_void_p];self.dll.PlanningHoldDisconnect.restype=None
    def request(self,operation,generation):
        if type(generation)is not int or not 0<generation<2**64:raise ValueError('Native action generation out of range')
        return self.dll.PlanningHoldRequest(self.context,C.byref(self.binding),{'HOLD':0,'DRAIN':1,'RELEASE':2}[operation],generation)
    def snapshot(self):
        report=NativeReport()
        if not self.dll.PlanningHoldSnapshot(self.context,C.byref(report)):raise RuntimeError('Native context unavailable')
        return {key:getattr(report,key) for key,_ in report._fields_}
    def disconnect(self):self.dll.PlanningHoldDisconnect(self.context)


class RoomPlanningHoldAdapter:
    def __init__(self,room,player,native_control):
        self.room=room;self.player=player;self.native=native_control;self.action=None
    def begin_owned_subset(self):
        if self.action is not None:raise RuntimeError('One claimed local action at a time')
        action=self.room.take_native_action(self.player)
        self.action=action
        if type(action)is not NativeReadyAction or input_digest(action.binding)!=bytes(self.native.binding.room_input_digest):
            self.fail_closed();raise RuntimeError('Native room/period/attachment binding mismatch')
        if self.native.request(action.operation,action.generation)!=0:
            self.fail_closed();raise RuntimeError('Native subset request refused')
        return self.inspect_subset()
    def inspect_subset(self):
        if self.action is None:raise RuntimeError('No locally claimed action')
        report=self.native.snapshot()
        if report['action_generation']!=self.action.generation:raise RuntimeError('Stale native action report')
        return dict(operation=self.action.operation,generation=self.action.generation,native=report,
                    room_ack_eligible=False,live_authority=False,
                    blockers=['Only reward/sortie entry bodies and one audited mouse query are gated.',
                              'Native UI transaction cancellation and other command/input routes are not covered.',
                              'Owner pool-thread continuity and physical input release are not proven.',
                              'No real-game deep replay ownership provider is wired.'])
    def acknowledge_ready(self):
        # This is intentionally not a bool-to-room-receipt converter. Even a
        # corrupt/caller-edited native report cannot open the room gate.
        self.fail_closed()
        raise RuntimeError('Native subset cannot acknowledge complete Ready input hold')
    def fail_closed(self):
        self.native.disconnect()  # Revoke local native authority before room fault.
        if self.action is not None:self.room.native_fault(self.action)
