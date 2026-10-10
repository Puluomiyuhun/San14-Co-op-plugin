"""Reward projection checks with the retained, rebind-capable HWND owner.

The execution/unknown/result checks remain the predecessor implementation.
Attaching this lease does not open input or install any native reward bridge.
"""
from reward_observed_context import CheckedPort as Predecessor, need
from player_input_rebind_port import InputLease
from b_remote_chain_session import Session
from b_observed_chain_completion import GuestCompletion


class _CheckpointLease:
    """Explicit mapping: native reward nonce epoch != checkpoint room epoch."""
    def __init__(self, port, lease):
        self.port, self.lease = port, lease
        self.native = port.native
        s, g = self.native.session, self.native.guest
        need(type(s) is Session and type(g) is GuestCompletion and g.session is s,
             'Exact retained chain owners required for input epoch mapping')
        self.session, self.guest = s, g
        self.period, self.epoch = g.period, g.epoch
        self.attachment = g.attachments['B']
        self.reward_binding = tuple(port.binding)
        self.input_binding = (*self.reward_binding[:2], self.epoch, self.attachment)
        self._check()

    def _check(self):
        p, g, s, lease = self.port, self.guest, self.session, self.lease
        need(p.native is self.native and self.native.session is s and self.native.guest is g and
             g.session is s and tuple(p.binding) == self.reward_binding and
             self.native.identity() == self.reward_binding and g.period == self.period and
             g.epoch == self.epoch and g.attachments['B'] == self.attachment and
             self.reward_binding[3] == self.attachment and s.phase in ('ACTIVE', 'REWARD_PLANNING') and
             g.phase == 'ACTIVE', 'Reward to checkpoint input mapping changed')
        need(bytes(lease.binding.room).hex() == s.scope['room_id'] and lease.binding.seat == 1 and
             lease.binding.period == self.period, 'Input room, seat or period differs')
        return lease.verify_binding(self.input_binding, self.native)

    def begin(self, binding):
        need(tuple(binding) == self.reward_binding, 'Foreign reward binding')
        self._check()
        return self.lease.begin(self.input_binding)

    def complete(self, ticket):
        self._check()
        return self.lease.complete(ticket)

    def fail(self, ticket, exc):
        # Never add a read/native identity RPC after an uncertain command.
        return self.lease.fail(ticket, exc)


class CheckedPort(Predecessor):
    def attach_input_lease(self, lease):
        with self.sampler.lock:
            need(type(lease) is InputLease and self.input_lease is None and self.calls == 0,
                 'Attach exact rebind input lease once before reward execution')
            self.input_lease = _CheckpointLease(self, lease)
            self.retained_input_lease = lease
