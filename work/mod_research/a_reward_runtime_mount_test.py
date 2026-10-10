"""Actual TLS/bootstrap/Journal/RuntimeMount; native business and transport owned doubles."""
from copy import deepcopy
from datetime import datetime
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import a_reward_runtime_mount as mounted
import a_runtime_reward_port_test as typed
import b_observed_completion_test as observed
from reward_checkpoint_fixture import World
from reward_room_flow import Replica,envelope
from reward_observed_flow import GuestConsumer
from observed_room_service import HostService

OUTPUT=None;ROWS=[]

class OwnedPlanningScheduler(typed.OwnedScheduler):
    """Production wire bytes; worker/native game body explicitly substituted."""
    def __init__(self,world):
        super().__init__(world);self.planning_state=0;self.open_calls=0;self.context=None;self.shared=None
    def call(self,name,raw):
        if self.shared is not None:return self.shared.invoke(lambda:self.perform(name,raw))
        return self.perform(name,raw)
    def perform(self,name,raw):
        if name=='ASaveRuntimeRewardConfigure':
            q=mounted.reward_port.Configure.from_buffer_copy(raw)
            self.context=q.context
            self.report=mounted.reward_port.Snapshot();self.report.header=mounted.base.Header(mounted.base.MAGIC,1,C.sizeof(self.report),13,0)
            self.report.nonce[:]=q.nonce;self.report.context=q.context;self.report.state=1;self.report.configured=1
        if name in ('ASaveRuntimeOpenPlanning','ASaveRuntimePlanningSnapshot'):
            kind=mounted.Open if name.endswith('OpenPlanning') else mounted.PlanningSnapshot
            q=kind.from_buffer_copy(raw);self.calls.append(name)
            if kind is mounted.Open:self.open_calls+=1;self.planning_state=2
            else:
                q.state=self.planning_state;q.hostThread=threading.get_native_id();q.opened=q.receiptMatched=1
            return 0,bytes(q)
        return super().call(name,raw)


def prepared(world):
    p=mounted.base.Prepare();p.pid=world.reader.pid;p.birth=world.birth;p.base=world.memory.base
    p.root=world.root;p.world=world.world;p.year,p.month,p.day=203,8,11;p.force=12;p.ruler=666
    p.epoch=123;p.period=1;p.nonce[:]=b'n'*32;p.native.attempt[:]=b't'*16;p.native.attachment[:]=b'x'*16
    p.native.ownerGeneration=1;p.roomInputDigest[:]=b'd'*32
    return p

class Cases(observed.Cases):
    def setUp(self):
        super().setUp()
        self.worlds={p:World(f) for p,f in (('A',12),('B',2))}
        self.worlds['A'].copy_tables_to_bootstrap_double(self.host);self.worlds['B'].copy_tables_to_bootstrap_double(self.guest)
        self.reward_key=secrets.token_bytes(32);self.cut_key=secrets.token_bytes(32)
        # Actual HostService methods over existing actual TLS servers. Its
        # startup/monitor is not executed by this bounded composition fixture.
        self.service=HostService.__new__(HostService);self.service.room=self.room;self.service.coordinator=self.c
        self.service.servers=self.servers;self.service.control=self.a;self.service._state_lock=threading.RLock()
        self.service._host_ready=False;self.service.guest_disconnected=threading.Event()
        self.mount=mounted.RuntimeMount(self.service,reward_key=self.reward_key,guest_cut_key=self.cut_key,records=self.folder/'mount')
        w=self.worlds['A'];self.prep=prepared(w);self.held=[]
        self.entry=SimpleNamespace(room=self.room,coordinator=self.c,provider=SimpleNamespace(reader=w.reader),prep=self.prep,
            hold=self.held.append,protection=SimpleNamespace(verify=lambda:None))
        self.scheduler=OwnedPlanningScheduler(w);self.addCleanup(self.scheduler.close)
        self.unknown=[];self.state=mounted.SharedCallState(threading.RLock(),self.unknown.append);self.scheduler.shared=self.state
        dll=self.folder/'owned-wire.dll';dll.write_bytes(b'explicit owned transport fixture')
        with patch.object(mounted,'MountTransport',return_value=self.scheduler):
            self.mount.bind_native(self.entry,SimpleNamespace(reader=w.reader),123,dll,self.prep,
                SimpleNamespace(module=123,nonce=self.prep.nonce),self.state,lambda w=w:w.birth)
        r,q,self.profile=self.first();self.assertTrue(self.adapter.apply(r,q,self.profile)['ok'])
        for p,w in self.worlds.items():w.attachment=self.c.attachments[p]

    def opened(self,report=True):
        self.mount.open(self.artifacts[1],self.room.artifacts,self.prep)
        self.flow=self.mount.flow;self.gate=self.mount.gate
        port=self.worlds['B'].port();self.replica=Replica(self.folder/'reward-B.sqlite',self.flow.scope,'B',port)
        self.consumer=GuestConsumer(self.b,self.replica,self.reward_key)
        self.guest_cut=mounted.GuestCutConsumer(self.consumer,self.profile,cut_key=self.cut_key,checkpoint_epoch=self.c.epoch)
        if report:self.consumer.report()

    def proposal(self,p):
        return envelope(self.flow.scope,'reward_submit',request_id=secrets.token_hex(16),district_id=11 if p=='A' else 2,
            officer_ids=[97] if p=='A' else [101])

    def evidence(self,**extra):
        ROWS.append(dict(case=self._testMethodName,mount=self.mount.status(),calls=list(self.scheduler.calls),
            owned_business_calls={p:w.calls for p,w in self.worlds.items()},**extra))

    def test_actual_two_actor_queue_cut_ready_and_readonly_seal(self):
        self.opened(False)
        self.mount.poll();self.assertEqual(self.mount.phase,'ACTIVE');self.assertIsNone(self.flow.last_guest)
        self.assertEqual(self.worlds['A'].calls,0);self.consumer.report()
        self.assertNotEqual(self.mount.local_epoch,self.c.epoch)
        self.assertNotEqual(bytes(self.mount.prep.native.attachment).hex(),self.mount.attachment)
        self.assertEqual(bytes(self.mount.profile),bytes(self.profile))
        for player,client in (('A',self.a),('B',self.b)):
            self.assertTrue(client.request(self.proposal(player))['ok']);self.mount.poll();self.guest_cut.poll()
        self.assertTrue(self.a.request(dict(action='reward_cut_prepare',epoch=self.c.epoch))['ok'])
        self.guest_cut.finish_input();self.mount.poll();self.assertEqual(self.gate.state,'COLLECTING')
        self.guest_cut.poll();self.mount.poll();self.assertEqual(self.mount.phase,'RETIRED')
        self.guest_cut.ready_after_cut();permit=self.c.seal_inputs();self.c.begin_simulation(permit)
        self.mount.validate_seal(permit);sample=self.mount.observe_sealed(self.c.node)
        self.assertEqual(sample.world_sha256,permit['world_sha256']);self.assertEqual(permit['sequence'],2)
        self.scheduler.planning_state=3;before=len(self.scheduler.calls);self.mount.poll()
        self.assertEqual(len(self.scheduler.calls),before);self.assertEqual(self.scheduler.open_calls,1)
        self.evidence(cut=permit,planning_context_period=self.prep.period,room_period=self.c.period)

    def test_bootstrap_state_rebuild_refused_before_open(self):
        w=self.worlds['A'];replacement=w.obj(mounted.reward.PLANNING_STACK[-1],0x800);w.memory.put(replacement+0x70,mounted.reward.PLANNING_STACK[-1].encode()+b'\0')
        array=w.reader.pointer(w.memory.base+0x19E7310+0x20);w.memory.pack(array+32,'<Q',replacement)
        with self.assertRaisesRegex(Exception,'attachment changed'):self.mount.open(self.artifacts[1],self.room.artifacts,self.prep)
        self.assertEqual(self.scheduler.open_calls,0);self.assertEqual(self.mount.phase,'HELD');self.evidence()

    def test_unknown_submit_holds_shared_entry_and_no_replay(self):
        self.opened();self.scheduler.fault='unknown';self.assertTrue(self.a.request(self.proposal('A'))['ok'])
        with self.assertRaises(Exception):self.mount.poll()
        self.assertTrue(self.state.unknown);self.assertEqual(len(self.unknown),1)
        with self.assertRaises(Exception):self.mount.poll()
        self.assertEqual(self.scheduler.calls.count('ASaveRuntimeRewardSubmit'),1)
        with self.assertRaises(Exception):self.state.invoke(lambda: self.fail('Stop must not run'))
        self.evidence()

class BuildCases(unittest.TestCase):
    def test_actual_approved_runtime_windows_artifact_paths(self):
        folder=PRIVATE/'a_runtime_reward_planning_runs/20261010-021152-669026'
        args=SimpleNamespace(reward_build_run=folder,reward_build_sha256=hashlib.sha256((folder/'result.json').read_bytes()).hexdigest())
        result,data=mounted.approved_planning_runtime(args,dict(production=dict(binaries={})))
        self.assertEqual(result['production']['binaries']['a_save_local_runtime.dll'],'59f37d7510fe10cd9abf2fdfbbfdf80f75b4eed6b6868b1123734fa1028d687a')
        self.assertEqual(C.sizeof(mounted.Open),192);self.assertEqual(C.sizeof(mounted.PlanningSnapshot),216)
        ROWS.append(dict(case=self._testMethodName,production_build_sha256=args.reward_build_sha256))

def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}

if __name__=='__main__':
    OUTPUT=PRIVATE/'a_reward_runtime_mount_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    observed.transport.OUTPUT=OUTPUT
    # Import all production lazy dependencies before pinning.
    import reward_checkpoint_shared_cut,reward_checkpoint_observer,b_warm_remote_completion
    before=pins();stream=io.StringIO()
    suite=unittest.TestSuite(cls(n) for cls in (Cases,BuildCases) for n in cls.__dict__ if n.startswith('test_'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);after=pins()
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    report=dict(result='PASS' if result.wasSuccessful() and before==after else 'FAIL',tests=result.testsRun,sources=after,
        inputs_unchanged=before==after,cases=ROWS,game_access=False,steam_access=False,
        actual_mount_TLS_journal_checked_projection=True,native_transport_business_RAM_doubles=True,
        host_service_constructor_monitor_executed=False,mounted_entry_integration_executed=False,
        failures=[(str(t),s) for t,s in result.failures+result.errors])
    report['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(report['result']!='PASS')

