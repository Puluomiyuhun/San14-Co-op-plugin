"""Typed successor control tests with an explicit owned native-RPC double."""
from datetime import datetime
from pathlib import Path
import ctypes as C
import hashlib, io, json, sys, threading, unittest

P=Path(__file__).resolve().parent; ROOT=P.parents[1]; PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import player_input_rebind_port as p

OUTPUT=None

class Body:
    def __init__(self):
        self.calls=[]; self.fault=None; self.transient=False; self.nonce=b'i'*32
        self.s=p.Snapshot(); s=self.s
        s.pid=123; s.birth=456; s.window=789; s.windowThread=9
        s.initialized=s.installed=s.held=s.acknowledged=s.publicationWrites=1
        s.phase=2; s.revision=s.acknowledgedRevision=2
        s.binding.room[:]=b'r'*16; s.binding.epoch[:]=b'e'*16; s.binding.attachment[:]=b'a'*16; s.binding.period=2
        s.leasesIssued=s.leasesCompleted=4
    def call(self,name,raw):
        self.calls.append(name); op=name.removeprefix('PlayerInput'); s=self.s
        typ={'Snapshot':p.Snapshot,'Rebind':p.Rebind,'Request':p.Request,'Acquire':p.Lease,'Complete':p.Lease}[op]
        q=typ.from_buffer_copy(raw)
        if op=='Snapshot':
            r=p.Snapshot.from_buffer_copy(bytes(s)); r.header=q.header; r.nonce[:]=q.nonce
            if self.transient:
                self.transient=False; r.active=1; r.acknowledged=0; r.acknowledgedRevision-=1
            return 0,bytes(r)
        assert bytes(q.binding)==bytes(s.binding)
        if op=='Rebind':
            assert s.phase==2 and s.held and s.acknowledged and not s.leaseId
            assert q.revision==s.revision+1
            s.binding=q.nextBinding; s.revision=s.acknowledgedRevision=q.revision
            if self.fault=='unknown':raise p.common.RemoteCallUnknown('owned lost rebind reply',dict(may_have_started=True))
            if self.fault=='open':s.held=0; s.localCommandPolicyOpen=1
            if self.fault=='old-binding':s.binding=q.binding
            if self.fault=='timeout':s.pending=1; s.acknowledged=0; s.acknowledgedRevision=q.revision-1
            if self.fault=='publication':s.publicationWrites+=1
            if self.fault=='callback-tail':self.transient=True
        if op=='Request':
            s.phase=q.phase; s.revision=s.acknowledgedRevision=q.revision; s.acknowledged=1
            s.held=int(q.phase!=0 or q.localReady); s.localReady=q.localReady
            s.localCommandPolicyOpen=int(not s.held); s.remoteExecutionPolicyOpen=int(q.phase==0)
        if op=='Acquire':
            assert s.phase==0 and q.sequence==s.leasesIssued+1
            s.leaseId=s.leaseSequence=s.leasesIssued=q.sequence; s.leaseRevision=q.revision; s.held=1; q.lease=q.sequence
        if op=='Complete':
            s.leaseId=0; s.leasesCompleted=q.sequence; s.held=int(s.phase!=0 or s.localReady)
        return 0,bytes(q)

class Cases(unittest.TestCase):
    def fixture(self):
        body=Body(); transport=p.Transport.__new__(p.Transport)
        transport.state=p.common.SharedCallState(threading.RLock(),lambda exc:None); transport._perform=body.call
        lease=p.InputLease(transport,nonce=body.nonce,binding=body.s.binding,pid=123,birth=456,window=789,
                           records=OUTPUT/self._testMethodName,wait_seconds=.02)
        n=p.Binding.from_buffer_copy(bytes(lease.binding)); n.period+=1; n.epoch[:]=b'f'*16; n.attachment[:]=b'b'*16
        return body,lease,n
    def test_two_generations_remain_load_until_explicit_new_planning(self):
        body,lease,n=self.fixture(); old=lease.local_binding
        report=lease.rebind_after_load(n)
        self.assertEqual(report['phase'],2); self.assertEqual(report['held'],1)
        self.assertEqual(body.calls.count('PlayerInputRequest'),0)
        self.assertNotEqual(old,lease.local_binding)
        with self.assertRaises(Exception):lease.verify_binding(old)
        lease.request_phase(0)
        ticket=lease.begin(lease.local_binding); self.assertEqual(ticket.sequence,5); lease.complete(ticket)
        lease.request_phase(2)
        n.period+=1; n.epoch[:]=b'g'*16; n.attachment[:]=b'c'*16
        lease.rebind_after_load(n)
        self.assertEqual(lease.snapshot().publicationWrites,1)
        self.assertEqual(lease.snapshot().leasesCompleted,5)
    def test_callback_tail_is_waited_not_mistaken_for_failed_ack(self):
        body,lease,n=self.fixture(); body.fault='callback-tail'
        result=lease.rebind_after_load(n)
        self.assertEqual(result['acknowledged'],1); self.assertIsNone(lease.failed)
    def test_wrong_successor_rejected_before_rpc(self):
        body,lease,n=self.fixture(); n.period+=1; count=len(body.calls)
        with self.assertRaises(Exception):lease.rebind_after_load(n)
        self.assertEqual(len(body.calls),count); self.assertIsNone(lease.failed)
    def test_planning_is_not_load(self):
        body,lease,n=self.fixture(); lease.request_phase(0)
        with self.assertRaises(Exception):lease.rebind_after_load(n)
        self.assertNotIn('PlayerInputRebind',body.calls)
    def test_unknown_rebind_prohibits_dependent_calls(self):
        body,lease,n=self.fixture(); body.fault='unknown'
        with self.assertRaises(p.common.RemoteCallUnknown):lease.rebind_after_load(n)
        self.assertIsNotNone(lease.state.unknown); count=len(body.calls)
        with self.assertRaises(Exception):lease.request_phase(0)
        with self.assertRaises(Exception):lease.snapshot()
        self.assertEqual(len(body.calls),count); self.assertTrue(body.s.held)
    def test_timeout_no_retry_or_planning(self):
        body,lease,n=self.fixture(); body.fault='timeout'
        with self.assertRaisesRegex(Exception,'unresolved'):lease.rebind_after_load(n)
        count=len(body.calls)
        with self.assertRaises(Exception):lease.rebind_after_load(n)
        self.assertEqual(len(body.calls),count); self.assertTrue(body.s.held)
    def test_false_ack_old_binding_refused(self):
        body,lease,n=self.fixture(); body.fault='old-binding'
        with self.assertRaisesRegex(Exception,'acknowledgement'):lease.rebind_after_load(n)
        self.assertIsNotNone(lease.failed)
    def test_release_or_new_owner_during_rebind_refused(self):
        body,lease,n=self.fixture(); body.fault='open'
        with self.assertRaisesRegex(Exception,'lost LOAD'):lease.rebind_after_load(n)
        self.assertIsNotNone(lease.failed)
    def test_publication_changed_refused(self):
        body,lease,n=self.fixture(); body.fault='publication'
        with self.assertRaisesRegex(Exception,'replaced owner'):lease.rebind_after_load(n)

if __name__=='__main__':
    OUTPUT=PRIVATE/'player_input_rebind_port_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); OUTPUT.mkdir(parents=True)
    sources={str(Path(m.__file__).resolve()):hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).resolve().is_relative_to(ROOT) and Path(m.__file__).suffix=='.py'}
    stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue()); print(stream.getvalue())
    stable=all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in sources.items())
    data=dict(result='PASS' if result.wasSuccessful() and stable else 'FAIL',tests=result.testsRun,sources=sources,inputs_unchanged=stable,game_access=False,native_rpc_double=True)
    data['artifacts']={str(f.relative_to(OUTPUT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in OUTPUT.rglob('*') if f.is_file()}
    path=OUTPUT/'result.json'; path.write_text(json.dumps(data,indent=2)); print(path); raise SystemExit(data['result']!='PASS')
