"""Actual entry lifecycle + TLS/Room/Session, explicit native/PE/RAM doubles.
No game/Steam access. Own files exercise real backup and result inventory.
"""
from contextlib import ExitStack
from datetime import datetime
import hashlib,io,json,sys,unittest,secrets
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import a_reward_runtime_entry as start
import a_reward_runtime_mount as mounting
import a_runtime_reward_port as reward_port
from a_runtime_reward_port_test import OwnedScheduler
from reward_checkpoint_fixture import World as UnifiedWorld
from reward_room_flow import Replica, envelope
from reward_observed_flow import GuestConsumer
from observed_room_service import HostService
import a_observed_start as frozen_entry
from b_warm_rules_factory import RulesBuild
from human_rules_activation_room import rules
import a_observed_start_call as safe_call
import ctypes as C
import b_observed_completion_test as joint
from b_observed_completion_test import *
import checkpoint_complete_live_capture as capture_module
import checkpoint_push_start
import game_reader
import run_autonomous_pilot
import a_save_ipc_client
import pefile

OUTPUT=None;ROWS=[];PRIVATE_INPUTS={}

class Cases(joint.Cases):
    def setUp(self):
        # The predecessor fixture ordinarily enrolls its own A adapter. Omit
        # that setup only: the entry under test performs the real enrollment.
        with patch.object(ObservedRoom,'enroll_observed_adapter'):
            super().setUp()
        self.a_world=UnifiedWorld(12);self.b_world=UnifiedWorld(2)
        self._unified_host()
        self.a_world.copy_tables_to_bootstrap_double(self.guest)
        # Retain the predecessor's actual TLS/Room. Only HostService constructor
        # setup is an explicit shell; its monitor and Ready method run unchanged.
        self.service=HostService.__new__(HostService)
        self.service.room,self.service.coordinator,self.service.control=self.room,self.c,self.a
        self.service.servers=self.servers;self.service.failure=None;self.service.guest_finished=None
        self.service.guest_disconnected=threading.Event();self.service._stop=threading.Event()
        self.service._state_lock=threading.RLock();self.service._host_ready=self.service._seal_started=False
        self.monitor=threading.Thread(target=self.service._monitor);self.monitor.start()
        self.mount=mounting.RuntimeMount(self.service,reward_key=secrets.token_bytes(32),guest_cut_key=secrets.token_bytes(32),
            records=self.folder/'mount',wait_seconds=2)
        self.entry=start.RoomEntry(self.room,self.c,self.key,mount=self.mount,no_new_commands=True)
        self.guest_cut=None;self.reward_submitted=False
        self.scheduler=OwnedScheduler(self.a_world)
        self.calls=[];self.published=[];self.events=[];self.fault=None
        f=self.host_fixture
        self.raw=wire.envelope(wire.Prepare,'Prepare',f.nonce)
        self.raw.pid,self.raw.birth,self.raw.base=f.reader.pid,f.birth,f.reader.memory.base
        self.raw.root,self.raw.world,self.raw.cache=f.reader.root,f.reader.world,f.cache
        self.raw.epoch,self.raw.period,self.raw.nativeRoomEpoch=123,1,71
        self.raw.year,self.raw.month,self.raw.day,self.raw.force,self.raw.ruler=203,8,11,12,666
        self.raw.states[:]=[a for _,a in f.reader.state_objects()]
        self.raw.native.attempt[:]=b'x'*16;self.raw.native.attachment[:]=b'y'*16;self.raw.native.ownerGeneration=1
        self.source_dir=self.folder/'a-saves';self.source_dir.mkdir()
        self.source=self.source_dir/'svdexSC34.s14';self.source.write_bytes(b'owned initial save')
        self.bundle=self.folder/'bundle';self.bundle.mkdir()
        for name in ('a_save_local_runtime.dll','checkpoint_planning_hold.dll','publisher.exe'):
            (self.bundle/name).write_bytes(('explicit owned binary double '+name).encode())
        (self.bundle/'result.json').write_text('{}')
        self.args=SimpleNamespace(build_run=self.bundle,publisher_build=self.bundle,repeat_abi_run=self.bundle,
            launcher_test_run=self.bundle,entry_test_run=self.bundle,wait_seconds=10)
        self.captured=dict(planning={'fixture':True},storage={'fixture':True})
        self.received_count=0;self.commands=[];self.polls=0;self.stopped=False;self.final=None

    def tearDown(self):
        self.scheduler.close();self.service._stop.set();self.monitor.join(3)
        self.assertFalse(self.monitor.is_alive())
        super().tearDown()

    def _unified_host(self):
        f=self.host_fixture;old=f.reader;w=self.a_world;m=w.memory
        # Explicit RAM environment, same actual GameReader for mount/reward and
        # native boundary/world observations; PE/RTTI identities remain doubles.
        for address in (f.cache,f.toolbar,f.panel,f.keyboard,f.report):
            raw=old.memory.spans[address];m.reserve(address,len(raw));m.put(address,raw)
        m.reserve(f.stack,40);m.pack(f.stack,'<5Q',*w.states)
        m.pack(w.states[4]+0x478,'<Q',f.toolbar);m.pack(w.states[2]+0x480,'<Q',f.panel)
        m.pack(m.base+0x2025318,'<Q',f.cache);m.pack(m.base+0x1FCA0A0,'<Q',f.keyboard)
        m.pack(m.base+0x19E7310+0x10,'<QQQ',5,16,f.stack)
        m.pack(m.base+0x1FC98B0,'<QQ',f.report,0)
        m.pack(w.world+0x165A,'<H',43);m.pack(m.base+0x18EB8B0,'<I',123)
        for p in f.plans.slots:m.pack(p.address,'<Q',p.hook)
        for p in f.plans.inlines:m.put(p.address,bytes(p.after)[:p.size])
        f.reader=w.reader;f.birth=w.birth;f.reader.root=w.root;f.reader.world=w.world
        f.plans.pid=w.reader.pid;f.plans.birth=w.birth
        self.host=f.reader
        def rebuild():
            f.runtime.saveStatus=5;f.runtime.saveGeneration=f.runtime.mailboxCount=1;f.runtime.mailboxStates[0]=5
            f.runtime.binds=f.runtime.queues=f.runtime.workerJoined=f.runtime.fileVerified=1
            f.runtime.phaseMask=31;f.runtime.originalReturned=27
            m.pack(w.world+0x34,'<HBB',203,8,21);f.node={**f.node,'day':21}
            for i in (3,4):
                a=w.obj(world.PLAN[i],0x800);m.put(a,m.read(w.states[i],0x800));w.states[i]=a
            m.pack(f.stack,'<5Q',*w.states)
        f.complete_and_rebuild=rebuild

    def progress_reward(self):
        if self.mount.phase not in ('ACTIVE','RETIRED'):return
        if self.guest_cut is None:
            self.b_world.attachment=self.c.attachments['B'];port=self.b_world.port()
            replica=Replica(self.folder/'mounted-B.sqlite',self.mount.flow.scope,'B',port)
            consumer=GuestConsumer(self.b,replica,self.mount.reward_key);consumer.report()
            self.guest_cut=mounting.GuestCutConsumer(consumer,self.mount.profile,
                cut_key=self.mount.cut_key,checkpoint_epoch=self.c.epoch)
            self.assertTrue(self.a.request(envelope(self.mount.flow.scope,'reward_submit',request_id='7'*32,
                district_id=11,officer_ids=[97]))['ok'])
            self.assertTrue(self.a.request(dict(action='reward_cut_prepare',epoch=self.c.epoch))['ok'])
            self.guest_cut.finish_input();self.reward_submitted=True
        self.guest_cut.poll()
        if self.mount.phase=='RETIRED' and not self.guest_cut.ready_attempted:self.guest_cut.ready_after_cut()

    def run_entry(self):
        owner=self;f=self.host_fixture;modules=[];exports={name:0x100+v*64 for name,v in repeat.OPS.items()}
        exports.update({name:0x100+v*64 for name,v in dict(RewardConfigure=11,RewardSubmit=12,RewardSnapshot=13,OpenPlanning=14,PlanningSnapshot=15).items()})
        f.reader.memory.reserve(f.plans.module,0x10000)
        for address in exports.values():f.reader.memory.put(f.plans.module+address,b'\x90'*32)
        class API:
            def __init__(self,reader):
                owner.calls.append('open-api');self.reader=reader;self.handle=99
                class Fn:
                    def __init__(self,fn):self.fn=fn
                    def __call__(self,*a):return self.fn(*a)
                def times(h,*a):a[0]._obj.value=f.birth;return 1
                self.k=SimpleNamespace(GetProcessId=Fn(lambda h:reader.pid),GetProcessTimes=Fn(times))
            def modules(self):return modules[:]
            def load_library_address(self):return 0x111
            def close(self):owner.calls.append('close-api')
        class PE:
            def __init__(self,path):self.DIRECTORY_ENTRY_EXPORT=SimpleNamespace(symbols=[SimpleNamespace(name=('ASaveRuntime'+n).encode(),address=a,forwarder=None) for n,a in exports.items()])
            def close(self):pass
            def get_data(self,rva,size):return b'\x90'*size
        class Channel:
            def __init__(self,*a,**k):self.reservation=None;owner.calls.append('channel-open')
            def submit(self,reservation):self.reservation=reservation;owner.calls.append('submit-'+str(reservation.generation))
            def wait_artifact(self,generation,timeout):
                owner.complete_host(generation)
                artifact=model_artifact(self.reservation.request,generation,data=('owned Save '+str(generation)).encode()*2100)
                (owner.source_dir/self.reservation.request['filename']).write_bytes(artifact.data)
                return artifact
            def snapshot(self):owner.progress_reward();return None
            def stop(self):owner.calls.append('channel-stop')
            def close(self):owner.calls.append('channel-close')
        def remote(api,address,raw,run,label):
            if address==0x111:
                path=Path(raw.decode('utf-16le').rstrip('\0'));base=f.plans.module if path.name=='a_save_local_runtime.dll' else 0x900000000
                modules.append((base,path));owner.calls.append('load-'+path.name);return 0,raw
            op=next(n for n,a in exports.items() if address==f.plans.module+a);owner.calls.append(op)
            if owner.fault=='tls-unknown' and op=='Snapshot' and owner.c.phase=='RECONCILING':
                raise start.RemoteCallUnknown('owned unresolved TLS Snapshot',{'label':label})
            if op.startswith('Reward'):
                if owner.fault=='reward-unknown' and op=='RewardSubmit':
                    raise start.RemoteCallUnknown('owned reward Submit uncertain',{'may_have_started':True})
                result=owner.scheduler.call('ASaveRuntime'+op,raw)
                if op=='RewardConfigure':
                    request=reward_port.Configure.from_buffer_copy(raw);s=reward_port.Snapshot()
                    s.header=wire.Header(wire.MAGIC,1,C.sizeof(s),13,0);s.nonce[:]=request.nonce;s.context=request.context
                    s.configured=1;s.state=1;s.hostThread=77;owner.scheduler.report=s
                return result
            if op=='OpenPlanning':
                answer=mounting.Open.from_buffer_copy(raw);f.runtime.ready=0
            elif op=='PlanningSnapshot':
                answer=mounting.PlanningSnapshot.from_buffer_copy(raw)
                answer.state=2;answer.opened=answer.receiptMatched=1;answer.hostThread=77
            elif op=='Plans':answer=f.plans
            elif op=='Snapshot':
                answer=f.snapshot()
                if owner.stopped:answer.stopped=answer.ownerStopped=answer.restoreReady=1;answer.ready=0
            elif op=='RequestNext':
                answer=repeat.Next.from_buffer_copy(raw);owner.commands.append(answer);f.runtime.ready=1
            elif op=='RepeatSnapshot':
                q=repeat.envelope(repeat.Snapshot,op,f.nonce)
                if owner.commands:
                    q.request=owner.commands[0].request;q.requested=q.hostThread=q.previousArtifactMatched=q.retiredSerial=q.retiredCount=1
                    owner.polls+=1;q.state=3 if owner.polls<3 or owner.fault=='running-stop' else 4
                    q.activeGeneration=1 if q.state==3 else 2;q.drainPending=int(q.state==3);q.nativeDateMatched=int(q.state==4)
                    if q.state==4 and f.node['day']==11:f.complete_and_rebuild()
                if owner.stopped:q.stopped=1
                answer=q
            elif op=='ServerStatus':
                answer=wire.envelope(wire.ServerStatus,op,f.nonce);answer.started=answer.threadExited=1
            else:
                typ={'Prepare':wire.Prepare,'StartServer':wire.StartServer}.get(op,wire.Command)
                answer=typ.from_buffer_copy(raw)
                if op=='Stop':owner.stopped=True
            blob=bytes(answer);(run/(label+'-response.bin')).write_bytes(blob)
            return 0,blob
        class Protection:
            def __init__(self,entry,*a,**kw):self.entry=entry;self.installed_once=False;self.restore_verified=False;self.phase='NEW'
            def install(self):
                owner.calls.append('rules-install');self.phase='PREPARING'
                if owner.fault=='rules-unknown':raise start.RemoteCallUnknown('owned rules Prepare unknown',{'rules':True})
                self.installed_once=True;self.phase='INSTALLED'
            def verify(self):
                if self.phase!='INSTALLED':raise ValueError('owned rules not installed')
            def restore(self):
                owner.calls.append('rules-restore')
                if self.entry.phase=='HELD' or owner.fault=='rules-restore-failed':
                    self.phase='HELD';raise ValueError('owned retained rules refuse unsafe restore')
                self.restore_verified=True;self.phase='RESTORED'
            def status(self):return dict(phase=self.phase,installed_once=self.installed_once,restore_verified=self.restore_verified,
                retained_or_unknown=self.phase not in ('NEW','RESTORED'))
        def publisher(exe,operation,*a):
            owner.published.append(operation);return {'status':'INSTALLED' if operation=='install' else 'RESTORED'}
        def event(kind,info):
            owner.events.append(kind)
            if kind.startswith('await-b-'):
                generation=int(kind[-1]);r,q,p=owner.received(generation,owner.room.artifacts)
                owner.adapter.apply(r,q,p);owner.received_count+=1
            elif kind=='await-room-turn':
                for client in (owner.a,owner.b):owner.assertTrue(client.request(dict(action='period_ready',epoch=owner.c.epoch,ready=True))['ok'])
                permit=owner.c.seal_inputs();owner.c.begin_simulation(permit)
            elif kind=='running-await-human' and owner.fault=='running-stop':raise ValueError('owned human wait stopped')
        binaries={name:start.sha(self.bundle/name) for name in ('a_save_local_runtime.dll','checkpoint_planning_hold.dll')}
        f.reader.close=lambda:owner.calls.append('reader-close')
        with ExitStack() as stack:
            replacements=[(start,'ProtectedRulesOwner',Protection),(start,'PRIVATE',self.folder/'private'),(start,'verify_entry_tests',lambda _:None),
                (start,'verify_launcher_tests',lambda _:None),
                (start,'approved_planning_runtime',lambda args,baseline:(baseline,{'production_dll':str(self.bundle/'a_save_local_runtime.dll')})),
                (reward_port,'module_approval',lambda *a:{'owned_environment_double':True}),
                (reward_port,'readable',lambda *a,**k:None),(reward_port,'process_birth',lambda _:f.birth),
                (reward_port,'remote_call',remote),
                (start,'verify_native_build',lambda _:({'production':{'binaries':binaries}},self.bundle,{'binaries':{'publisher.exe':start.sha(self.bundle/'publisher.exe')}})),
                (wire,'prepare_from_capture',lambda *a:wire.Prepare.from_buffer_copy(bytes(self.raw))),
                (capture_module,'SOURCE',self.source),(capture_module,'SOURCE_SHA',start.sha(self.source)),
                (game_reader,'GameReader',lambda **k:f.reader),(run_autonomous_pilot,'ProcessAPI',API),
                (checkpoint_push_start,'process_birth',lambda _:f.birth),(pefile,'PE',PE),
                (start,'capture',lambda _:(self.folder/'capture.json',self.captured)),(start,'remote_call',remote),
                (start,'publish',publisher),(a_save_ipc_client,'ASaveClient',Channel),
                (start.failure_diagnostic,'export_layout',lambda *a:None),
                (start.failure_diagnostic,'observe',lambda *a:{'status':'OWNED_DOUBLE'}),
                (start,'post_turn_check',lambda *a:{'result':'OWNED_DOUBLE'})]
            for obj,name,value in replacements:stack.enter_context(patch.object(obj,name,value))
            build=RulesBuild(PRIVATE/'human_rules_activation_v2_runs/20261008-000431-509932/production.dll',PRIVATE/'human_rules_activation_publish_v2_runs/20261008-000527-938626/inputs/publisher-production.exe')
            PRIVATE_INPUTS[str(build.stage)]=build.stage_sha;PRIVATE_INPUTS[str(build.publisher)]=build.publisher_sha
            code=start.execute(self.args,self.folder/'capture.json',self.captured,entry=self.entry,on_event=event,rules_build=build,settings=rules(1,0),reward_flow=self.mount)
        resultfile=next((self.folder/'private/a_reward_runtime_entry_runs').glob('*/result.json'))
        self.final=json.loads(resultfile.read_text())
        ROWS.append(dict(case=self._testMethodName,code=code,result=self.final,events=self.events,calls=self.calls,published=self.published,
            actual_mount_cut=(type(self.mount) is mounting.RuntimeMount and self.mount.gate is not None and
                              self.mount.gate.receipt is not None and self.mount.gate.receipt['cut']['sequence']==1),
            shared_call_unknown=(self.mount.state.unknown if hasattr(self.mount,'state') else None),
            native_business_double_calls=self.a_world.calls))
        return code

    def test_entry_actual_tls_two_periods_and_original_cleanup(self):
        self.assertEqual(self.run_entry(),0)
        self.assertEqual(self.final['result'],'PASS_PROTECTED_ROOM_TWO_SAVES')
        self.assertEqual(self.received_count,2);self.assertEqual(self.published,['install','restore'])
        self.assertTrue(self.final['save_comparison']['originals_unchanged'])
        self.assertLess(self.calls.index('ArmPublishedSources'),self.calls.index('rules-install'))
        self.assertLess(self.calls.index('rules-install'),self.calls.index('submit-1'))
        self.assertLess(self.calls.index('submit-2'),self.calls.index('rules-restore'))
        self.assertLess(self.calls.index('rules-restore'),self.calls.index('Stop'))
        self.assertTrue(self.entry.status()['protection']['restore_verified'])
        self.assertEqual(self.calls.count('Prepare'),1);self.assertEqual(self.calls.count('RequestNext'),1)
        self.assertLess(self.calls.index('Prepare'),self.calls.index('ArmOwner'))
        self.assertEqual(self.entry.phase,'TWO_COMPLETIONS_RETAINED')
        with self.assertRaises(RuntimeError):self.entry.prepare(self.raw)

    def test_tls_native_unknown_retains_and_skips_stop_restore(self):
        self.fault='tls-unknown';self.assertEqual(self.run_entry(),1)
        self.assertTrue(self.final['uncertain']);self.assertNotIn('Stop',self.calls)
        self.assertEqual(self.published,['install']);self.assertEqual(self.entry.phase,'HELD')
        self.assertEqual(self.calls.count('submit-1'),1);self.assertNotIn('submit-2',self.calls)
        self.assertFalse(self.warm.events)

    def test_running_stop_does_not_fake_restore(self):
        self.fault='running-stop';self.assertEqual(self.run_entry(),1)
        self.assertNotIn('Stop',self.calls);self.assertEqual(self.published,['install'])
        self.assertFalse(self.final['cleanup_verified']);self.assertTrue(self.entry.status()['protection']['retained_or_unknown'])
        self.assertEqual(self.calls.count('submit-1'),1);self.assertNotIn('submit-2',self.calls)

    def test_rules_unknown_retains_before_any_save(self):
        self.fault='rules-unknown';self.assertEqual(self.run_entry(),1)
        self.assertNotIn('submit-1',self.calls);self.assertNotIn('Stop',self.calls);self.assertNotIn('rules-restore',self.calls)
        self.assertEqual(self.published,['install']);self.assertTrue(self.final['uncertain'])

    def test_rules_restore_refusal_does_not_restore_seven(self):
        self.fault='rules-restore-failed';self.assertEqual(self.run_entry(),1)
        self.assertEqual(self.calls.count('submit-2'),1);self.assertNotIn('Stop',self.calls)
        self.assertEqual(self.published,['install']);self.assertTrue(self.entry.status()['protection']['retained_or_unknown'])


    def test_reward_unknown_latches_shared_native_owner_and_skips_cleanup(self):
        self.fault='reward-unknown';self.assertEqual(self.run_entry(),1)
        self.assertTrue(self.final['uncertain']);self.assertIsNotNone(self.mount.state.unknown)
        self.assertEqual(self.calls.count('RewardSubmit'),1)
        self.assertNotIn('RequestNext',self.calls);self.assertNotIn('submit-2',self.calls)
        self.assertNotIn('Stop',self.calls);self.assertNotIn('rules-restore',self.calls)
        self.assertEqual(self.published,['install'])
        self.assertEqual(self.mount.flow.host.journal.status()['unknown_sequences'],[1])
        self.assertFalse(self.final['cleanup_verified'])

    def test_other_mount_rejected_before_entry_build_or_native_access(self):
        other=mounting.RuntimeMount(self.service,reward_key=secrets.token_bytes(32),guest_cut_key=secrets.token_bytes(32),
            records=self.folder/'other-mount')
        with self.assertRaisesRegex(RuntimeError,'Exact retained room entry'):
            start.execute(self.args,self.folder/'capture.json',self.captured,entry=self.entry,on_event=lambda *a:None,
                rules_build=None,settings=rules(1,0),reward_flow=other)
        self.assertEqual(self.calls,[])
        ROWS.append(dict(case=self._testMethodName,foreign_mount_refused_before_native=True))

    def test_false_condition_or_reused_room_rejected_before_prepare(self):
        with self.assertRaises(RuntimeError):start.RoomEntry(self.room,self.c,self.key,mount=self.mount,no_new_commands=False)
        self.entry.prepare(self.raw)
        with self.assertRaises(RuntimeError):self.entry.prepare(self.raw)
        self.assertEqual(self.calls,[])

    def test_unresolved_remote_call_keeps_unknown_when_final_log_fails(self):
        calls=[]
        class Kernel:
            def CheckRemoteDebuggerPresent(self,h,p):p._obj.value=False;return 1
            def VirtualAllocEx(self,*a):return 0x12340000
            def WriteProcessMemory(self,h,a,v,n,p):p._obj.value=n;return 1
            def CreateRemoteThread(self,*a):a[-1]._obj.value=77;return 0x8888
            def WaitForSingleObject(self,*a):return 258
            def CloseHandle(self,*a):calls.append('close-thread');return 1
            def VirtualFreeEx(self,*a):calls.append('free');return 1
        api=SimpleNamespace(k=Kernel(),handle=99)
        original=safe_call.save_new
        def save(path,value):
            if path.name.endswith('-result.json'):raise OSError('owned disk full after timeout')
            return original(path,value)
        with patch.object(safe_call,'save_new',side_effect=save):
            with self.assertRaises(start.RemoteCallUnknown) as caught:
                safe_call.remote_call(api,0x7890,b'owned',self.folder,'unknown-log',timeout_ms=1)
        r=caught.exception.record
        self.assertTrue(r['may_have_started']);self.assertFalse(r['completed']);self.assertTrue(r['retained_buffer'])
        self.assertEqual(r['buffer'],0x12340000);self.assertIn('disk full',r['result_log_error'])
        self.assertEqual(calls,['close-thread'])
        ROWS.append(dict(case=self._testMethodName,record=r,no_buffer_release=True))

    def test_observation_callbacks_drained_before_local_cleanup(self):
        from b_warm_world_test import configuration
        p,_=configuration();f=self.host_fixture;prep=self.entry.prepare(self.raw)
        self.entry.bind_runtime(prep,f.reader,f.plans,read_birth=lambda:f.birth,runtime_snapshot=f.snapshot)
        self.entry.protection=SimpleNamespace(verify=lambda:None) # callback-drain fixture only
        self.entry.phase='RUNNING';entered=threading.Event();release=threading.Event();closed=threading.Event();errors=[]
        def blocking():entered.set();release.wait(3);return f.snapshot()
        self.entry.provider.runtime_snapshot=blocking
        def observing():
            try:
                with self.room.lock,self.c.lock:self.entry._boundary(p,'begin')
            except BaseException as exc:errors.append(repr(exc))
        worker=threading.Thread(target=observing);worker.start();self.assertTrue(entered.wait(2))
        closer=threading.Thread(target=lambda:(self.entry.close_observation(),closed.set()));closer.start()
        self.assertFalse(closed.wait(.05));release.set();worker.join(3);closer.join(3)
        self.assertFalse(worker.is_alive() or closer.is_alive());self.assertTrue(closed.is_set());self.assertEqual(errors,[])
        with self.assertRaises(RuntimeError):self.entry._boundary(p,'complete')
        ROWS.append(dict(case=self._testMethodName,callback_drained=True,subsequent_callback_rejected=True))



NAMES=['test_entry_actual_tls_two_periods_and_original_cleanup','test_tls_native_unknown_retains_and_skips_stop_restore',
       'test_running_stop_does_not_fake_restore','test_rules_unknown_retains_before_any_save',
       'test_rules_restore_refusal_does_not_restore_seven',
       'test_false_condition_or_reused_room_rejected_before_prepare',
       'test_reward_unknown_latches_shared_native_owner_and_skips_cleanup',
       'test_other_mount_rejected_before_entry_build_or_native_access',
       'test_unresolved_remote_call_keeps_unknown_when_final_log_fails','test_observation_callbacks_drained_before_local_cleanup']

def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}

if __name__=='__main__':
    OUTPUT=PRIVATE/'a_reward_runtime_entry_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    transport.OUTPUT=OUTPUT;joint.OUTPUT=OUTPUT;before=pins();stream=io.StringIO()
    run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in NAMES))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins()
    unchanged=all(sources.get(k)==v for k,v in before.items())
    result=dict(result='PASS' if run.wasSuccessful() and run.testsRun==len(NAMES) and unchanged else 'FAIL',
        tests=run.testsRun,sources=sources,private_inputs=PRIVATE_INPUTS,sources_unchanged=unchanged,entry_integration_executed=any(r.get('code')==0 for r in ROWS),
        mounted_entry_integration_executed=any(r.get('code')==0 and r.get('actual_mount_cut') for r in ROWS),
        protected_integration_executed=True,service_constructor_shell=True,
        game_access=False,steam_access=False,native_execution=False,actual_tls=True,actual_journal=True,actual_file_backup=True,
        native_RAM_PE_publisher_channel_doubles=True,cases=ROWS,
        failures=[(str(t),d) for t,d in run.errors+run.failures])
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if result['result']=='PASS' else 1)
