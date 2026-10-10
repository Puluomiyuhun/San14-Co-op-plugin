"""B reward Runner with a one-shot, retained HWND input-policy owner.

Only the audited window messages are held. First checkpoint load precedes the
input installation; device/engine-wide exclusion and window restoration are not
provided. No independent reward runtime, automatic retry or DLL unload.
"""
import hashlib,secrets
from pathlib import Path
import b_reward_runner as predecessor
import b_reward_native_port as native
import player_input_lease_bootstrap_port as bootstrap
import player_input_lease_port as inputs
from a_runtime_reward_port import SharedCallState
from reward_observed_context import CheckedPort,need

SOURCES=('b_input_reward_runner.py','player_input_lease_bootstrap_port.py','player_input_lease_port.py')

class Runner(predecessor.Runner):
    def __init__(self,config,link,*,input_build,window,window_thread,input_timeout_ms=3000,on_event,**kw):
        need(type(input_build) is bootstrap.Build and type(window) is int and window>0 and
             type(window_thread) is int and window_thread>0 and type(input_timeout_ms) is int and
             50<=input_timeout_ms<=5000,'Explicit approved window bootstrap identity required')
        need(callable(on_event),'Explicit planning consumer required')
        self.input_build=input_build;self.window=window;self.window_thread=window_thread;self.input_timeout_ms=input_timeout_ms
        self.input=None;self.input_attempted=False;self.input_bootstrap=None;self.input_phase=None;self.input_receipt=None
        self.user_event=on_event
        super().__init__(config,link,on_event=self._input_event,**kw)

    def _reward_preflight(self):
        super()._reward_preflight();bootstrap.approved(self.input_build)

    def _reward_sources(self,pins):
        super()._reward_sources(pins)
        for name in SOURCES:
            path=predecessor.HERE/name
            need(pins.get(str(path.resolve()))==hashlib.sha256(path.read_bytes()).hexdigest(),
                 'Input Runner source missing or changed: '+name)

    def _input_event(self,name,runner):
        need(runner is self,'Foreign Runner event')
        if name=='reward-planning-open':self._install_input()
        self.user_event(name,self)

    def _install_input(self):
        with self.reward_lock:
            need(not self.input_attempted and self.input is None and self.phase=='REWARD_PLANNING' and
                 self.reward is not None and self.reward.phase=='ACTIVE','One bootstrap after first formal load required')
            owner=self.reward.native;port=owner.checked_port;s=self.session
            need(type(owner) is native.NativePort and type(port) is CheckedPort and port.native is owner and
                 owner.session is s and owner.guest is self.guest and s.warm.api.reader is s.reader and
                 type(owner.state) is SharedCallState and owner.transport.state is owner.state,
                 'Exact retained B reward owner and shared native call gate required')
            need(port.calls==0 and port.input_lease is None and len(self.guest.history)==len(s.sessions)==1,
                 'Install input before any B reward execution')
            owner.state.require_known();pid,birth,epoch,attachment=port.binding
            need(pid==self.local['pid'] and birth==self.local['birth'] and attachment==self.guest.attachments['B'],
                 'B input process/attachment differs')
            binding=inputs.Binding();binding.room[:]=bytes.fromhex(s.scope['room_id'])
            binding.attachment[:]=bytes.fromhex(attachment);binding.epoch[:]=bytes.fromhex(epoch)
            binding.period=self.guest.period;binding.seat=1
            self.input_attempted=True
            try:
                self.input=bootstrap.bootstrap(s.warm.api,build=self.input_build,binding=binding,
                    nonce=secrets.token_bytes(32),pid=pid,birth=birth,window=self.window,window_thread=self.window_thread,
                    call_state=owner.state,records=self.records/'input-bootstrap',timeout_ms=self.input_timeout_ms)
                self.input_bootstrap=self.input.bootstrap_record
                need(self.input.state is owner.state,'Input call uncertainty must share B native state')
                port.attach_input_lease(self.input)
                self.input_receipt=self.input.request_phase(0,False);self.input_phase='PLANNING'
                self._record('input-planning.json',dict(receipt=self.input_receipt,first_load_preceded_install=True,
                    all_input_coverage=False,window_owner_retained=True))
            except BaseException as exc:
                self.input_bootstrap=getattr(exc,'retained_input_bootstrap',self.input_bootstrap)
                raise

    def finish_input(self):
        with self.reward_lock:
            need(self.phase=='REWARD_PLANNING' and self.reward is not None and self.reward.phase=='ACTIVE' and
                 not self.finish_requested.is_set() and self.input is not None and self.input_phase=='PLANNING',
                 'Acknowledged input Planning required before Ready')
            try:
                self.input_receipt=self.input.request_phase(0,True);self.input_phase='READY'
                self._record('input-ready.json',dict(receipt=self.input_receipt,remote_reward_allowed=True))
                return super().finish_input()
            except BaseException as exc:
                self._terminal(exc);raise

    def _before_apply(self,generation):
        super()._before_apply(generation)
        if generation==2:
            need(self.input is not None and self.input_phase=='READY' and self.reward.phase=='RELEASED',
                 'Ready input and retired reward lane required before second load')
            self.input_receipt=self.input.request_phase(2);self.input_phase='LOAD'
            self._record('input-load.json',dict(receipt=self.input_receipt,old_reward_queue_retired=True,
                audited_window_messages_held=True,full_input_coverage=False))

    def finish_native(self):
        need(self.input is not None and self.input_phase=='LOAD','Second load must remain input-held')
        s=self.input.snapshot()
        need(s.phase==2 and s.held and s.acknowledged and not s.pending and not s.active and not s.leaseId and
             s.revision==s.acknowledgedRevision and not s.remoteExecutionPolicyOpen and not s.localCommandPolicyOpen,
             'Final input Load acknowledgement/drain missing')
        self.cleanup.update(input_owner_retained=True,input_window_restored=False,audited_window_messages_held=True,
            input_global_exclusion_proven=False,input_bootstrap=self.input_bootstrap,
            source_restore_scope='warm-load and human-rules entries; input WndProc remains retained')
        self._record('input-final-held.json',dict(snapshot=bootstrap.common.base.values(s),unload_attempted=False))
        super().finish_native()

    def _terminal(self,exc):
        if self.input is not None and not self.cleanup.get('local_handles_closed'):
            try:self.input.fail(None,exc)
            except BaseException as secondary:self.input_hold_error=repr(secondary)
        self.cleanup.update(input_owner_retained=self.input_attempted,input_window_restored=False,
            input_bootstrap=self.input_bootstrap,input_global_exclusion_proven=False)
        super()._terminal(exc)

def run(config,link,**kw):return Runner(config,link,**kw).run()
