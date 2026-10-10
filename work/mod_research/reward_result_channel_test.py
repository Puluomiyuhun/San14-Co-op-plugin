"""Owned projections + real loopback TLS/SQLite; no native game sink exists."""
from copy import deepcopy
from datetime import datetime
import hashlib,hmac,io,json,socket,socketserver,ssl,sys,threading,unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import reward_result_channel as channel
import reward_result_delta as delta
from reward_observed_fixture import World
from reward_observed_context import projection,CONTRACT,validate_effect
import authority_reward as reward
import room_transport as transport

OUTPUT=None
KEY=bytes(range(1,33))  # Owned fixture only; no production key input/output.


def contexts(w):return {f:reward.capture_context(w.reader,f) for f in (12,2)}


def candidate(actor=12):
    w=World(12);before=contexts(w)
    command=reward.make_command(before[actor],11 if actor==12 else 2,[97] if actor==12 else [101])
    w.execute(command);after=contexts(w)
    return projection(before),projection(after),delta.infer_delta(before,after)


def scope(node):
    return dict(schema=channel.SCOPE,room_id='1'*32,binding_epoch='2'*32,timeline_epoch='3'*32,
        attachments={'A':'a'*32,'B':'b'*32},actors={'A':dict(force_id=12,main_district_id=11),
        'B':dict(force_id=2,main_district_id=2)},date=deepcopy(node),projection_contract=CONTRACT)


class OwnedSink(channel.LocalResultSink):
    def __init__(self,s,p):super().__init__();self.scope=deepcopy(s);self.value=deepcopy(p);self.calls=0;self.fail_after=False
    def current_scope(self):return deepcopy(self.scope)
    def snapshot(self):return deepcopy(self.value)
    def apply_atomic(self,before,after):
        if self.value!=before:raise ValueError('Owned full compare-before differs')
        self.calls+=1;self.value=deepcopy(after)
        if self.fail_after:raise OSError('Owned result lost after atomic replacement')


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        while True:
            try:p=transport.read_packet(self.rfile)
            except (EOFError,OSError):return
            try:answer=dict(ok=True,**self.server.channel.receive(p))
            except Exception as exc:answer=dict(ok=False,error=type(exc).__name__)
            transport.write_packet(self.wfile,answer)


class Server(socketserver.TCPServer):
    allow_reuse_address=False
    def __init__(self,c,folder):
        cert,key,self.fingerprint=transport.make_certificate(folder)
        self.context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);self.context.minimum_version=ssl.TLSVersion.TLSv1_2
        self.context.load_cert_chain(cert,key);self.channel=c
        super().__init__(('127.0.0.1',0),Handler)
    def get_request(self):
        sock,address=super().get_request();sock.settimeout(5)
        try:return self.context.wrap_socket(sock,server_side=True),address
        except BaseException:sock.close();raise


class Tests(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir();self.channels=[]
    def tearDown(self):
        for c in self.channels:c.close()
    def make(self,before,name='receiver',s=None,create=True,local_player='B'):
        s=s or scope(before['date']);sink=OwnedSink(s,before)
        c=channel.ResultChannel(self.folder/(name+'.sqlite'),s,local_player=local_player,key=KEY,sink=sink,create=create)
        self.channels.append(c);return c,sink
    def signed(self,d,actor='A',event='4'*32,seq=1,s=None):
        return channel.packet(s or scope(d['date']),actor,event,seq,d,key=KEY)
    def assert_held(self,c,sink,calls=0):
        self.assertTrue(c.status()['held']);self.assertEqual(sink.calls,calls)

    def test_real_tls_source_registration_receive_and_durable_duplicate(self):
        before,after,d=candidate();s=scope(d['date']);p=self.signed(d)
        source,local=self.make(after,'source',s,local_player='A');receiver,remote=self.make(before,'receiver',s)
        a=source.record_local_completed(p);self.assertEqual(local.calls,0);self.assertFalse(a['sink_invoked'])
        server=Server(receiver,self.folder/'tls');thread=threading.Thread(target=server.serve_forever);thread.start()
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);context.check_hostname=False;context.verify_mode=ssl.CERT_NONE
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        try:
            with socket.create_connection(server.server_address,timeout=5) as raw:
                with context.wrap_socket(raw,server_hostname='127.0.0.1') as sock:
                    self.assertEqual(hashlib.sha256(sock.getpeercert(binary_form=True)).hexdigest(),server.fingerprint)
                    with sock.makefile('rwb') as stream:
                        transport.write_packet(stream,p);first=transport.read_packet(stream)
                        transport.write_packet(stream,p);second=transport.read_packet(stream)
        finally:server.shutdown();server.server_close();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertTrue(first['ok']);self.assertFalse(first['duplicate'])
        self.assertTrue(second['duplicate']);self.assertEqual(remote.value,after);self.assertEqual(remote.calls,1)
        self.assertFalse(first['full_reward_effects_verified']);self.assertFalse(first['room_ready_permission'])
        receiver.close();reopened,sink=self.make(after,'receiver',s,False)
        self.assertTrue(reopened.receive(p)['duplicate']);self.assertEqual(sink.calls,0)
        (self.folder/'results.json').write_text(json.dumps(dict(source=a,first=first,duplicate=second),indent=2),encoding='utf-8')
        self.assertNotIn(KEY,(self.folder/'receiver.sqlite').read_bytes())

    def test_both_authorized_actors(self):
        for actor,player in ((12,'A'),(2,'B')):
            before,after,d=candidate(actor);c,sink=self.make(before,player,local_player='B' if player=='A' else 'A')
            c.receive(self.signed(d,player));self.assertEqual(sink.value,after);self.assertEqual(sink.calls,1)

    def test_signature_actor_date_and_attachment_refuse_before_apply(self):
        before,after,d=candidate()
        for fault in ('signature','actor','date','attachment','remote-pointer'):
            with self.subTest(fault=fault):
                c,sink=self.make(before,fault);p=self.signed(d)
                if fault=='signature':p['proof']='0'*64
                elif fault=='attachment':sink.scope['attachments']['B']='c'*32
                else:
                    if fault=='actor':p['body']['player']='B'
                    elif fault=='date':p['body']['date']['day']=21
                    else:p['body']['delta']['pointer']=0x140001000
                    p['proof']=hmac.new(KEY,channel.DOMAIN+channel.canonical(p['body']),hashlib.sha256).hexdigest()
                with self.assertRaises((ValueError,KeyError)):c.receive(p)
                self.assert_held(c,sink);self.assertEqual(sink.value,before);self.assertEqual(c.status()['events'],0)

    def test_compare_before_all_or_nothing(self):
        before,after,d=candidate();c,sink=self.make(before);sink.value['cities'][0]['food']-=1;original=deepcopy(sink.value)
        with self.assertRaises(ValueError):c.receive(self.signed(d))
        self.assert_held(c,sink);self.assertEqual(original,sink.value);self.assertEqual(c.status()['events'],0)

    def test_unknown_after_write_is_terminal_across_reopen(self):
        before,after,d=candidate();c,sink=self.make(before);p=self.signed(d);sink.fail_after=True
        with self.assertRaises(OSError):c.receive(p)
        self.assert_held(c,sink,1);self.assertEqual(sink.value,after);self.assertEqual(c.status()['pending'],1)
        with self.assertRaises(ValueError):c.receive(p)
        c.close();again,new_sink=self.make(after,create=False)
        with self.assertRaises(channel.ResultHeld):again.receive(p)
        self.assertEqual(new_sink.calls,0);self.assertEqual(sink.calls,1)

    def test_intent_and_result_persistence_failures_do_not_replay(self):
        before,after,d=candidate();p=self.signed(d)
        for stage,calls in (('_reserve',0),('_persist_result',1)):
            with self.subTest(stage=stage):
                c,sink=self.make(before,stage)
                with patch.object(c,stage,side_effect=OSError('owned disk failure')):
                    with self.assertRaises(OSError):c.receive(p)
                self.assert_held(c,sink,calls)
                c.close();again,new_sink=self.make(sink.value,stage,create=False)
                with self.assertRaises(channel.ResultHeld):again.receive(p)
                self.assertEqual(new_sink.calls,0)

    def test_repeated_identity_sequence_and_local_mismatch_refuse(self):
        before,after,d=candidate()
        for fault in ('event-reused','sequence-reused','local-before'):
            c,sink=self.make(before,fault,local_player='A' if fault=='local-before' else 'B');p=self.signed(d)
            if fault=='local-before':
                with self.assertRaises(ValueError):c.record_local_completed(p)
                self.assert_held(c,sink);continue
            c.receive(p)
            if fault=='event-reused':p=self.signed(d,seq=2)
            else:p=self.signed(d,event='5'*32)
            with self.assertRaises(ValueError):c.receive(p)
            self.assert_held(c,sink,1)

    def test_large_local_projection_does_not_use_wire_limit(self):
        before,after,d=candidate()
        for ident in range(1100,1700):
            row=deepcopy(before['persons'][0]);row['id']=ident
            before['persons'].append(deepcopy(row));after['persons'].append(deepcopy(row))
        d['before_sha256']=delta.journal.digest(before);d['after_sha256']=delta.journal.digest(after)
        d['effects']=validate_effect(before,after,d['command'],dict(expected_costs=d['effects']['costs']))
        self.assertGreater(len(delta.journal.canonical(after).encode()),channel.MAX_PACKET)
        p=self.signed(d);self.assertLess(len(channel.canonical(p)),channel.MAX_PACKET)
        c,sink=self.make(after,'local',local_player='A');result=c.record_local_completed(p)
        self.assertEqual(sink.calls,0);self.assertEqual(result['receipt']['after_sha256'],d['after_sha256'])
        remote,other=self.make(before);remote.receive(p);self.assertEqual(other.value,after);self.assertEqual(other.calls,1)

    def test_local_seat_direction_and_reopen_binding(self):
        before,after,d=candidate();p=self.signed(d)
        for method,state,seat in (('receive',before,'A'),('record_local_completed',after,'B')):
            c,sink=self.make(state,method,local_player=seat)
            with self.assertRaises(channel.ResultError):getattr(c,method)(p)
            self.assert_held(c,sink);self.assertEqual(c.status()['events'],0)
        c,sink=self.make(after,'bound',local_player='A');c.record_local_completed(p);c.close()
        with self.assertRaisesRegex(channel.ResultError,'local seat'):
            channel.ResultChannel(self.folder/'bound.sqlite',scope(d['date']),local_player='B',key=KEY,sink=sink)
        reopened,sink=self.make(after,'bound',local_player='A',create=False)
        self.assertTrue(reopened.record_local_completed(p)['duplicate']);self.assertEqual(sink.calls,0)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sources():
    paths={Path(__file__).resolve()}
    for m in list(sys.modules.values()):
        f=getattr(m,'__file__',None)
        if f:
            p=Path(f).resolve()
            if p.suffix=='.py' and ROOT in p.parents:paths.add(p)
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}


def main():
    global OUTPUT
    OUTPUT=PRIVATE/'reward_result_channel_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    # Preload certificate dependencies before fixing the source closure.
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    pins=sources();stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (OUTPUT/'tests.log').write_text(stream.getvalue(),encoding='utf-8')
    unchanged=sources()==pins
    artifacts={str(p.relative_to(OUTPUT)):sha(p) for p in sorted(OUTPUT.rglob('*')) if p.is_file()}
    report=dict(family='san14.reward-result-channel.test.v1',result='PASS' if result.wasSuccessful() and unchanged else 'FAIL',tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),sources=pins,artifacts=artifacts,inputs_unchanged=unchanged,
        real_loopback_tls=True,real_sqlite=True,sink='owned dict atomic replacement',game_process_access=False,
        steam_access=False,**channel.CAPABILITIES)
    path=OUTPUT/'result.json';path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(stream.getvalue());print(json.dumps(dict(result=report['result'],path=str(path),sha256=sha(path))))
    return 0 if report['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
