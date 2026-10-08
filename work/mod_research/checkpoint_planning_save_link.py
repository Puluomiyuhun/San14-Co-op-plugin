"""Bind a captured planning start to its later fresh-save reservation.

Identity/phase data only. It does not advance a native Session, authenticate a
remote claim, hold input, authorize Save, or infer that simulation finished.
"""
from dataclasses import dataclass
from copy import deepcopy
import json

from checkpoint_fresh_save_binding import FreshSaveBinding, SaveReservation
from authoritative_sync import canonical, digest, next_node, require
from planning_period_scope import from_coordinator, native_digest


@dataclass(frozen=True)
class LinkedReservation:
    reservation: SaveReservation
    context_bytes: bytes

    def context(self):
        # Return an independent value; callers cannot change the captured data.
        return json.loads(self.context_bytes)

    @property
    def context_sha256(self):
        from authoritative_sync import sha
        return sha(self.context_bytes)


class PlanningSaveLink:
    """One planning period, at most one reservation; no reset/retry.

    Construct at period start and retain across actual Room Ready/seal/run.
    Calling from_coordinator again at save time would be wrong: the Coordinator
    is RUNNING, the old epoch still applies, and the saved date is next_node.
    B's verified loaded receipt is what eventually creates the next epoch.
    """
    def __init__(self, binding):
        require(type(binding) is FreshSaveBinding, 'Actual local FreshSaveBinding required')
        self._binding=binding
        c=binding.coordinator
        with binding.room.lock,c.lock:
            self._planning=from_coordinator(c,'A')
            self._scope=deepcopy(c.scope)
            self._attachment=c.attachments['A']
            self._contract=c.state_contract
            self._used=False

    def _check(self):
        c=self._binding.coordinator;s=self._planning
        require(c.scope==self._scope and c.attachments['A']==self._attachment
            and c.state_contract==self._contract, 'Planning source instance changed')
        require(c.epoch==s['timeline_epoch'] and c.period==s['period'] and c.node==s['date'],
            'Planning period rotated or start date changed')
        require(c.phase=='RUNNING' and c.connected=={'A','B'} and c.event is None
            and not any(c.inflight.values()), 'No uninterrupted current export phase')
        require(type(c.seal) is dict and c.seal['epoch']==s['timeline_epoch']
            and c.seal['period']==s['period'] and c.seal['sequence']>=s['base_sequence'],
            'Sealed cut is not descended from captured planning start')

    def reserve(self,generation,filename,observation):
        b=self._binding;c=b.coordinator
        with b.room.lock,c.lock:
            require(not self._used,'Planning reservation attempt already consumed')
            self._check()
            # Consume before calling a function which may reserve and then fail.
            # Invalid/uncertain reservation does not permit a silent second try.
            self._used=True
            reservation=b.reserve(generation,filename,observation)
            q=reservation.request
            saved=next_node(self._planning['date'])
            require((q['year'],q['month'],q['day'])==(saved['year'],saved['month'],saved['day'])
                and q['period']==self._planning['period'] and q['cut']==c.seal['sequence'],
                'Fresh-save request is not this planning period endpoint')
            value=dict(schema='san14.planning-save-link.v1',planning=deepcopy(self._planning),
                planning_native_digest=native_digest(self._planning),
                planning_scope_sha256=digest(self._scope),sealed_input=deepcopy(c.seal),
                saved_node=saved,reservation_binding_sha256=reservation.binding_sha256,
                native_request={**dict(q),'room_id':q['room_id'].hex()},
                requires_post_simulation_native_boundary=True,
                next_planning_epoch_available=False,save_authorized=False,
                full_input_held=False,simulation_permit=False)
            return LinkedReservation(reservation,canonical(value))
