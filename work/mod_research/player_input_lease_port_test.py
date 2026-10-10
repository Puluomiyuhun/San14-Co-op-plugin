"""Actual A/B typed reward + CheckedPort/SQLite, with explicit HWND/native doubles."""
from datetime import datetime
import ctypes as C
import hashlib,io,json,sys,threading,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import player_input_lease_port as p
import b_reward_native_port_test as btyped
import a_runtime_reward_port_test as atyped
import execution_journal as journal
OUTPUT=None
class InputBody:
    def __init__(self,native):
        self.calls=[];self.fault=None;self.s=p.Snapshot();s=self.s
        s.pid,s.birth=native.binding[:2];s.window=12345;s.windowThread=77;s.initialized=s.installed=s.held=1;s.phase=5
        s.binding.room[:]=b'r'*16;s.binding.epoch[:]=bytes.fromhex(native.binding[2]);s.binding.attachment[:]=bytes.fromhex(native.binding[3]);s.binding.period=2;s.controlMessage=0xC001
        self.nonce=b'i'*32
    def call(self,name,raw):
        self.calls.append(name);op=name.removeprefix('PlayerInput');kind={'Request':p.Request,'Snapshot':p.Snapshot}.get(op,p.Lease);q=kind.from_buffer_copy(raw);s=self.s
        if op=='Snapshot':
            r=p.Snapshot.from_buffer_copy(bytes(s));r.header=q.header;r.nonce[:]=q.nonce;return 0,bytes(r)
        if op=='Request':
            assert not s.leaseId
            s.phase=q.phase;s.localReady=q.localReady;s.revision=s.acknowledgedRevision=q.revision;s.acknowledged=1
            s.held=int(s.phase!=0 or bool(s.localReady));s.remoteExecutionPolicyOpen=int(s.phase==0);s.localCommandPolicyOpen=int(not s.held)
            if self.fault=='ack-without-hold':s.held=0
            if self.fault=='ack-local-open':s.localCommandPolicyOpen=1
            if self.fault=='ack-remote-open':s.remoteExecutionPolicyOpen=1
        if op=='Acquire':
            assert s.phase==0 and not s.leaseId and q.sequence==s.leasesIssued+1
            if self.fault=='reject-acquire':return 1,raw
            s.leaseId=s.leaseSequence=s.leasesIssued=q.sequence;s.leaseRevision=q.revision;s.held=1;q.lease=q.sequence
        if op=='Complete':
            assert s.leaseId==q.lease
            s.leaseId=0;s.leasesCompleted=q.sequence;s.held=int(s.phase!=0 or bool(s.localReady))
            if self.fault=='unknown-complete':raise p.common.RemoteCallUnknown('owned lost Complete',dict(may_have_started=True))
        if op=='Unknown':s.phase=5;s.held=s.uncertain=1
        return 0,bytes(q)
class Cases(unittest.TestCase):
    def fixture(self,side='B'):
        if side=='B':
            w,sch,n,rep,intent=btyped.Tests.fixture(self)
        else:
            f=atyped.Fixture(OUTPUT/self._testMethodName);self.addCleanup(f.scheduler.close)
            w,sch,n,rep,intent=f.world,f.scheduler,f.native,f.replica,f.intent
            state=p.common.SharedCallState(threading.RLock(),lambda exc:None)
            transport=p.common.RemoteTransport.__new__(p.common.RemoteTransport);transport.state=state;transport._perform=sch.call;n.transport=transport
        body=InputBody(n);transport=p.Transport.__new__(p.Transport);transport.state=n.transport.state;transport._perform=body.call
        lease=p.InputLease(transport,nonce=body.nonce,binding=body.s.binding,pid=n.binding[0],birth=n.binding[1],window=body.s.window,records=OUTPUT/self._testMethodName/'input',wait_seconds=.1)
        rep.port.attach_input_lease(lease);lease.request_phase(0,True)
        return w,sch,n,rep,intent,body,lease
    def run_ready(self,side):
        w,s,n,r,i,body,lease=self.fixture(side);original=w.execute
        def execute(command):
            self.assertTrue(body.s.held);self.assertNotEqual(body.s.leaseId,0)
            for phase in (1,2,3,4):
                with self.assertRaises(Exception):lease.request_phase(phase)
            return original(command)
        w.execute=execute
        event=i(1,'B');self.assertEqual(r.apply(event)['status'],'APPLIED_LOCAL');self.assertEqual(w.calls,1)
        self.assertEqual(body.s.leasesCompleted,1);self.assertEqual(body.s.held,1);self.assertFalse(body.s.leaseId)
        self.assertTrue(r.apply(event)['duplicate']);self.assertEqual(body.calls.count('PlayerInputAcquire'),1)
        lease.request_phase(2);self.assertEqual(body.s.phase,2)
    def test_A_ready_allows_remote_and_blocks_load_during_execution(self):self.run_ready('A')
    def test_B_ready_allows_remote_and_blocks_load_during_execution(self):self.run_ready('B')
    def test_effect_check_failure_retains_lease_and_holds(self):
        w,s,n,r,i,body,lease=self.fixture();w.failure='unselected'
        with self.assertRaises(Exception):r.apply(i(1,'B'))
        self.assertEqual(body.calls.count('PlayerInputComplete'),0);self.assertEqual(body.calls.count('PlayerInputUnknown'),1)
        self.assertTrue(body.s.held);self.assertTrue(body.s.leaseId);self.assertEqual(r.journal.status()['phase'],'HOLD')
    def test_native_unknown_forbids_even_cleanup_rpc(self):
        w,s,n,r,i,body,lease=self.fixture();s.fault='unknown';event=i(1,'B')
        with self.assertRaises(journal.ExecutionHeld):r.apply(event)
        self.assertTrue(s.done.wait(2));self.assertTrue(n.state.unknown);self.assertTrue(body.s.held)
        self.assertNotIn('PlayerInputComplete',body.calls);self.assertNotIn('PlayerInputUnknown',body.calls)
        count=len(body.calls)
        with self.assertRaises(Exception):lease.request_phase(2)
        self.assertEqual(len(body.calls),count)
    def test_known_acquire_rejection_stops_before_reward_and_closes_input(self):
        w,s,n,r,i,body,lease=self.fixture();body.fault='reject-acquire'
        with self.assertRaises(journal.ExecutionHeld):r.apply(i(1,'B'))
        self.assertEqual(w.calls,0);self.assertEqual(body.s.phase,5);self.assertTrue(body.s.held)
    def test_lost_complete_reply_keeps_journal_unknown_no_replay(self):
        w,s,n,r,i,body,lease=self.fixture();body.fault='unknown-complete';event=i(1,'A')
        with self.assertRaises(journal.ExecutionHeld):r.apply(event)
        with self.assertRaises(Exception):r.apply(event)
        self.assertEqual(w.calls,1);self.assertTrue(n.state.unknown);self.assertEqual(body.calls.count('PlayerInputComplete'),1)
    def test_ack_without_ready_hold_rejected(self):
        w,s,n,r,i,body,lease=self.fixture();body.fault='ack-without-hold'
        with self.assertRaisesRegex(Exception,'does not enforce'):lease.request_phase(0,True)
        self.assertIsNotNone(lease.failed);self.assertEqual(w.calls,0)
    def test_ack_with_local_commands_open_rejected(self):
        w,s,n,r,i,body,lease=self.fixture();body.fault='ack-local-open'
        with self.assertRaisesRegex(Exception,'does not enforce'):lease.request_phase(0,True)
        self.assertIsNotNone(lease.failed);self.assertEqual(w.calls,0)
    def test_load_ack_with_remote_execution_open_rejected(self):
        w,s,n,r,i,body,lease=self.fixture();body.fault='ack-remote-open'
        with self.assertRaisesRegex(Exception,'does not enforce'):lease.request_phase(2)
        self.assertIsNotNone(lease.failed);self.assertEqual(w.calls,0)
    def test_changed_attachment_rejected_before_native(self):
        w,s,n,r,i,body,lease=self.fixture();body.s.binding.attachment[0]^=1
        with self.assertRaises(journal.ExecutionHeld):r.apply(i(1,'B'))
        self.assertEqual(w.calls,0);self.assertNotIn('PlayerInputAcquire',body.calls)
if __name__=='__main__':
    OUTPUT=PRIVATE/'player_input_lease_port_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True);btyped.OUTPUT=OUTPUT
    sources={str(Path(m.__file__).resolve()):hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).resolve().is_relative_to(ROOT) and Path(m.__file__).suffix=='.py'}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue());print(stream.getvalue());stable=all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in sources.items())
    d=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,game_access=False,HWND_and_native_business_doubles=True,actual_typed_A_B_CheckedPort_SQLite=True,sources=sources,inputs_unchanged=stable)
    d['artifacts']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in OUTPUT.rglob('*') if f.is_file()};(OUTPUT/'result.json').write_text(json.dumps(d,indent=2));print(OUTPUT/'result.json');raise SystemExit(d['result']!='PASS')
