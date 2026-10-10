"""Two-window production Python composition over owned RAM and native/TLS doubles.
No game, DLL export, TLS socket, input opening or Windows target process used.
"""
from copy import deepcopy
from datetime import datetime
import ctypes as C
import hashlib,io,json,sys,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_chain_reward_native_port as native
import b_chain_reward_session as sessionmod
import b_chain_input_transition as transition
import b_reward_native_port_test as old
from reward_observed_fixture import World
from b_remote_chain_session import Session
from b_observed_chain_completion import GuestCompletion
from reward_rebind_context import CheckedPort
from b_warm_profile_contract import Profile
from b_warm_adapter_key import Native
import execution_journal as journal
OUTPUT=None

class Scheduler(old.Scheduler):
    def call(self,name,raw):
        if name=='BRewardConfigure':
            self.calls.append(name);q=native.Configure.from_buffer_copy(raw)
            s=old.old.port.Snapshot();s.header=q.header;s.nonce[:]=q.nonce;s.context=q.context
            s.state=s.configured=1;self.report=s
            return 0,raw
        if name=='BRewardRestore' and self.fault=='restore-unknown':
            self.calls.append(name)
            raise native.RemoteCallUnknown('Owned restore outcome unknown',dict(automatic_retry=False))
        code,answer=super().call(name,raw)
        if name=='BRewardSnapshot':
            s=native.Snapshot.from_buffer_copy(answer)
            if self.fault=='restore-drift':s.slotRestored=0
            return code,bytes(s)
        return code,answer

class Harness:
    def __init__(self,test):
        self.test=test;self.folder=OUTPUT/test._testMethodName;self.folder.mkdir()
        self.w=World(2);self.w.memory.pack(self.w.memory.base+0x2025318,'<Q',self.w.root);self.held=[];self.schedulers=[];self.module_rows=[];self.queue=None
        s=self.s=Session.__new__(Session);g=self.g=GuestCompletion.__new__(GuestCompletion)
        s.reader=self.w.reader;s.native_identity=(self.w.reader.pid,self.w.birth);s.read_birth=lambda:self.w.birth
        s._lock=threading.RLock();g._lock=threading.RLock();g.session=s;g.held=None
        s.factory=SimpleNamespace(uncertain=False);s.boundary=SimpleNamespace(hold=self.held.append,observe=lambda:None)
        s.control=SimpleNamespace(request=self.request,close=lambda:None);g.control=s.control
        api=SimpleNamespace(reader=s.reader,modules=lambda:list(self.module_rows),load_library_address=lambda:123)
        s.warm=SimpleNamespace(calls=SimpleNamespace(uncertain=False),api=api,steam={},first_hooks=[])
        self.ready_calls=0;self.n=0;self.move()
        self.dll=self.folder/'b_reward_owner.dll';self.dll.write_bytes(b'EXPLICIT OWNED DLL LOADER DOUBLE')
        self.report_key=self.folder/'report.key';self.cut_key=self.folder/'cut.key'
        Native().write_new(self.report_key,b'r'*32);Native().write_new(self.cut_key,b'k'*32)
        self.patches=[patch.object(native,'approved_build',return_value=dict(dll=self.dll,sha256=hashlib.sha256(self.dll.read_bytes()).hexdigest(),dependencies=[])),
            patch.object(native,'storage_bindings',return_value=dict(storageVtable=444,read=dict(address=888))),
            patch.object(native,'live_hook_evidence',return_value=[]),patch.object(native,'retained_call',side_effect=self.load),
            patch.object(native,'Transport',side_effect=self.transport),patch.object(transition,'observe_completed',side_effect=self.observed)]
        for p in self.patches:p.start();test.addCleanup(p.stop)
    def move(self):
        self.n+=1;n=self.n;s,g=self.s,self.g
        day=11 if n==1 else 21
        self.w.memory.pack(self.w.world+0x34,'<HBB',203,8,day)
        if n>1:self.w.memory.pack(self.w.people[101]+0x196,'<H',0) # Owned next-turn checkpoint fixture.
        self.w.attachment=('b' if n==1 else 'c')*32
        p=Profile();p.file.name=b'svdexccSC03.s14';p.file.slot=63;p.file.size=123;p.file.sha256[:]=bytes([n])*32
        p.before.year=p.loaded.year=203;p.before.month=p.loaded.month=8;p.before.day=p.loaded.day=day
        p.source.ruler,p.source.force,p.source.district=666,12,11;p.target.ruler,p.target.force,p.target.district=952,2,2;p.currentForce=2
        self.profile=p;s.boundary.profile=Profile.from_buffer_copy(bytes(p))
        g.period=n+1;g.epoch=format(80+n,'032x');g.attachments=dict(A='a'*32,B=self.w.attachment)
        g.history=[dict(checkpoint_id=format(i,'064x')) for i in range(1,n+1)];s.sessions=[{} for _ in range(n)]
        s.phase=g.phase='ACTIVE';s.lifecycle=SimpleNamespace(current=SimpleNamespace(retired=False))
        s.warm.banks=[dict(index=i,module=1000+i,load_accepted=True,warm_load_retired=True,refresh_load_retired=True) for i in range(n)]
        s.warm.current=s.warm.banks[-1]
        def hand(kind):
            h=kind();h.currentGeneration=n;h.certificateCount=n-1
            for i in range(n):h.banks[i]=1000+i;h.completed[i]=1
            return h
        s.warm.hand=hand
        # Same reader projection, with independent current native epoch/attachment.
        sampler=native.ContextSampler(self.w.reader,pid=self.w.reader.pid,birth=self.w.birth,epoch=self.w.epoch,
            attachment_id=self.w.attachment,current_binding=lambda:(self.w.epoch,self.w.attachment),node=dict(year=203,month=8,day=day),
            viewer=2,players={12:dict(ruler=666,district=11),2:dict(ruler=952,district=2)},read_birth=lambda:self.w.birth)
        self.scope=dict(schema='san14.replica-scope.v1',room_id='1'*32,binding_epoch='2'*32,timeline_epoch=format(30+n,'032x'),
            profile=dict(protocol='san14.room.v1',game_sha256=old.old.reward.SUPPORTED_SHA256,adapter_contract='research-no-native-room-adapter.v1',checkpoint_sha256='c'*64,rules_sha256='d'*64),
            bindings=dict(A=dict(force_id=12,main_district_id=11),B=dict(force_id=2,main_district_id=2)),state_contract=old.old.CONTRACT,
            initial_state_sha256=journal.digest(sampler.capture()[1]))
        s.scope=deepcopy(self.scope);self.cut_state='ACTIVE'
        self.discovery=dict(ok=True,schema=sessionmod.DISCOVERY_SCHEMA,ready=True,native_gameplay_enabled=False,context=dict(scope=deepcopy(self.scope),
            checkpoint_period=g.period,checkpoint_epoch=g.epoch,attachments=deepcopy(g.attachments),
            profile_sha256=hashlib.sha256(bytes(p)).hexdigest(),node=dict(year=203,month=8,day=day,phase='PLANNING_BOUNDARY')))
    def install_input(self):
        import player_input_rebind_port as inputs
        from player_input_rebind_port_test import Body
        body=Body();v=body.s;v.pid=self.w.reader.pid;v.birth=self.w.birth
        v.binding.room[:]=bytes.fromhex(self.scope['room_id']);v.binding.seat=1
        v.binding.epoch[:]=bytes.fromhex(self.g.epoch);v.binding.attachment[:]=bytes.fromhex(self.g.attachments['B'])
        v.binding.period=self.g.period
        state=native.SharedCallState(threading.RLock(),lambda exc:self.held.append('input unknown callback'))
        transport=inputs.Transport.__new__(inputs.Transport);transport.state=state;transport._perform=body.call
        lease=inputs.InputLease(transport,nonce=body.nonce,binding=v.binding,pid=v.pid,birth=v.birth,
            window=v.window,records=self.folder/'preinstalled-input',wait_seconds=.05)
        self.s._chain_input_owner=lease;self.s._chain_input_transitions={1:dict(phase='REBOUND_HELD')}
        return lease,body
    def observed(self,s,g):
        self.test.assertIs(s,self.s);self.test.assertIs(g,self.g)
        return dict(node=self.discovery['context']['node'])
    def load(self,api,address,payload,*args):
        self.test.assertEqual(address,123)
        path=Path(payload.decode('utf-16le').rstrip('\0'));self.module_rows.append((0x90000000+len(self.module_rows)*0x10000,str(path)))
        return 0,b''
    def transport(self,api,**kw):
        sch=Scheduler(self.w);self.schedulers.append(sch);self.test.addCleanup(sch.close)
        return SimpleNamespace(call=lambda name,raw:kw['call_state'].invoke(lambda:sch.call(name,raw)),
                               module=kw['module'],dll=kw['dll'],scheduler=sch,state=kw['call_state'])
    def request(self,q):
        action=q['action']
        if action=='reward_scope':return dict(ok=True,scope=deepcopy(self.scope),attachment=self.g.attachments['B'])
        if action=='reward_report':return dict(ok=True)
        if action=='reward_next':
            result=self.queue;self.queue=None;return dict(ok=True,intent=result)
        if action=='reward_cut_status':return dict(ok=True,state=self.cut_state,receipt=dict(checkpoint_cut_installed=True))
        if action=='period_ready':self.ready_calls+=1;return dict(ok=True)
        if action=='reward_cut_prepare':return dict(ok=True)
        raise AssertionError(action)
    def open(self,suffix=''):
        return sessionmod.RewardSession.open(session=self.s,guest=self.g,profile=self.profile,discovery=self.discovery,
            build='OWNED BUILD DOUBLE',report_key_path=self.report_key,cut_key_path=self.cut_key,records=self.folder/f'window{self.n}{suffix}')
    def reward(self,r):
        cmd=r.replica.command(2,2,[101]);self.queue=journal.make_intent(self.scope,1,'B','7'*32,cmd,r.replica.journal.status()['state_sha256'])
        return r.poll()
    def retire(self,r):
        r.finish_input();r.cut.attest_attempted=True # Paired cut authority is an explicit protocol double.
        self.cut_state='RETIRED_SHARED_CUT';r.poll();r.assert_released()

class Tests(unittest.TestCase):
    def test_two_windows_actual_factory_journals_and_second_reward(self):
        h=Harness(self);a=h.open();self.assertIs(type(a.replica.port),CheckedPort)
        h.reward(a);h.retire(a);old_context=bytes(a.native.context);old_db=a.replica.journal
        h.move();b=h.open();h.reward(b);h.retire(b)
        self.assertEqual(h.w.calls,2);self.assertIsNot(a.native,b.native);self.assertIs(a.native.state,b.native.state)
        self.assertNotEqual(old_context,bytes(b.native.context));self.assertIsNot(old_db,b.replica.journal)
        self.assertNotEqual(a.native.transport.dll,b.native.transport.dll)
        self.assertEqual([n.context.period for n in (a.native,b.native)],[2,3])
        self.assertEqual([n.context.native.ownerGeneration for n in (a.native,b.native)],[1,2])
        self.assertEqual(set(h.s._b_chain_reward_native),{1,2});self.assertEqual(set(h.s._b_chain_reward_windows),{1,2})
        self.assertEqual([x.calls.count('BRewardConfigure') for x in h.schedulers],[1,1])
        self.assertEqual([x.calls.count('BRewardSubmit') for x in h.schedulers],[1,1])
        self.assertTrue(a.native.closed and b.native.closed)
    def test_stale_window_and_context_cannot_execute_after_second_load(self):
        h=Harness(self);a=h.open();h.reward(a);h.retire(a);h.move();b=h.open()
        with self.assertRaises(Exception):a.native.identity()
        with self.assertRaises(Exception):a.submit(2,[101])
        self.assertEqual(sum(x.calls.count('BRewardSubmit') for x in h.schedulers),1)
        self.assertEqual(h.s.phase,'TERMINAL')
    def test_old_discovery_rejected_before_second_native_owner(self):
        h=Harness(self);a=h.open();discovery=deepcopy(h.discovery);h.reward(a);h.retire(a);h.move();h.discovery=discovery
        with self.assertRaises(Exception):h.open()
        self.assertEqual(len(h.schedulers),1)
    def test_unretired_window_cannot_open_successor(self):
        h=Harness(self);a=h.open();h.reward(a);h.move()
        with self.assertRaisesRegex(Exception,'did not release'):h.open()
        self.assertEqual(len(h.schedulers),1)
    def test_retired_receipt_not_enough_when_old_native_slot_drifted(self):
        h=Harness(self);a=h.open();h.reward(a);h.retire(a);h.move();h.schedulers[0].fault='restore-drift'
        with self.assertRaisesRegex(Exception,'restoration or drain'):h.open()
        self.assertEqual(len(h.schedulers),1);self.assertEqual(h.s.phase,'TERMINAL')
    def test_second_unknown_submit_keeps_claims_and_no_retry(self):
        h=Harness(self);a=h.open();h.reward(a);h.retire(a);h.move();b=h.open();h.schedulers[1].fault='unknown'
        with self.assertRaises(Exception):h.reward(b)
        self.assertTrue(h.schedulers[1].done.wait(2));self.assertTrue(h.s.warm.calls.uncertain)
        with self.assertRaises(Exception):b.poll()
        with self.assertRaises(Exception):h.open('-retry')
        self.assertEqual(h.schedulers[1].calls.count('BRewardSubmit'),1)
        self.assertEqual(len(h.schedulers),2);self.assertEqual(set(h.s._b_chain_reward_native),{1,2})
    def test_unknown_restore_cannot_release_or_open_next(self):
        h=Harness(self);a=h.open();h.reward(a);h.schedulers[0].fault='restore-unknown'
        with self.assertRaises(Exception):h.retire(a)
        self.assertEqual(h.s.phase,'TERMINAL');self.assertIsNone(a.receipt)
        with self.assertRaises(Exception):a.poll()
        self.assertEqual(h.schedulers[0].calls.count('BRewardRestore'),1)
    def test_preinstalled_input_gate_reused_and_unknown_marks_whole_chain(self):
        h=Harness(self);lease,body=h.install_input();r=h.open()
        self.assertIs(r.native.state,lease.state);self.assertIs(r.native.transport.state,lease.state)
        h.schedulers[0].fault='unknown'
        with self.assertRaises(Exception):h.reward(r)
        self.assertTrue(lease.state.unknown);self.assertTrue(h.s.warm.calls.uncertain)
        self.assertEqual(h.s.phase,'TERMINAL');before=list(body.calls)
        with self.assertRaises(Exception):h.open('-retry')
        self.assertEqual(before,body.calls)
    def test_preinstalled_input_wrong_gate_refused_before_native_load(self):
        h=Harness(self);lease,_=h.install_input()
        lease.state=native.SharedCallState(threading.RLock(),lambda exc:None)
        with self.assertRaisesRegex(Exception,'shared input'):h.open()
        self.assertEqual(h.module_rows,[]);self.assertEqual(h.s.phase,'TERMINAL')
    def test_preinstalled_input_foreign_epoch_and_open_policy_rejected(self):
        for mode in ('epoch','open'):
            with self.subTest(mode=mode):
                # Separate fixture folders and claims for each rejection.
                original=self._testMethodName;self._testMethodName=original+'-'+mode
                h=Harness(self);self._testMethodName=original;lease,body=h.install_input()
                if mode=='epoch':lease.binding.epoch[0]^=1
                else:body.s.phase=0;body.s.localCommandPolicyOpen=body.s.remoteExecutionPolicyOpen=1;body.s.held=0
                with self.assertRaises(Exception):h.open()
                self.assertEqual(h.module_rows,[])
                for patcher in reversed(h.patches):patcher.stop()
    def test_preinstalled_input_without_window_never_sends_ready(self):
        h=Harness(self);h.install_input();r=h.open();h.reward(r)
        with self.assertRaisesRegex(Exception,'input owner/window'):h.retire(r)
        self.assertEqual(h.ready_calls,0);self.assertEqual(h.s.phase,'TERMINAL')
    def test_registered_window_missing_input_owner_never_sends_ready(self):
        from b_chain_reward_input import Window
        h=Harness(self);lease,_=h.install_input();r=h.open()
        Window.open(r,lease,records=h.folder/'real-window');h.reward(r)
        del h.s._chain_input_owner
        with self.assertRaises(Exception):h.retire(r)
        self.assertEqual(h.ready_calls,0);self.assertEqual(h.s.phase,'TERMINAL')
    def test_window_not_ready_never_sends_ready(self):
        from b_chain_reward_input import Window
        h=Harness(self);lease,_=h.install_input();r=h.open()
        Window.open(r,lease,records=h.folder/'real-window');h.reward(r)
        with self.assertRaises(Exception):h.retire(r) # Direct finish does not put Window into READY.
        self.assertEqual(h.ready_calls,0);self.assertEqual(h.s.phase,'TERMINAL')
    def test_load_ack_failure_never_sends_ready_or_enables_load(self):
        from b_chain_reward_input import Window
        h=Harness(self);lease,_=h.install_input();r=h.open()
        w=Window.open(r,lease,records=h.folder/'real-window');h.reward(r);w.finish_input()
        r.cut.attest_attempted=True;h.cut_state='RETIRED_SHARED_CUT'
        with patch.object(lease,'request_phase',side_effect=RuntimeError('owned missing LOAD acknowledgement')):
            with self.assertRaisesRegex(Exception,'acknowledgement'):r.poll()
        self.assertEqual(h.ready_calls,0);self.assertEqual(h.s.phase,'TERMINAL')
    def test_transport_evidence_error_becomes_unknown(self):
        with patch.object(native.common,'remote_call',side_effect=OSError('evidence failed')):
            with self.assertRaises(native.RemoteCallUnknown):native.retained_call(None)
    def test_no_third_reward_window(self):
        h=Harness(self);h.move();h.move()
        with self.assertRaises(Exception):h.open()
        self.assertFalse(h.schedulers)

if __name__=='__main__':
    OUTPUT=PRIVATE/'b_chain_reward_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    files=['b_chain_reward_native_port.py','b_chain_reward_session.py','b_chain_reward_flow.py','b_chain_reward_test.py','b_chain_reward_input.py',
        'a_runtime_reward_port.py','reward_observed_context.py','reward_rebind_context.py','b_chain_input_transition.py',
        'b_remote_chain_session.py','b_observed_chain_completion.py','b_warm_chain_coordinator_contract.py',
        'b_warm_profile_contract.py','b_warm_start_support.py','b_warm_adapter_key.py','b_warm_received_apply.py',
        'reward_checkpoint_observer.py','reward_observed_fixture.py','b_reward_native_port_test.py','a_runtime_reward_port_test.py',
        'player_input_rebind_port.py','player_input_rebind_port_test.py']
    before={str(HERE/n):hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in files}
    before.update({str(ROOT/'outputs/san14-link'/n):hashlib.sha256((ROOT/'outputs/san14-link'/n).read_bytes()).hexdigest()
                   for n in ('execution_journal.py','reward_room_flow.py','game_reader.py','authority_reward.py','authoritative_sync.py')})
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');stable=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
    result=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,sources=before,inputs_unchanged=stable,
        game_access=False,steam_access=False,native_exports_executed=False,actual_TLS=False,actual_SQLite_reward_projection=True,
        production_python_factory_executed=True,environment_native_and_authority_doubles=True)
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(stream.getvalue());print(OUTPUT/'result.json')
    raise SystemExit(result['result']!='PASS')
