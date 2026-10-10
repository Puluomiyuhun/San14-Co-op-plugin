"""Three IPC client framing/failure tests and actual TLS room/native-wire control.
Pipe transport and native save/load/Runtime are explicit doubles; no game access.
"""
from datetime import datetime
import hashlib,io,json,sys,unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch
P=Path(__file__).resolve().parent;ROOT=P.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import a_save_three_ipc_client as ipc
import a_save_ipc_client as old
import checkpoint_three_save_packet as pkt
from checkpoint_fresh_save_binding import SaveReservation
from checkpoint_fresh_save_binding_test import model_artifact
import a_observed_three_native_control as native_control
import a_save_three_runtime_contract as wire
import a_save_three_repeat_contract as repeat
import a_b_three_joint_test as joint

OUT=None
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reservation(generation):
    q=dict(generation=generation,room_epoch=71,period=generation,cut=0,room_id=b'r'*32,
        year=203,month=8 if generation<3 else 9,day=11 if generation==1 else 21 if generation==2 else 1,
        ruler=666,force=12,reserved=0,filename=f'mp{generation:08x}.s14')
    return SaveReservation(generation,hashlib.sha256(str(generation).encode()).hexdigest(),MappingProxyType(q))

def packet(q):
    data=('owned synthetic Save '+str(q['generation'])).encode()*29
    a=model_artifact(q,q['generation'],data=data);q=dict(q);q['filename']=q['filename'].encode()+b'\0\0'
    return (pkt.PREFIX.pack(pkt.MAGIC,1,pkt.HEADER_BYTES,len(data))+
        pkt.REQUEST.pack(*(q[k] for k in pkt.REQUEST_FIELDS))+
        pkt.REPORT.pack(*(a.report[k] for k in pkt.REPORT_FIELDS))+bytes.fromhex(a.sha256)+data)

class NativeTransportDouble:
    def __init__(self):self.sent=[];self.closed=False;self.quarantined=False;self.saved={};self.fail=None
    def close(self):self.closed=True
    def exchange(self,raw,timeout):
        self.sent.append(raw);magic,version,op,seq,secret,binding=ipc.PREFIX.unpack_from(raw)
        row=ipc.SAVE_REQUEST.unpack_from(raw,ipc.PREFIX.size);generation=row[0]
        q=dict(zip(ipc.REQUEST_FIELDS,row));data=b''
        if op==ipc.SUBMIT:
            q['filename']=q['filename'].rstrip(b'\0').decode();self.saved[generation]=q
        if self.fail=='lost-third' and op==ipc.SUBMIT and generation==3:raise OSError('lost third reply')
        if op==ipc.COPY:
            data=packet(self.saved[generation])
            if self.fail=='bad-third' and generation==3:data=data[:-1]+bytes([data[-1]^1])
        count=len(self.saved)
        if self.fail=='fourth-count':count=4
        snap=dict(owner_error=0,initialized=1,armed=1,stopped=int(op==ipc.STOP),save_status=5,save_error=0,
            completed_requests=count,binds=1,queues=1,user_subset_held=0,generation=generation,active_scopes=0,capabilities=0)
        body=ipc.SNAPSHOT_PAYLOAD.pack(*(snap[k] for k in ipc.SNAPSHOT_FIELDS))+data
        return ipc.RESPONSE.pack(magic,version,op,seq,ipc.OK,len(body),binding)+body

class ClientCases(unittest.TestCase):
    def make(self,client=ipc.ASaveClient):
        t=NativeTransportDouble();faults=[]
        c=client(ipc.Endpoint('\\\\.\\pipe\\san14-a-save-'+'2'*32,23,31,b's'*32),on_fault=faults.append,transport_factory=lambda _:t)
        self.addCleanup(c.close);return c,t,faults
    def first_two(self,c):
        for n in (1,2):c.submit(reservation(n));self.assertEqual(c.copy(n).request['generation'],n)
    def test_three_complete_packets_same_client_and_fourth_refused(self):
        c,t,f=self.make();self.first_two(c);c.submit(reservation(3));a=c.copy(3)
        self.assertEqual(a.report['completed_requests'],3);self.assertEqual(c.status()['delivered_generations'],[1,2,3])
        before=len(t.sent)
        with self.assertRaises(ipc.ASaveChannelError):c.submit(reservation(4))
        self.assertEqual(len(t.sent),before);self.assertEqual(f,[])
        self.assertEqual(c.copy(1).request['generation'],1);self.assertEqual(c.status()['submitted_generations'],[1,2,3])
    def test_next_requires_previous_artifact_and_order(self):
        c,t,f=self.make()
        with self.assertRaises(ipc.ASaveChannelError):c.submit(reservation(2))
        self.assertEqual(t.sent,[]);c.submit(reservation(1));before=len(t.sent)
        with self.assertRaises(ipc.ASaveChannelError):c.submit(reservation(2))
        self.assertEqual(len(t.sent),before);c.copy(1);c.submit(reservation(2))
    def test_lost_third_reply_consumed_terminal_no_replay(self):
        c,t,f=self.make();self.first_two(c);t.fail='lost-third'
        with self.assertRaises(OSError):c.submit(reservation(3))
        before=len(t.sent);self.assertEqual(c.status()['submitted_generations'],[1,2,3]);self.assertTrue(t.closed)
        with self.assertRaises(ipc.ASaveChannelError):c.submit(reservation(3))
        with self.assertRaises(ipc.ASaveChannelError):c.copy(3)
        self.assertEqual(len(t.sent),before);self.assertEqual(f,['A_IPC_OUTCOME_UNKNOWN'])
    def test_corrupt_third_packet_does_not_deliver(self):
        c,t,f=self.make();self.first_two(c);c.submit(reservation(3));t.fail='bad-third'
        with self.assertRaises(pkt.PacketError):c.copy(3)
        self.assertEqual(c.status()['delivered_generations'],[1,2]);self.assertTrue(t.closed)
    def test_unsupported_fourth_snapshot_holds(self):
        c,t,f=self.make();t.fail='fourth-count'
        with self.assertRaisesRegex(ipc.ASaveChannelError,'snapshot'):c.snapshot()
        self.assertTrue(t.closed);self.assertTrue(f)
    def test_legacy_client_still_rejects_third(self):
        t=NativeTransportDouble();faults=[]
        c=old.ASaveClient(old.Endpoint('\\\\.\\pipe\\san14-a-save-'+'3'*32,23,31,b's'*32),on_fault=faults.append,transport_factory=lambda _:t)
        self.addCleanup(c.close);self.first_two(c)
        with self.assertRaises(old.ASaveChannelError):c.submit(reservation(3))

class NativeWireCase(joint.Cases):
    # Run only the inherited joint happy path, through dedicated Prepare/Plans
    # identity. Frozen Snapshot gap test remains in its own predecessor suite.
    test_direct_predecessor_type_and_snapshot_gaps_are_real=None
    def test_actual_three_control_chain_session_signed_completions(self):
        with patch.object(joint,'control_module',native_control),patch.object(joint,'wire',wire),patch.object(joint,'repeat',repeat):
            super().test_actual_three_control_chain_session_signed_completions()

def main():
    global OUT
    OUT=PRIVATE/'a_save_three_ipc_client_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUT.mkdir(parents=True)
    joint.transport.OUTPUT=OUT;before=joint.chain.pins();before[str(Path(__file__).resolve())]=sha(__file__)
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (ClientCases,NativeWireCase)])
    log=io.StringIO();r=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (OUT/'tests.log').write_text(log.getvalue(),encoding='utf-8')
    after=joint.chain.pins();after[str(Path(__file__).resolve())]=sha(__file__)
    report=dict(result='PASS' if r.wasSuccessful() and before==after else 'FAIL',tests=r.testsRun,sources=after,inputs_unchanged=before==after,
        game_access=False,pipe_transport_double=True,native_save_load_RAM_snapshot_doubles=True,actual_TLS=True,dedicated_native_wire_control=True,
        artifacts={str(p):sha(p) for p in OUT.rglob('*') if p.is_file()})
    p=OUT/'result.json';p.write_text(json.dumps(report,indent=2)+'\n');print(log.getvalue());print(json.dumps(dict(result=report['result'],path=str(p),sha256=sha(p))))
    return int(report['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
