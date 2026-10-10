"""Actual authenticated two-seat TLS + authority/local SQLite; owned sinks only."""
from copy import deepcopy
from datetime import datetime
import hashlib,io,json,secrets,sys,threading,time,unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import reward_result_room as protocol
import reward_result_channel as channel
import reward_result_delta as delta
from reward_result_channel_test import OwnedSink,scope,contexts
from reward_observed_fixture import World
from reward_observed_context import projection
import authority_reward as reward
from room_session import Room
from room_transport import Server,Client,make_certificate

OUTPUT=None
KEY=bytes(range(1,33));REPORT_KEYS={'A':b'A'*32,'B':b'B'*32}


class Harness:
    def __init__(self,folder):
        self.folder=folder;folder.mkdir();self.channels={};self.world=World(12)
        manifest=dict(profile=dict(protocol='san14.room.v1',game_sha256=reward.SUPPORTED_SHA256,
            adapter_contract='research-no-native-room-adapter.v1',checkpoint_sha256='c'*64,rules_sha256='d'*64),
            forces=[dict(id=12,name='Owned A',main_district_id=11),dict(id=2,name='Owned B',main_district_id=2)],source='Owned byte-layout result protocol')
        self.room=Room(manifest);self.endpoint=protocol.ResultEndpoint(self.room)
        cert,key,fingerprint=make_certificate(folder/'tls');self.server=Server(('127.0.0.1',0),self.endpoint,cert,key)
        self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start()
        self.clients={p:Client('127.0.0.1',self.server.server_address[1],fingerprint,
            dict(method=method,credential=token,profile=manifest['profile'])) for p,method,token in
            (('A','host',self.room.host_token),('B','join',self.room.invite))}
        for p,force in (('A',12),('B',2)):
            self.request(p,dict(action='select_force',force_id=force,request_id=secrets.token_hex(16),expected_revision=self.room.revision))
        for p in ('A','B'):self.request(p,dict(action='confirm_force',request_id=secrets.token_hex(16),expected_revision=self.room.revision))
        initial=projection(contexts(self.world));self.scope=scope(initial['date']);self.scope.update(room_id=self.room.room_id,binding_epoch=self.room.binding_epoch)
        self.observed_scope=deepcopy(self.scope)
        self.authority=protocol.ResultAuthority(folder/'authority.sqlite',self.room,self.scope,key=KEY,report_keys=REPORT_KEYS,current_scope=lambda:deepcopy(self.observed_scope))
        self.endpoint.mount(self.authority)
        self.sinks={p:OwnedSink(self.scope,initial) for p in ('A','B')}
        for p in ('A','B'):
            self.channels[p]=channel.ResultChannel(folder/(p+'.sqlite'),self.scope,local_player=p,key=KEY,sink=self.sinks[p],create=True)
    def request(self,p,value):
        r=self.clients[p].request(value)
        if r.get('ok') is not True:raise ValueError(str(r))
        return r
    def send(self,p,action,**fields):return self.request(p,protocol.envelope(self.scope,action,**fields))
    def candidate(self,player,event=None):
        actor=12 if player=='A' else 2;before=contexts(self.world)
        self.world.execute(reward.make_command(before[actor],11 if actor==12 else 2,[97] if actor==12 else [101]))
        after=contexts(self.world);d=delta.infer_delta(before,after)
        self.sinks[player].value=projection(after)  # Already-completed local business double.
        return protocol.submission(self.scope,player,event or secrets.token_hex(16),d,key=KEY)
    def apply_and_ack(self,player,p):
        c=self.channels[player];result=c.record_local_completed(p) if p['body']['player']==player else c.receive(p)
        return self.send(player,'result_ack',receipt=result['receipt'],proof=protocol.ack_proof(REPORT_KEYS[player],result['receipt']))
    def close(self):
        for c in self.clients.values():c.close()
        self.server.shutdown();self.thread.join(5);self.server.server_close()
        assert not self.thread.is_alive()
        for c in self.channels.values():c.close()
        self.authority.close()


class Tests(unittest.TestCase):
    def harness(self):
        h=Harness(OUTPUT/self._testMethodName);self.addCleanup(h.close);return h

    def test_two_seats_same_authority_order_and_no_command_replay(self):
        h=self.harness();rows=[]
        for seq,player in enumerate(('A','B'),1):
            proposal=h.candidate(player);r=h.send(player,'result_submit',proposal=proposal);p=r['packet']
            self.assertEqual(p['body']['sequence'],seq)
            self.assertEqual(h.send(player,'result_submit',proposal=proposal)['packet'],p)
            self.assertEqual(h.send('A','result_poll')['packet'],p);self.assertEqual(h.send('B','result_poll')['packet'],p)
            first=h.apply_and_ack(player,p);self.assertEqual(first['status'],'WAITING_RECEIPTS')
            other='B' if player=='A' else 'A';last=h.apply_and_ack(other,p);self.assertEqual(last['status'],'PAIRED')
            self.assertTrue(h.apply_and_ack(other,p)['duplicate']);self.assertIsNone(h.send(player,'result_poll')['packet'])
            rows.append(dict(sequence=seq,player=player,first=first,last=last))
        self.assertEqual(h.world.calls,2);self.assertEqual([h.sinks[p].calls for p in ('A','B')],[1,1])
        self.assertEqual(h.sinks['A'].value,h.sinks['B'].value);self.assertEqual(h.authority.status()['pending'],0)
        self.assertFalse(h.room.view('A')['native_gameplay_enabled']);self.assertFalse(rows[-1]['last']['room_ready_permission'])
        (h.folder/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

    def test_authenticated_seat_rejects_shared_key_impersonation(self):
        h=self.harness();proposal=h.candidate('A')
        r=h.clients['B'].request(protocol.envelope(h.scope,'result_submit',proposal=proposal))
        self.assertFalse(r['ok']);self.assertTrue(h.authority.status()['held']);self.assertEqual(h.authority.status()['sequence'],0)
        self.assertEqual([s.calls for s in h.sinks.values()],[0,0])

    def test_missing_receipt_blocks_next_result(self):
        h=self.harness();p=h.send('A','result_submit',proposal=h.candidate('A'))['packet'];h.apply_and_ack('A',p)
        with self.assertRaisesRegex(ValueError,'lacks both'):h.send('B','result_submit',proposal=h.candidate('B'))
        self.assertEqual(h.authority.status()['sequence'],1);self.assertEqual(h.authority.status()['pending'],1)
        self.assertTrue(h.authority.status()['held']);self.assertEqual(len(h.authority.db.execute('SELECT * FROM receipts').fetchall()),1)

    def test_disconnect_holds_unresolved_and_refuses_old_connection(self):
        h=self.harness();p=h.send('A','result_submit',proposal=h.candidate('A'))['packet'];old=h.authority.connections['B']
        with self.assertRaises(FileExistsError):
            protocol.ResultAuthority(h.folder/'authority.sqlite',h.room,h.scope,key=KEY,report_keys=REPORT_KEYS,current_scope=lambda:h.scope)
        h.clients['B'].close()
        deadline=time.monotonic()+3
        while h.room.players['B']['connection'] is not None and time.monotonic()<deadline:time.sleep(.01)
        self.assertIsNone(h.room.players['B']['connection']);self.assertTrue(h.authority.status()['held'])
        r=h.endpoint.handle('B',old,protocol.envelope(h.scope,'result_poll'));self.assertFalse(r['ok'])
        self.assertEqual(h.authority.status()['pending'],1)
        with self.assertRaisesRegex(channel.ResultError,'connected'):
            protocol.ResultAuthority(h.folder/'authority.sqlite',h.room,h.scope,key=KEY,report_keys=REPORT_KEYS,current_scope=lambda:h.scope)

    def test_wrong_connection_and_timeline_are_terminal(self):
        h=self.harness()
        r=h.endpoint.handle('A','f'*32,protocol.envelope(h.scope,'result_poll'))
        self.assertFalse(r['ok']);self.assertTrue(h.authority.status()['held']);self.assertEqual(h.authority.status()['sequence'],0)

    def test_live_scope_drift_rejected(self):
        h=self.harness();h.observed_scope['date']=dict(year=203,month=8,day=21,period='下旬')
        with self.assertRaisesRegex(ValueError,'changed'):h.send('A','result_poll')
        self.assertTrue(h.authority.status()['held']);self.assertEqual(h.authority.status()['sequence'],0)

    def test_changed_event_and_wrong_seat_ack_rejected(self):
        h=self.harness();proposal=h.candidate('A');p=h.send('A','result_submit',proposal=proposal)['packet']
        receipt=h.channels['A'].record_local_completed(p)['receipt']
        # A's valid private receipt must not count as B's confirmation.
        with self.assertRaisesRegex(ValueError,'signature'):
            h.send('B','result_ack',receipt=receipt,proof=protocol.ack_proof(REPORT_KEYS['A'],receipt))
        self.assertEqual(h.authority.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],0)
        self.assertTrue(h.authority.status()['held'])

    def test_event_payload_reuse_is_terminal(self):
        h=self.harness();proposal=h.candidate('A');h.send('A','result_submit',proposal=proposal)
        changed=deepcopy(proposal['body']['delta']);changed['after_sha256']='f'*64
        forged=protocol.submission(h.scope,'A',proposal['body']['event_id'],changed,key=KEY)
        with self.assertRaisesRegex(ValueError,'reused'):h.send('A','result_submit',proposal=forged)
        self.assertTrue(h.authority.status()['held']);self.assertEqual(h.authority.status()['sequence'],1)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
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
    OUTPUT=PRIVATE/'reward_result_room_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    pins=sources();stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (OUTPUT/'tests.log').write_text(stream.getvalue(),encoding='utf-8');unchanged=sources()==pins
    result=dict(family='san14.reward-result-room.test.v1',result='PASS' if r.wasSuccessful() and unchanged else 'FAIL',tests=r.testsRun,
        failures=len(r.failures),errors=len(r.errors),sources=pins,inputs_unchanged=unchanged,
        artifacts={str(p.relative_to(OUTPUT)):sha(p) for p in sorted(OUTPUT.rglob('*')) if p.is_file()},
        real_two_seat_tls=True,real_sqlite=True,game_process_access=False,steam_access=False,**channel.CAPABILITIES)
    path=OUTPUT/'result.json';path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(stream.getvalue());print(json.dumps(dict(result=result['result'],path=str(path),sha256=sha(path))))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
