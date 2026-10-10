"""Two B reward windows; permanently retire each native owner before its successor."""
from copy import deepcopy
import hashlib
from pathlib import Path
import threading

from authoritative_sync import canonical
from b_remote_chain_session import Session
from b_observed_chain_completion import GuestCompletion
from b_warm_profile_contract import Profile,validate_profile
from b_warm_received_apply import write_once
from b_warm_adapter_key import load_key
from reward_observed_context import CONTRACT,need
from reward_rebind_context import CheckedPort
from b_chain_reward_flow import GuestConsumer,GuestCutConsumer
from reward_room_flow import Replica,envelope
import execution_journal as journal
from reward_planning_discovery import SCHEMA as DISCOVERY_SCHEMA


def discovery_context(reply):
    need(type(reply) is dict and set(reply)=={'ok','schema','ready','context','native_gameplay_enabled'} and
         reply['ok'] is True and reply['schema']==DISCOVERY_SCHEMA and type(reply['ready']) is bool and
         reply['native_gameplay_enabled'] is False,'Exact authenticated reward discovery required')
    if not reply['ready']:
        need(reply['context'] is None,'Unready discovery contains authority');return None
    context=reply['context']
    need(type(context) is dict and set(context)=={'scope','profile_sha256','checkpoint_epoch','checkpoint_period','node','attachments'},
         'Exact planning context required')
    return deepcopy(context)


class RewardSession:
    def __init__(self,*args,**kw):raise TypeError('Use RewardSession.open')

    @classmethod
    def open(cls,*,session,guest,**kw):
        need(type(session) is Session and type(guest) is GuestCompletion and guest.session is session,
             'Exact retained B checkpoint owners required')
        with guest._lock,session._lock:
            return cls._open(session=session,guest=guest,**kw)

    @classmethod
    def _open(cls,*,session,guest,profile,discovery,build,report_key_path,cut_key_path,records):
        from b_chain_reward_native_port import NativePort
        need(type(session) is Session and type(guest) is GuestCompletion and guest.session is session,
             'Exact retained B checkpoint owners required')
        window=len(guest.history)
        need(window in (1,2) and session.phase==guest.phase=='ACTIVE' and len(session.sessions)==window and
             guest.period==window+1 and not session.lifecycle.current.retired,'Completed bootstrap and live target rules required')
        need(type(profile) is Profile,'Actual current checkpoint profile required');validate_profile(profile)
        claims=getattr(session,'_b_chain_reward_windows',None)
        if claims is None:claims={};session._b_chain_reward_windows=claims
        need(window not in claims and set(claims)==set(range(1,window)), 'Ordered once-only reward windows required')
        if window>1:
            previous=claims[window-1]
            need(previous.phase=='RELEASED' and previous.failed is None and previous.restore_attempted and previous.receipt is not None,
                 'Previous reward window did not release its native bridge')
            state=previous.replica.journal.status()
            need(state['phase']=='IDLE' and not state['unknown_sequences'] and previous.replica.port.sampler.failed is not None,
                 'Previous reward journal was not permanently retired')
        from b_chain_input_transition import observe_completed
        observed=observe_completed(session,guest)
        need(observed['node']==dict(year=profile.loaded.year,month=profile.loaded.month,day=profile.loaded.day,phase='PLANNING_BOUNDARY'),
             'Current loaded profile date differs')
        current=session.boundary.profile
        need(bytes(current.file)==bytes(profile.file) and bytes(current.source)==bytes(profile.source) and
             bytes(current.target)==bytes(profile.target),'Current accepted profile identity differs')
        discovery=discovery_context(discovery);need(discovery is not None,'Reward mount is not ready')
        need(discovery['checkpoint_period']==guest.period and discovery['node']==dict(year=profile.loaded.year,month=profile.loaded.month,day=profile.loaded.day,phase='PLANNING_BOUNDARY') and discovery['profile_sha256']==hashlib.sha256(bytes(profile)).hexdigest() and
             discovery['checkpoint_epoch']==guest.epoch and discovery['attachments']==guest.attachments,
             'Reward discovery differs from formal bootstrap')
        scope=deepcopy(discovery['scope']);journal.validate_scope(scope)
        if window>1:
            need(scope['timeline_epoch']!=previous.replica.scope['timeline_epoch'] and guest.epoch!=previous.bound[2] and
                 guest.attachments['B']!=previous.bound[3]['B'],'Fresh reward journal/context epoch required')
        need(scope['state_contract']==CONTRACT and all(scope[k]==session.scope[k] for k in
             ('room_id','binding_epoch','profile','bindings')),'Reward scope differs from checkpoint room')
        reply=session.control.request(dict(action='reward_scope'))
        need(reply.get('ok') is True and reply['scope']==scope and reply['attachment']==guest.attachments['B'],
             'Current reward scope/attachment differs')
        report_key=load_key(report_key_path);cut_key=load_key(cut_key_path)
        records=Path(records);records.mkdir(parents=True,exist_ok=False)
        obj=cls.__new__(cls);claims[window]=obj;obj.window=window;obj.session=session;obj.guest=guest;obj.records=records;obj.profile_bytes=bytes(profile)
        obj.scope_bytes=canonical(scope);obj.phase='OPENING';obj.failed=None;obj.native=None;obj.replica=None
        obj.consumer=None;obj.cut=None;obj.restore_attempted=False;obj.receipt=None;obj.lock=threading.RLock()
        obj.bound=(session.reader,session.lifecycle.current,guest.epoch,deepcopy(guest.attachments),guest.history[window-1]['checkpoint_id'])
        try:
            obj.native=NativePort.open(session=session,guest=guest,profile=profile,scope=scope,records=records/'native',build=build)
            need(type(obj.native) is NativePort and type(obj.native.checked_port) is CheckedPort and
                 obj.native.session is session and obj.native.guest is guest,'Same retained B provider required')
            session.phase='REWARD_PLANNING'
            obj.replica=Replica(records/'execution.sqlite',scope,'B',obj.native.checked_port)
            obj.native.attach_journal(obj.replica.journal)
            obj.consumer=GuestConsumer(session.control,obj.replica,report_key)
            obj.cut=GuestCutConsumer(obj.consumer,profile,cut_key=cut_key,checkpoint_epoch=guest.epoch)
            obj.consumer.report();obj.phase='ACTIVE'
            write_once(records/'opened.json',dict(profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),
                checkpoint_id=obj.bound[4],epoch=guest.epoch,attachment=guest.attachments['B'],
                independent_b_user_owner=True,input_exclusion_proven=False))
            return obj
        except BaseException as exc:
            obj.native=getattr(exc,'retained_native_port',obj.native)
            obj.hold(exc);exc.retained_reward_session=obj;raise

    def _binding(self):
        s=self.session;g=self.guest;r,port,epoch,attachments,checkpoint=self.bound
        need(self.failed is None and s._b_chain_reward_windows.get(self.window) is self and
             g.period==self.window+1 and s.phase==('ACTIVE' if self.phase=='RELEASED' else 'REWARD_PLANNING') and g.phase=='ACTIVE' and len(s.sessions)==len(g.history)==self.window and
             s.reader is r and s.lifecycle.current is port and not port.retired and
             g.epoch==epoch and g.attachments==attachments and g.history[self.window-1]['checkpoint_id']==checkpoint and
             canonical(self.replica.scope)==self.scope_bytes,'Reward owner/attachment changed or retired')
        need(not s.warm.calls.uncertain,'Shared native control is uncertain')

    def submit(self,district_id,officer_ids):
        import secrets
        with self.lock:
            try:
                self._binding();need(self.phase=='ACTIVE' and not self.cut.prepared,'B input has ended')
                return self.cut._request(envelope(self.replica.scope,'reward_submit',request_id=secrets.token_hex(16),
                    district_id=district_id,officer_ids=officer_ids))
            except BaseException as exc:self.hold(exc);raise

    def finish_input(self):
        with self.lock:
            try:self._binding();need(self.phase=='ACTIVE','Input is not active');return self.cut.finish_input()
            except BaseException as exc:self.hold(exc);raise

    def poll(self):
        with self.lock:
            try:
                self._binding();need(self.phase=='ACTIVE','Reward window cannot be polled again')
                status=self.cut.poll()
                if status.get('state')=='RETIRED_SHARED_CUT':self._retire(status)
                return status
            except BaseException as exc:self.hold(exc);raise

    def _retire(self,status):
        with self.guest._lock,self.session._lock:
            try:return self._retire_locked(status)
            except BaseException as exc:self.hold(exc);raise

    def _retire_locked(self,status):
        need(self.cut.prepared and self.cut.attest_attempted and status['receipt']['checkpoint_cut_installed'] is True,
             'Explicitly drained and attested shared cut required')
        state=self.replica.journal.status();need(state['phase']=='IDLE' and not state['unknown_sequences'],'Local intent unresolved')
        write_once(self.records/'cut-retirement-intent.json',dict(status=status,local_report=self.replica.report()))
        self.phase='RETIRING';self.replica.port.retire('B reward epoch retired before native world replacement')
        need(not self.restore_attempted,'Native restore cannot repeat');self.restore_attempted=True
        self.receipt=self.native.stop_restore();self.native.verify_restored()
        write_once(self.records/'native-restored.json',self.receipt);self.phase='RESTORED'
        self._hold_input_before_ready()
        self.session.phase='ACTIVE'
        self.cut.ready_after_cut();self.phase='RELEASED'
        write_once(self.records/'released.json',dict(checkpoint_epoch=self.bound[2],old_queue_retired=True,
            native_bridge_restored=True,ready_sent=True,input_exclusion_proven=False))

    def _hold_input_before_ready(self):
        """A native, acknowledged LOAD hold must precede network Ready."""
        windows=getattr(self.session,'_chain_reward_input_windows',{})
        owner=getattr(self.session,'_chain_input_owner',None)
        if owner is None and not windows:
            need(self.native.input_owner is None, 'Installed input owner disappeared before Ready')
            return # Explicit no-input diagnostic mode; no input guarantee inferred.
        from b_chain_reward_input import Window
        from player_input_rebind_port import InputLease
        window=windows.get(self.window)
        need(type(owner) is InputLease and type(window) is Window and window.reward is self and
             window.input is owner and window.window==self.window and
             self.native.checked_port.retained_input_lease is owner,
             'Current exact input owner/window required before Ready')
        need(self.phase=='RESTORED' and self.session.phase=='REWARD_PLANNING',
             'Input must close before enabling checkpoint application')
        window.ensure_load_before_ready()
        need(window.phase=='LOAD_HELD' and window.failed is None and self.phase=='RESTORED' and
             self.session.phase=='REWARD_PLANNING', 'Native LOAD hold not established before Ready')

    def assert_released(self):
        with self.lock:
            try:
                self._binding();need(self.phase=='RELEASED' and self.restore_attempted and self.replica.port.sampler.failed is not None,
                                     'Reward bridge/queue not retired before next load')
                state=self.replica.journal.status();need(state['phase']=='IDLE' and not state['unknown_sequences'],'Old journal uncertain')
                self.native.verify_restored()
            except BaseException as exc:self.hold(exc);raise

    def hold(self,exc):
        self.failed=self.failed or repr(exc);self.phase='HELD'
        if self.replica is not None:self.replica.port.retire(self.failed)
        self.session.phase='TERMINAL';self.session.boundary.hold(self.failed)
        try:write_once(self.records/'held.json',dict(error=self.failed,restore_attempted=self.restore_attempted,
            native_restored=self.receipt is not None,no_replay=True))
        except BaseException as secondary:self.record_error=repr(secondary)
