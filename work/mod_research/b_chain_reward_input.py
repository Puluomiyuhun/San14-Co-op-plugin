"""Open each B reward window only after current-world HWND rebinding.

No installer, Ready shortcut or load call: the caller retains the actual chain
session, native reward owner, input owner and cut consumer for their lifetime.
"""
from pathlib import Path
import threading
from b_chain_reward_session import RewardSession
from b_chain_reward_native_port import NativePort
from reward_rebind_context import CheckedPort
from player_input_rebind_port import InputLease
from b_warm_received_apply import write_once
from reward_observed_context import need


class Window:
    def __init__(self, *args, **kwargs):
        raise TypeError('Use Window.open')

    @classmethod
    def open(cls, reward, input_owner, *, records):
        need(type(reward) is RewardSession and type(input_owner) is InputLease,
             'Exact current reward session and retained input owner required')
        with reward.lock, reward.guest._lock, reward.session._lock, input_owner.lock:
            s, g, native = reward.session, reward.guest, reward.native
            n = len(g.history)
            need(n in (1, 2) and reward.phase == 'ACTIVE' and reward.failed is None and
                 type(native) is NativePort and type(native.checked_port) is CheckedPort and
                 native.session is s and native.guest is g and reward.replica.port is native.checked_port,
                 'Fresh reward window for the current chain required')
            need(getattr(s, '_chain_input_owner', None) is input_owner and
                 s._chain_input_transitions[n]['phase'] == 'REBOUND_HELD',
                 'Current checkpoint input must be acknowledged and remain held')
            claims = getattr(s, '_chain_reward_input_windows', None)
            if claims is None:
                claims = {}; s._chain_reward_input_windows = claims
            need(n not in claims and set(claims) == set(range(1, n)), 'Input window already attempted or skipped')
            need(n == 1 or claims[n-1].phase == 'LOAD_HELD', 'Previous input window did not enter LOAD')
            directory = Path(records)
            need(directory.is_absolute(), 'Absolute fresh input window records required')
            directory.mkdir(parents=True, exist_ok=False)
            obj = cls.__new__(cls); claims[n] = obj
            obj.reward, obj.input, obj.records, obj.window = reward, input_owner, directory, n
            obj.phase = 'OPENING'; obj.failed = None; obj.lock = threading.RLock()
            try:
                reward._binding(); native.state.require_known(); input_owner.state.require_known()
                need(native.state is input_owner.state and native.transport.state is input_owner.state,
                     'Retained input and current reward must share one unknown-call gate')
                obj._held()
                need(not reward.cut.prepared and not reward.cut.attest_attempted and
                     native.checked_port.calls == 0 and native.checked_port.input_lease is None,
                     'Fresh unused reward lane required before opening input')
                write_once(directory/'open-intent.json', dict(checkpoint=g.history[-1]['checkpoint_id'],
                    period=g.period, epoch=g.epoch, attachment=g.attachments['B'], full_input_exclusion_proven=False))
                native.checked_port.attach_input_lease(input_owner)
                receipt = input_owner.request_phase(0, False)
                reward._binding(); native.checked_port.input_lease._check()
                write_once(directory/'opened.json', dict(receipt=receipt, native_menu_capture_enabled=False,
                    full_input_exclusion_proven=False))
                obj.phase = 'PLANNING'
                return obj
            except BaseException as exc:
                obj._fail(exc); exc.retained_input_window = obj; raise

    def _held(self):
        s = self.input.snapshot()
        need(s.phase == 2 and s.held and s.acknowledged and not s.localReady and
             s.revision == s.acknowledgedRevision and s.leasesIssued == s.leasesCompleted and
             not any((s.pending, s.active, s.leaseId, s.localCommandPolicyOpen, s.remoteExecutionPolicyOpen)),
             'Current input requires drained acknowledged LOAD hold')
        return s

    def finish_input(self):
        with self.reward.lock, self.lock:
            need(self.phase == 'PLANNING' and self.failed is None, 'Planning input already ended')
            try:
                self.reward._binding()
                receipt = self.input.request_phase(0, True)
                write_once(self.records/'ready-input.json', dict(receipt=receipt, remote_rewards_allowed=True))
                result = self.reward.finish_input()
                self.phase = 'READY'
                return result
            except BaseException as exc:
                self._fail(exc); raise

    def ensure_load_before_ready(self):
        """Called by native retirement before Session.ACTIVE or network Ready."""
        with self.reward.lock, self.lock:
            need(self.phase == 'READY' and self.failed is None, 'Ready input required before LOAD')
            try:
                r = self.reward
                need(r.phase == 'RESTORED' and r.session.phase == 'REWARD_PLANNING' and
                     r.receipt is not None and r.restore_attempted and r.native.closed and
                     r.session._chain_reward_input_windows.get(self.window) is self,
                     'Current native retirement must precede LOAD and network Ready')
                receipt = self.input.request_phase(2)
                self._held()
                write_once(self.records/'load-held.json', dict(receipt=receipt, reward_queue_retired=True,
                    full_input_exclusion_proven=False))
                self.phase = 'LOAD_HELD'
                return receipt
            except BaseException as exc:
                self._fail(exc); raise

    def prepare_load(self):
        """Verify the hold that must already precede the Ready publication."""
        with self.reward.lock, self.lock:
            try:
                self.reward.assert_released()
                need(self.phase == 'LOAD_HELD' and self.failed is None,
                     'LOAD acknowledgement must precede Ready and loading')
                return self._held()
            except BaseException as exc:
                self._fail(exc); raise

    def _fail(self, exc):
        self.phase = 'HELD'; self.failed = self.failed or repr(exc)
        try:
            self.input.fail(None, exc)
        except BaseException as secondary:
            self.input_hold_error = repr(secondary)
        self.reward.hold(exc)
        try:
            write_once(self.records/'failed.json', dict(error=self.failed, no_retry=True))
        except BaseException as secondary:
            self.record_error = repr(secondary)
