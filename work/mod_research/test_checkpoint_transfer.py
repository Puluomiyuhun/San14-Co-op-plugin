"""Adversarial framing/integrity tests for bounded checkpoint pipelining."""
from pathlib import Path
import sys,json,unittest,base64
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parents[1]/'outputs/san14-link'),str(HERE)]
from authoritative_sync import CheckpointReceiver,CheckpointPackage,canonical,digest,SyncError,scope_from_room
from checkpoint_transfer import receive_checkpoint
from test_authoritative_sync import bound_room


class Stream:
    def __init__(self,replies):self.replies=iter(replies);self.sent=[];self.closed=False
    def write(self,data):
        if self.closed:raise OSError('closed')
        self.sent.append(json.loads(data));return len(data)
    def flush(self):pass
    def readline(self,n):
        if self.closed:raise OSError('closed')
        return next(self.replies,b'')[:n]


class Peer:
    def __init__(self,replies):self.stream=Stream(replies);self.closed=False
    def close(self):self.closed=True;self.stream.closed=True


def fixture():
    s=scope_from_room(bound_room());cut={'sequence':0,'prefix_sha256':digest(s)};epoch='a'*32
    parts={'world.s14':bytes(range(251))*1045,'adapter.json':b'{"fixture":true}'}
    p=CheckpointPackage(s,epoch,1,cut,{'year':203,'month':8,'day':21,'phase':'PLANNING_BOUNDARY'},
        'fixture.v1','b'*64,parts,source_player='A')
    r=CheckpointReceiver(p.manifest,p.checkpoint_id,s,epoch,1,cut)
    r.fixture_scope=s
    chunks=list(p.chunks());replies=[canonical({'ok':True,'chunk':c})+b'\n' for c in chunks]
    return p,r,parts,chunks,replies


class Tests(unittest.TestCase):
    def test_pipeline_integrity(self):
        p,r,parts,chunks,replies=fixture();peer=Peer(replies);progress=[]
        got=receive_checkpoint(peer,r,action='test_checkpoint_chunk',progress=progress.append)
        self.assertEqual(got['parts'],parts);self.assertFalse(got['native_loaded']);self.assertTrue(peer.closed)
        self.assertEqual(got['request_windows'],3);self.assertEqual(progress[-1]['received'],sum(map(len,parts.values())))
    def test_out_of_order_within_windows(self):
        p,r,parts,chunks,replies=fixture();replies=[v for i in range(0,len(replies),4) for v in reversed(replies[i:i+4])]
        self.assertEqual(receive_checkpoint(Peer(replies),r,action='x')['parts'],parts)
    def test_exact_reconnect_retries(self):
        p,r,parts,chunks,replies=fixture()
        for c in chunks[:4]:r.accept(c)
        self.assertEqual(receive_checkpoint(Peer(replies),r,action='x')['parts'],parts)
    def test_duplicate_response_closes(self):
        p,r,parts,chunks,replies=fixture();replies[1]=replies[0];peer=Peer(replies)
        with self.assertRaises(SyncError):receive_checkpoint(peer,r,action='x')
        self.assertTrue(peer.closed)
    def test_unrequested_window_chunk(self):
        p,r,parts,chunks,replies=fixture();replies[0]=replies[-1];peer=Peer(replies)
        with self.assertRaises(SyncError):receive_checkpoint(peer,r,action='x')
        self.assertTrue(peer.closed)
    def test_eof_mid_window_closes(self):
        p,r,parts,chunks,replies=fixture();peer=Peer(replies[:2])
        with self.assertRaises(EOFError):receive_checkpoint(peer,r,action='x')
        self.assertTrue(peer.closed)
    def test_wrong_checkpoint_closes(self):
        p,r,parts,chunks,replies=fixture();chunks[0]['checkpoint_id']='0'*64
        replies[0]=canonical({'ok':True,'chunk':chunks[0]})+b'\n';peer=Peer(replies)
        with self.assertRaises(SyncError):receive_checkpoint(peer,r,action='x')
        self.assertTrue(peer.closed)
    def test_corrupt_complete_payload_closes(self):
        p,r,parts,chunks,replies=fixture();raw=bytearray(base64.b64decode(chunks[0]['data']));raw[0]^=1
        chunks[0]['data']=base64.b64encode(raw).decode();replies[0]=canonical({'ok':True,'chunk':chunks[0]})+b'\n';peer=Peer(replies)
        with self.assertRaises(SyncError):receive_checkpoint(peer,r,action='x')
        self.assertTrue(peer.closed)
    def test_denied_endpoint_closes(self):
        p,r,parts,chunks,replies=fixture();peer=Peer([b'{"ok":false,"error":"denied"}\n'])
        with self.assertRaises(SyncError):receive_checkpoint(peer,r,action='x')
        self.assertTrue(peer.closed)
    def test_oversized_reply_closes(self):
        p,r,parts,chunks,replies=fixture();peer=Peer([b' '*70000+b'\n'])
        with self.assertRaises(ValueError):receive_checkpoint(peer,r,action='x')
        self.assertTrue(peer.closed)
    def test_invalid_window_before_send(self):
        for window in (0,9,True,4.0):
            p,r,parts,chunks,replies=fixture();peer=Peer(replies)
            with self.assertRaises(SyncError):receive_checkpoint(peer,r,action='x',window=window)
            self.assertEqual(peer.stream.sent,[])
    def test_progress_error_closes(self):
        p,r,parts,chunks,replies=fixture();peer=Peer(replies)
        def fail(_):raise RuntimeError('UI callback')
        with self.assertRaises(RuntimeError):receive_checkpoint(peer,r,action='x',progress=fail)
        self.assertTrue(peer.closed)
    def test_cancellation_closes(self):
        p,r,parts,chunks,replies=fixture();peer=Peer(replies)
        def cancel(_):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):receive_checkpoint(peer,r,action='x',progress=cancel)
        self.assertTrue(peer.closed)
    def test_extra_tail_cannot_pollute_a_later_request(self):
        p,r,parts,chunks,replies=fixture();peer=Peer(replies+[replies[-1]])
        self.assertEqual(receive_checkpoint(peer,r,action='x')['parts'],parts)
        self.assertTrue(peer.closed)
        with self.assertRaises(OSError):peer.stream.readline(65537)
    def test_corrupt_receiver_needs_fresh_pinned_instance(self):
        p,r,parts,chunks,replies=fixture();bad=dict(chunks[0]);raw=bytearray(base64.b64decode(bad['data']));raw[0]^=1
        bad['data']=base64.b64encode(raw).decode()
        corrupted=[canonical({'ok':True,'chunk':bad})+b'\n']+replies[1:]
        with self.assertRaises(SyncError):receive_checkpoint(Peer(corrupted),r,action='x')
        with self.assertRaises(SyncError):receive_checkpoint(Peer(replies),r,action='x')
        # The replacement receiver pins the exact same checkpoint, not a new
        # manifest supplied in response to the corruption.
        fresh=CheckpointReceiver(p.manifest,p.checkpoint_id,r.fixture_scope,p.manifest['epoch'],1,p.manifest['cut'])
        self.assertEqual(receive_checkpoint(Peer(replies),fresh,action='x')['parts'],parts)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (HERE/'checkpoint-transfer-tests.json').write_text(json.dumps({'result':'PASS' if result.wasSuccessful() else 'FAIL',
        'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'native_loaded':False},indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
