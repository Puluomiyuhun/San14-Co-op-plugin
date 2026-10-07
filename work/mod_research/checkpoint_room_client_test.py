"""Actual TLS idle survival, concurrent reply pairing and lost-reply no replay."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
import socketserver
import threading
import time
import unittest

from checkpoint_room_client import RoomConnection
from checkpoint_room_artifacts import OUT, RoomError
from checkpoint_room_lifecycle import CheckpointRoom
from checkpoint_connected_prototype import TrackingServer
from room_transport import read_packet, write_packet, make_certificate

HERE=Path(__file__).resolve().parent


class ShortIdleHandler(socketserver.StreamRequestHandler):
    def handle(self):
        connection=secrets.token_hex(16);player=None
        self.connection.settimeout(1.7)
        try:
            greeting=self.server.room.authenticate(read_packet(self.rfile),connection)
            player=greeting['player_id'];write_packet(self.wfile,{'ok':True,**greeting})
            while True:
                request=read_packet(self.rfile)
                response=self.server.room.handle(player,connection,request)
                write_packet(self.wfile,response)
        except (EOFError,OSError,RoomError):pass
        finally:
            if player:self.server.room.disconnect(player,connection)


class Owner(CheckpointRoom):
    def __init__(self):
        super().__init__(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')))
        self.mutations=0

    def handle(self,player,connection,request):
        if request.get('action')=='fixture_echo':
            time.sleep(.01)
            return {'ok':True,'echo':request['nonce']}
        if request.get('action')=='fixture_apply_and_drop_reply':
            self.mutations+=1
            raise EOFError('Fixture drops reply after counting request')
        return super().handle(player,connection,request)


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.folder=HERE/'checkpoint_room_client_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        self.folder.mkdir(parents=True)
        self.owner=Owner();cert,key,self.fp=make_certificate(self.folder/'tls')
        self.server=TrackingServer(('127.0.0.1',0),self.owner,cert,key)
        self.server.RequestHandlerClass=ShortIdleHandler
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.02},daemon=True)
        self.thread.start();self.client=None

    def connect(self):
        self.client=RoomConnection('127.0.0.1',self.server.server_address[1],self.fp,
            dict(method='host',credential=self.owner.host_token,profile=self.owner.manifest['profile']),heartbeat_seconds=1)
        return self.client

    def tearDown(self):
        if self.client:
            self.assertTrue(self.client.close()['closed'])
            self.assertFalse(self.client._thread.is_alive())
        self.server.shutdown();self.thread.join(timeout=5)
        self.assertTrue(self.server.wait_handlers());self.server.server_close()

    def test_idle_beyond_server_timeout_survives_without_player_commands(self):
        c=self.connect();time.sleep(2.35)
        state=c.status()
        self.assertTrue(state['transport_open'])
        self.assertGreaterEqual(state['heartbeat_count'],2)
        self.assertTrue(c.request({'action':'status'})['ok'])
        self.assertNotIn(self.owner.host_token,json.dumps(state))

    def test_concurrent_calls_keep_each_reply_paired_and_heartbeat_stops_on_close(self):
        c=self.connect();time.sleep(1.1)
        errors=[];pairs=[]
        def work(worker):
            try:
                for i in range(10):
                    value=f'{worker}:{i}'
                    reply=c.request({'action':'fixture_echo','nonce':value})
                    pairs.append((value,reply['echo']))
            except BaseException as exc:errors.append(type(exc).__name__)
        threads=[threading.Thread(target=work,args=(i,)) for i in range(3)]
        for t in threads:t.start()
        for t in threads:t.join(timeout=5)
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(errors,[]);self.assertEqual(len(pairs),30)
        self.assertTrue(all(a==b for a,b in pairs))
        self.assertGreaterEqual(c.status()['heartbeat_count'],1)
        self.assertTrue(c.close()['closed'])
        with self.assertRaises(RoomError):c.request({'action':'status'})

    def test_lost_reply_latches_uncertainty_and_never_replays_request(self):
        c=self.connect()
        with self.assertRaises(EOFError):c.request({'action':'fixture_apply_and_drop_reply'})
        self.assertEqual(self.owner.mutations,1)
        with self.assertRaises(RoomError):c.request({'action':'fixture_apply_and_drop_reply'})
        self.assertEqual(self.owner.mutations,1)
        state=c.status()
        self.assertFalse(state['transport_open'])
        self.assertTrue(state['fault']['request_may_have_been_sent'])
        self.assertFalse(state['fault']['automatically_retried'])
        self.assertFalse(state['automatic_reconnect'])

    def test_close_error_stops_heartbeat_but_does_not_claim_transport_closed(self):
        c=self.connect();original=c._client.close;calls=[]
        def fail_once():
            calls.append(1)
            if len(calls)==1:raise OSError('Fixture close failure')
            original()
        c._client.close=fail_once
        with self.assertRaises(OSError):c.close()
        self.assertFalse(c._thread.is_alive())
        self.assertFalse(c.status()['transport_open'])
        self.assertFalse(c.status()['closed'])
        self.assertEqual(c.status()['close_error'],'OSError')
        with self.assertRaises(RoomError):c.request({'action':'status'})
        self.assertTrue(c.close()['closed'])
        self.assertIsNone(c.status()['close_error'])
        self.assertEqual(len(calls),2)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ConnectionTests))
    folder=HERE/'checkpoint_room_client_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    data=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),game_access=False,
        scope='ACTUAL_LOOPBACK_TLS_SHORT_IDLE_DEADLINE',
        source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in
            ('checkpoint_room_client.py','checkpoint_room_client_test.py')})
    (folder/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(folder/'result.json')
    raise SystemExit(0 if result.wasSuccessful() else 1)
