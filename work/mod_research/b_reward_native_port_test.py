"""Typed B dispatch over owned memory; scheduler and native business are explicit doubles."""
from datetime import datetime
import ctypes as C
import hashlib,io,json,sys,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_reward_native_port as port
import a_runtime_reward_port_test as old
from reward_observed_context import CheckedPort
from reward_room_flow import Replica
import execution_journal as journal
OUTPUT=None
class Scheduler(old.OwnedScheduler):
    def call(self,name,raw):
        if name in ('BRewardStop','BRewardRestore'):
            self.calls.append(name)
            if name=='BRewardStop':self.stopped=True
            else:self.restored=True
            return 0,raw
        if name=='BRewardSubmit':
            self.calls.append(name)
            return super().call('ASaveRuntimeRewardSubmit',raw)
        if name=='BRewardSnapshot':
            q=port.Snapshot.from_buffer_copy(raw)
            aq=old.port.Snapshot.from_buffer_copy(raw[:C.sizeof(old.port.Snapshot)])
            _,answer=super().call('ASaveRuntimeRewardSnapshot',bytes(aq))
            s=port.Snapshot.from_buffer_copy(answer+bytes(C.sizeof(port.Snapshot)-len(answer)))
            s.header=q.header;s.readyResealed=0;s.nativeClean=s.armed=1
            if s.state==2:s.submitted=s.sequence
            s.bridgeStarted=s.bridgeFinally=s.completed
            if getattr(self,'stopped',False):s.admissionClosed=s.stopped=1
            if getattr(self,'restored',False):s.armed=0;s.slotRestored=s.restoreVerified=1
            return 0,bytes(s)
        raise AssertionError(name)
class Tests(unittest.TestCase):
    def fixture(self):
        folder=OUTPUT/self._testMethodName;folder.mkdir()
        w=old.World(12);sampler=w.port().sampler;sch=Scheduler(w);self.addCleanup(sch.close)
        n=port.NativePort.__new__(port.NativePort)
        c=port.Context();c.pid=w.reader.pid;c.birth=w.birth;c.period=2;c.epoch=123
        c.native.attempt[:]=b'a'*16;c.native.attachment[:]=bytes.fromhex(w.attachment);c.native.ownerGeneration=1;c.inputDigest[:]=b'd'*32
        held=[];n.session=SimpleNamespace(phase='REWARD_PLANNING',warm=SimpleNamespace(calls=SimpleNamespace(uncertain=False)),factory=SimpleNamespace(uncertain=False),boundary=SimpleNamespace(hold=held.append))
        # Factory/process attachment is not claimed by this owned dispatch test.
        n._graph=lambda:n.state.require_known()
        n.state=port.SharedCallState(threading.RLock(),n._unknown)
        transport=port.Transport.__new__(port.Transport);transport.state=n.state;transport._perform=sch.call
        port.common.RuntimeRewardPort.__init__(n,sampler,transport,nonce=b'n'*32,context=c,records=folder,wait_seconds=.3,poll_seconds=.005)
        n.closed=False;n.configured=True;n.restore_attempted=False;n.session.reader=w.reader
        n.slot_planning={};n.slot_storage={};n.slot_baseline=[]
        checked=CheckedPort(sampler,n)
        scope=dict(schema='san14.replica-scope.v1',room_id='1'*32,binding_epoch='2'*32,timeline_epoch='3'*32,
            profile=dict(protocol='san14.room.v1',game_sha256=old.reward.SUPPORTED_SHA256,adapter_contract='research-no-native-room-adapter.v1',checkpoint_sha256='c'*64,rules_sha256='d'*64),
            bindings=dict(A=dict(force_id=12,main_district_id=11),B=dict(force_id=2,main_district_id=2)),state_contract=old.CONTRACT,initial_state_sha256=checked.observe())
        rep=Replica(folder/'journal.sqlite',scope,'B',checked);n.attach_journal(rep.journal)
        def intent(seq,player):
            force,district,person=(12,11,97) if player=='A' else (2,2,101)
            return journal.make_intent(scope,seq,player,format(seq,'032x'),rep.command(force,district,[person]),rep.journal.status()['state_sha256'])
        return w,sch,n,rep,intent
    def test_two_actor_durable_dispatch_and_duplicate(self):
        w,s,n,r,i=self.fixture()
        for seq,player in ((1,'A'),(2,'B')):
            event=i(seq,player);self.assertEqual(r.apply(event)['status'],'APPLIED_LOCAL');self.assertTrue(r.apply(event)['duplicate'])
        self.assertEqual(w.calls,2);self.assertEqual(s.calls.count('BRewardSubmit'),2);self.assertEqual(r.journal.status()['phase'],'IDLE')
    def test_no_durable_intent_no_native_submit(self):
        w,s,n,r,i=self.fixture()
        with self.assertRaises(RuntimeError):n.execute(i(1,'A')['command'])
        self.assertEqual(w.calls,0);self.assertNotIn('BRewardSubmit',s.calls)
    def test_unknown_latches_retained_session_and_never_replays(self):
        w,s,n,r,i=self.fixture();s.fault='unknown';event=i(1,'B')
        with self.assertRaises(journal.ExecutionHeld):r.apply(event)
        self.assertTrue(s.done.wait(2));self.assertEqual(n.session.phase,'TERMINAL')
        self.assertTrue(n.session.warm.calls.uncertain);self.assertTrue(n.session.factory.uncertain)
        with self.assertRaises(Exception):r.apply(event)
        self.assertEqual(w.calls,1);self.assertEqual(s.calls.count('BRewardSubmit'),1)
    def test_retired_sampler_still_allows_verified_restore(self):
        w,s,n,r,i=self.fixture();r.apply(i(1,'A'));n.sampler.retire('cut committed')
        with patch.object(port,'live_hook_evidence',return_value=[]) as slots:
            result=n.stop_restore();self.assertTrue(result['native_bridge_restored']);n.verify_restored()
            self.assertEqual(slots.call_count,2)
        self.assertEqual(s.calls.count('BRewardStop'),1);self.assertEqual(s.calls.count('BRewardRestore'),1)
        with self.assertRaises(Exception):n.stop_restore()
        self.assertEqual(s.calls.count('BRewardRestore'),1)
    def test_native_restore_receipt_does_not_override_slot_drift(self):
        w,s,n,r,i=self.fixture();r.apply(i(1,'A'));n.sampler.retire('cut committed')
        with patch.object(port,'live_hook_evidence',side_effect=RuntimeError('owned slot drift')):
            with self.assertRaisesRegex(RuntimeError,'slot drift'):n.stop_restore()
        self.assertEqual(n.session.phase,'TERMINAL');self.assertEqual(s.calls.count('BRewardRestore'),1)
    def test_uncleared_native_result_holds(self):
        w,s,n,r,i=self.fixture();s.fault='not-cleared'
        with self.assertRaises(journal.ExecutionHeld):r.apply(i(1,'A'))
        self.assertEqual(n.session.phase,'TERMINAL');self.assertEqual(r.journal.status()['phase'],'HOLD')
if __name__=='__main__':
    OUTPUT=PRIVATE/'b_reward_native_port_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (OUTPUT/'test.log').write_text(stream.getvalue());print(stream.getvalue())
    stable=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in sources.items())
    result=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,game_access=False,native_business_double=True,production_factory_executed=False,sources=sources,inputs_unchanged=stable)
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(result,indent=2));print(OUTPUT/'result.json')
    raise SystemExit(result['result']!='PASS')
