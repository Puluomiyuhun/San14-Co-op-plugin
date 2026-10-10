"""Actual entry lifecycle + TLS/Room/Session, explicit native/PE/RAM doubles.
No game/Steam access. Own files exercise real backup and result inventory.
New typed three-slot wire, finite sampler, room control and B chain are real Python code.
"""
from contextlib import ExitStack
from datetime import datetime
import hashlib,io,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import a_observed_three_start as start
import a_observed_start_call as safe_call
import ctypes as C
import a_b_three_joint_test as joint
from b_observed_completion_test import *
import checkpoint_complete_live_capture as capture_module
import checkpoint_push_start
import game_reader
import run_autonomous_pilot
import a_save_three_ipc_client as a_save_ipc_client
import a_save_three_runtime_contract as wire
import a_save_three_repeat_contract as repeat
import a_observed_three_boundary as new_boundary
import a_observed_boundary_test as boundary_fixture
from a_observed_three_room import ObservedRoom
from a_observed_three_boundary_test import complete
import pefile

OUTPUT=None;ROWS=[];PRIVATE_INPUTS={}

class Cases(joint.Cases):
    test_direct_predecessor_type_and_snapshot_gaps_are_real=None
    test_actual_three_control_chain_session_signed_completions=None
    def complete_host(self,generation):complete(self.host_fixture,generation)
    def setUp(self):
        for obj,name,value in ((boundary_fixture,'wire',wire),(boundary_fixture,'observed',new_boundary)):
            guard=patch.object(obj,name,value);guard.start();self.addCleanup(guard.stop)
        # The predecessor fixture ordinarily enrolls its own A adapter. Omit
        # that setup only: the entry under test performs the real enrollment.
        with patch.object(ObservedRoom,'enroll_observed_adapter'):
            super().setUp()
        self.entry=start.RoomEntry(self.room,self.c,self.key,no_new_commands=True)
        self.calls=[];self.published=[];self.events=[];self.fault=None
        f=self.host_fixture
        self.raw=wire.envelope(wire.Prepare,'Prepare',f.nonce)
        self.raw.pid,self.raw.birth,self.raw.base=f.reader.pid,f.birth,f.reader.memory.base
        self.raw.root,self.raw.world,self.raw.cache=f.reader.root,f.reader.world,f.cache
        self.raw.epoch,self.raw.period,self.raw.nativeRoomEpoch=123,1,71
        self.raw.year,self.raw.month,self.raw.day,self.raw.force,self.raw.ruler=203,8,11,12,666
        self.raw.states[:]=[a for _,a in f.reader.states]
        self.source_dir=self.folder/'a-saves';self.source_dir.mkdir()
        self.source=self.source_dir/'svdexSC34.s14';self.source.write_bytes(b'owned initial save')
        self.bundle=self.folder/'bundle';self.bundle.mkdir()
        for name in ('a_save_local_runtime.dll','checkpoint_planning_hold.dll','publisher.exe'):
            (self.bundle/name).write_bytes(('explicit owned binary double '+name).encode())
        (self.bundle/'result.json').write_text('{}')
        self.args=SimpleNamespace(build_run=self.bundle,publisher_build=self.bundle,repeat_abi_run=self.bundle,
            launcher_test_run=self.bundle,entry_test_run=self.bundle,wait_seconds=3)
        self.captured=dict(planning={'fixture':True},storage={'fixture':True})
        self.received_count=0;self.commands=[];self.polls=0;self.stopped=False;self.final=None

    def run_entry(self):
        owner=self;f=self.host_fixture;modules=[];exports={name:0x100+v*16 for name,v in repeat.OPS.items()}
        class API:
            def __init__(self,reader):owner.calls.append('open-api')
            def modules(self):return modules[:]
            def load_library_address(self):return 0x111
            def close(self):owner.calls.append('close-api')
        class PE:
            def __init__(self,path):self.DIRECTORY_ENTRY_EXPORT=SimpleNamespace(symbols=[SimpleNamespace(name=('ASaveRuntime'+n).encode(),address=a) for n,a in exports.items()])
            def close(self):pass
        class Channel:
            def __init__(self,*a,**k):self.reservation=None;owner.calls.append('channel-open')
            def submit(self,reservation):self.reservation=reservation;owner.calls.append('submit-'+str(reservation.generation))
            def wait_artifact(self,generation,timeout):
                owner.complete_host(generation)
                artifact=model_artifact(self.reservation.request,generation,data=('owned Save '+str(generation)).encode()*2100)
                (owner.source_dir/self.reservation.request['filename']).write_bytes(artifact.data)
                return artifact
            def snapshot(self):return None
            def stop(self):owner.calls.append('channel-stop')
            def close(self):owner.calls.append('channel-close')
        def remote(api,address,raw,run,label):
            if address==0x111:
                path=Path(raw.decode('utf-16le').rstrip('\0'));base=f.plans.module if path.name=='a_save_local_runtime.dll' else 0x900000000
                modules.append((base,path));owner.calls.append('load-'+path.name);return 0,raw
            op=next(n for n,a in exports.items() if address==f.plans.module+a);owner.calls.append(op)
            if owner.fault=='tls-unknown' and op=='Snapshot' and owner.c.phase=='RECONCILING':
                raise start.RemoteCallUnknown('owned unresolved TLS Snapshot',{'label':label})
            if op=='Plans':answer=f.plans
            elif op=='Snapshot':
                answer=f.snapshot()
                if owner.stopped:answer.stopped=answer.ownerStopped=answer.restoreReady=1;answer.ready=0
            elif op=='RequestNext':
                answer=repeat.Next.from_buffer_copy(raw);owner.commands.append(answer);owner.polls=0
            elif op=='RepeatSnapshot':
                q=repeat.envelope(repeat.Snapshot,op,f.nonce)
                if owner.commands:
                    q.request=owner.commands[-1].request;q.hostThread=q.previousArtifactMatched=1;q.retiredSerial=q.retiredCount=len(owner.commands)
                    owner.polls+=1;q.state=3 if owner.polls<3 or owner.fault=='running-stop' else 4
                    q.activeGeneration=len(owner.commands) if q.state==3 else len(owner.commands)+1;q.requested=q.drainPending=int(q.state==3);q.nativeDateMatched=int(q.state==4)
                    if q.state==4 and (f.node['month'],f.node['day'])!=(q.request.month,q.request.day):
                        f.complete_and_rebuild();complete(f,len(owner.commands))
                        f.node.update(year=q.request.year,month=q.request.month,day=q.request.day)
                        f.write(f.reader.world+0x36,q.request.month,'<B');f.write(f.reader.world+0x37,q.request.day,'<B')
                if not owner.commands:q.activeGeneration=1
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
            replacements=[(start,'PRIVATE',self.folder/'private'),(start,'verify_entry_tests',lambda _:None),
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
            code=start.execute(self.args,self.folder/'capture.json',self.captured,entry=self.entry,on_event=event)
        resultfile=next((self.folder/'private/a_observed_three_start_runs').glob('*/result.json'))
        self.final=json.loads(resultfile.read_text())
        ROWS.append(dict(case=self._testMethodName,code=code,result=self.final,events=self.events,calls=self.calls,published=self.published))
        return code

    def test_execute_three_tls_completions_two_turns_and_cleanup(self):
        self.assertEqual(self.run_entry(),0)
        self.assertEqual(self.final['result'],'PASS_OBSERVED_ROOM_THREE_SAVES')
        self.assertEqual(self.received_count,3);self.assertEqual(self.published,['install','restore'])
        self.assertEqual(self.calls.count('Prepare'),1);self.assertEqual(self.calls.count('RequestNext'),2)
        self.assertEqual(self.entry.phase,'THREE_COMPLETIONS_RETAINED')
        self.assertEqual((self.c.node['month'],self.c.node['day']),(9,1))
        self.assertTrue(self.final['save_comparison']['only_expected_new_files'])
        self.assertTrue(self.final['save_comparison']['originals_unchanged'])
        with self.assertRaises(RuntimeError):self.entry.prepare(self.raw)

    def test_unknown_native_result_holds_and_skips_restore(self):
        self.fault='tls-unknown';self.assertEqual(self.run_entry(),1)
        self.assertTrue(self.final['uncertain']);self.assertNotIn('Stop',self.calls)
        self.assertEqual(self.published,['install']);self.assertEqual(self.entry.phase,'HELD')
        self.assertNotIn('submit-2',self.calls);self.assertFalse(self.warm.events)

    def test_stop_while_running_does_not_claim_restored(self):
        self.fault='running-stop';self.assertEqual(self.run_entry(),1)
        self.assertIn('Stop',self.calls);self.assertEqual(self.published,['install'])
        self.assertFalse(self.final['cleanup_verified']);self.assertEqual(self.received_count,1)
        self.assertNotIn('submit-2',self.calls)

    def test_refuses_unagreed_condition_and_reused_entry(self):
        with self.assertRaises(RuntimeError):start.RoomEntry(self.room,self.c,self.key,no_new_commands=False)
        self.entry.prepare(self.raw)
        with self.assertRaises(RuntimeError):self.entry.prepare(self.raw)
        self.assertEqual(self.calls,[])

def pins():
    return joint.chain.pins()

if __name__=='__main__':
    output=PRIVATE/'a_observed_three_start_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    transport.OUTPUT=output;before=pins();before[str(Path(__file__).resolve())]=start.sha(__file__)
    log=io.StringIO();r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (output/'tests.log').write_text(log.getvalue(),encoding='utf-8');after=pins();after[str(Path(__file__).resolve())]=start.sha(__file__)
    stable=all(after.get(p)==h for p,h in before.items())
    report=dict(family='san14.a-observed-three-start.v1',result='PASS' if r.wasSuccessful() and stable else 'FAIL',
        tests=r.testsRun,sources=after,sources_unchanged=stable,entry_integration_executed=True,game_access=False,
        actual_TLS=True,actual_entry_execute=True,native_save_load_PE_process_approval_doubles=True,cases=ROWS)
    report['artifacts']={str(p):start.sha(p) for p in output.rglob('*') if p.is_file()}
    path=output/'result.json';path.write_text(json.dumps(report,indent=2)+'\n');print(log.getvalue());print(json.dumps(dict(result=report['result'],path=str(path),sha256=start.sha(path))))
    raise SystemExit(report['result']!='PASS')

