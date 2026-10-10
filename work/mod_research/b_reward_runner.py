"""Explicit B entry successor: bootstrap, shared reward planning, restore, load2.

No automatic finish-input and no A Save Runtime. The trusted local caller may
submit B proposals or explicitly end its input window. UI/menu interception is
not supplied here. All native modules and failed owners remain retained.
"""
from b_observed_start import *
from b_observed_start import Runner as FrozenRunner
from b_reward_session import RewardSession,discovery_context
import threading

REWARD_SOURCES=('b_reward_runner.py','b_reward_session.py','b_reward_native_port.py',
    'reward_planning_discovery.py','a_reward_runtime_mount.py','a_runtime_reward_port.py',
    'reward_observed_context.py','reward_observed_flow.py','reward_checkpoint_observer.py')


class Runner(FrozenRunner):
    def __init__(self,config,link,*,native_build,report_key_path,cut_key_path,on_event):
        super().__init__(config,link)
        need(callable(on_event),'Explicit local planning event consumer required')
        self.native_build=native_build;self.report_key_path=Path(report_key_path);self.cut_key_path=Path(cut_key_path)
        self.on_event=on_event;self.reward=None;self.finish_requested=threading.Event();self.reward_lock=threading.RLock()

    def _reward_preflight(self):
        from b_reward_native_port import approved_build
        approved_build(self.native_build)
        load_key(self.report_key_path);load_key(self.cut_key_path)

    def _reward_sources(self,pins):
        for name in REWARD_SOURCES:
            path=HERE/name
            need(pins.get(str(path.resolve()))==hashlib.sha256(path.read_bytes()).hexdigest(),'Reward startup source missing or changed: '+name)
        for name in ('reward_room_flow.py','execution_journal.py'):
            path=ROOT/'outputs/san14-link'/name
            need(pins.get(str(path.resolve()))==hashlib.sha256(path.read_bytes()).hexdigest(),'Reward journal source missing or changed: '+name)

    def finish_input(self):
        with self.reward_lock:
            need(self.phase=='REWARD_PLANNING' and self.reward is not None and self.reward.phase=='ACTIVE' and
                 not self.finish_requested.is_set(),'B planning input has not opened or already ended')
            self.finish_requested.set()

    def submit(self,district_id,officer_ids):
        with self.reward_lock:
            need(self.phase=='REWARD_PLANNING' and not self.finish_requested.is_set() and self.reward is not None,
                 'B planning does not accept new commands')
            return self.reward.submit(district_id,officer_ids)

    def _reward_planning(self,profile):
        end=time.monotonic()+self.local['wait_seconds'];self.phase='AWAITING_REWARD_MOUNT'
        while True:
            need(time.monotonic()<end,'A reward mount wait timed out; no reconnect')
            discovery=request_ok(self.link.control,dict(action='planning_reward_context'))
            if discovery_context(discovery) is not None:break
            time.sleep(.05)
        try:
            self.reward=RewardSession.open(session=self.session,guest=self.guest,profile=profile,discovery=discovery,
                build=self.native_build,report_key_path=self.report_key_path,cut_key_path=self.cut_key_path,
                records=self.records/'reward-planning')
        except BaseException as exc:
            self.reward=getattr(exc,'retained_reward_session',self.reward);raise
        self.phase='REWARD_PLANNING';self.on_event('reward-planning-open',self)
        end=time.monotonic()+self.local['wait_seconds']
        while self.reward.phase!='RELEASED':
            need(time.monotonic()<end,'Reward planning timed out; retain native owner')
            with self.reward_lock:
                if self.finish_requested.is_set() and not self.reward.cut.prepared:self.reward.finish_input()
                self.reward.poll()
            time.sleep(.01)
        self.phase='REWARD_RESTORED';self.on_event('reward-planning-restored',self)

    def _before_apply(self,generation):
        if generation==2:
            need(self.reward is not None,'Missing reward retirement owner')
            self.reward.assert_released()
            self._record('before-second-load.json',dict(reward_sources_restored=True,old_queue_retired=True,
                no_pending_native_intent=True,profile_sha256=hashlib.sha256(self.reward.profile_bytes).hexdigest()))

    def _terminal(self,exc):
        if self.reward is not None and self.reward.phase not in ('HELD','RELEASED'):
            try:self.reward.hold(exc)
            except BaseException as secondary:self.reward_hold_error=repr(secondary)
        super()._terminal(exc)

    def run(self):
        need(self.phase=='NEW','Runner cannot be replayed');self.phase='CHECKING'
        primary=None
        try:
            self._reward_preflight();checked=preflight(self.config);self._reward_sources(checked['sources']);self.records.mkdir(parents=True,exist_ok=False)
            self._record('preflight.json',checked)
            old,raw=files.read_file(Path(self.local['target']));need(old==self.local['initial_target'],'Target drift before backup')
            files.save_new(self.records/'original-CC03.bin',raw);self._record('original-target.json',old)
            scope=None;before=self.local['initial_node']
            for generation in (1,2):
                c=self._context(generation,scope);validate_scope(c['scope']);scope=c['scope'];m=c['manifest']
                need(canonical(scope['profile'])==canonical(self.config['network']['profile']),
                     'Authenticated compatibility profile differs from invitation')
                for side,key in (('A','source_player'),('B','target_player')):
                    v=self.local[key];need(scope['bindings'][side]==dict(force_id=v['force'],main_district_id=v['district']),
                                           'Authenticated seat differs from local native identity')
                need(scope['profile']['rules_sha256']==digest(self.local['rules']),'Room rules differ')
                wanted=before if generation==1 else next_node(before)
                need(m['node']==wanted,'Expected same-day bootstrap then exactly one turn')
                p=make_profile(self.local,m['parts']['world.s14'],before,m['node'],generation)
                receive=receive_bootstrap_staged if generation==1 else receive_staged
                received=receive(self.link.control,self.link.connect_download,checkpoint_id=c['checkpoint_id'],
                    scope=scope,epoch=c['epoch'],period=c['period'],cut=m['cut'],attachments=c['attachments'],
                    directory=self.records/f'received-{generation}')
                self.received.append(received)
                if generation==1:self._open(c,p,checked['sources'])
                q=NextWorldRequest(generation+1,c['checkpoint_id'],secrets.token_bytes(16),
                                   *(m['node'][k] for k in ('year','month','day')))
                self._before_apply(generation)
                self.phase='APPLYING';reply=self.guest.apply(received,q,p)
                self._record(f'formal-{generation}.json',reply);before=m['node']
                if generation==1:
                    self._reward_planning(p)
            self.finish_native()
        except BaseException as exc:
            primary=exc;self._terminal(exc)
        finally:
            if self.records.exists():
                try:
                    self._notify()
                    if primary is None:self._wait_host_finished()
                except BaseException as exc:
                    if primary is None:primary=exc;self._terminal(exc)
                    else:self.notification_error=type(exc).__name__
            try:self.link.close()
            except BaseException as exc:
                if primary is None:primary=exc;self._terminal(exc)
                else:self.network_close_error=type(exc).__name__
        if primary is not None:raise primary
        self.phase='COMPLETE'
        result=dict(result='PASS_B_REWARD_TWO_CHECKPOINTS_RESTORED',cleanup=self.cleanup,
            reward_native=self.reward.receipt,old_reward_queue_retired=True,
            native_gameplay_enabled=False,full_world_verified=False,input_exclusion_proven=False,
            scheduler_fence_proven=False,human_no_new_commands=True,network_closed=True)
        self._record('result.json',result);return result


def run(config,link,**kw):return Runner(config,link,**kw).run()
