"""Two-period MODEL receipts and real loopback TLS; no native world claims."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
import tempfile
import threading
import unittest

from checkpoint_room_lifecycle import CheckpointRoom, RoomError, SyncError
from checkpoint_room_artifacts import OUT
from authoritative_sync import PeriodCoordinator, CheckpointPackage, CheckpointReceiver, scope_from_room, next_node
from checkpoint_transfer import receive_checkpoint
from room_transport import Client, make_certificate
from checkpoint_room_client import RoomConnection
from checkpoint_connected_prototype import TrackingServer

HERE=Path(__file__).resolve().parent


def select_room(room):
    room.authenticate(dict(method='host',credential=room.host_token,profile=room.manifest['profile']),'a')
    room.authenticate(dict(method='join',credential=room.invite,profile=room.manifest['profile']),'b')
    for p,c,f in (('A','a',12),('B','b',2)):
        assert room.handle(p,c,dict(action='select_force',force_id=f,request_id=secrets.token_hex(16),
                                   expected_revision=room.revision))['ok']
    for p,c in (('A','a'),('B','b')):
        assert room.handle(p,c,dict(action='confirm_force',request_id=secrets.token_hex(16),
                                   expected_revision=room.revision))['ok']


def coordinator_for(room):
    c=PeriodCoordinator(scope_from_room(room),'synthetic-multiperiod-model.v1','a'*64,
        {'A':'a'*32,'B':'b'*32},dict(year=203,month=8,day=1,phase='PLANNING_BOUNDARY'))
    if room._coordinator is None:room.bind_coordinator(c)
    return c


def offer(c, *, ready_from_network=False):
    if not ready_from_network:
        for p in ('A','B'):c.set_ready(p,c.epoch,True)
    c.begin_simulation(c.seal_inputs())
    cut={k:c.seal[k] for k in ('sequence','prefix_sha256')}
    parts={'world.s14':(b'SYNTHETIC_WORLD_PERIOD_'+str(c.period).encode())*10000,
           'adapter.json':b'{"synthetic_fixture_only":true}'}
    package=CheckpointPackage(c.scope,c.epoch,c.period,cut,next_node(c.node),c.state_contract,
        hashlib.sha256(parts['world.s14']).hexdigest(),parts,source_player='A')
    c.offer_checkpoint('A',package.manifest)
    return package


def receiver_for(c,package):
    return CheckpointReceiver(package.manifest,package.checkpoint_id,c.scope,c.epoch,c.period,package.manifest['cut'])


def complete_model(c,package,receiver=None):
    # Explicit simulated trusted observations. Not called by production owner.
    if receiver is None:
        receiver=receiver_for(c,package)
        for chunk in package.chunks():receiver.accept(chunk)
    c.received('B',c.epoch,receiver)
    intent=c.begin_guest_load('B',c.epoch)
    c.loaded('B',c.epoch,package.checkpoint_id,intent,package.manifest['world_sha256'],2,
        secrets.token_hex(16),dict(attachment=c.attachments['A'],
            world_sha256=package.manifest['world_sha256'],node=package.manifest['node']))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.room=CheckpointRoom(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')))
        select_room(self.room);self.c=coordinator_for(self.room);self.p=offer(self.c)
        self.service=self.room.install_offered_checkpoint(self.c,self.p)

    def ticket(self,package=None):
        return self.room.handle('B','b',dict(action='checkpoint_download_offer',
            checkpoint_id=(package or self.p).checkpoint_id))

    def authenticate(self,token,connection):
        return self.room.download_endpoint.authenticate(dict(method='checkpoint_download',credential=token,
            profile=self.room.manifest['profile']),connection)

    def request_chunk(self,package,connection):
        chunk=next(package.chunks())
        return self.room.download_endpoint.handle('B',connection,dict(action='checkpoint_chunk',
            **{k:chunk[k] for k in ('checkpoint_id','part','index')}))

    def test_rotation_requires_completed_prior_receipt(self):
        future=CheckpointPackage(self.c.scope,secrets.token_hex(16),2,self.p.manifest['cut'],
            next_node(self.p.manifest['node']),self.c.state_contract,'b'*64,
            {'world.s14':b'future','adapter.json':b'{}'},source_player='A')
        with self.assertRaises(RoomError):self.room.install_offered_checkpoint(self.c,future)
        self.assertIs(self.room.artifacts,self.service)
        self.assertFalse(self.service.closed)

    def test_same_publication_does_not_reset_quota_or_retire_connection(self):
        token=self.ticket()['download_token'];self.authenticate(token,'first')
        self.assertIs(self.room.install_offered_checkpoint(self.c,self.p),self.service)
        self.assertEqual(self.service.ticket_count,1)
        self.assertTrue(self.request_chunk(self.p,'first')['ok'])
        self.assertEqual(self.room.checkpoint_status()['generation'],1)

    def test_new_generation_revokes_old_tickets_connections_and_checkpoint_requests(self):
        unused=self.ticket()['download_token']
        self.authenticate(self.ticket()['download_token'],'old-download')
        complete_model(self.c,self.p);new=offer(self.c)
        self.assertFalse(self.room.checkpoint_status()['download_available'])
        self.room.install_offered_checkpoint(self.c,new)
        self.assertTrue(self.room.checkpoint_status()['download_available'])
        self.assertTrue(self.service.closed)
        self.assertFalse(self.ticket()['ok'])
        self.assertFalse(self.request_chunk(new,'old-download')['ok'])
        with self.assertRaises(RoomError):self.authenticate(unused,'late')
        self.authenticate(self.ticket(new)['download_token'],'new-download')
        self.assertTrue(self.request_chunk(new,'new-download')['ok'])
        self.assertFalse(self.request_chunk(self.p,'new-download')['ok'])
        self.assertEqual(self.room.download_endpoint.status()['active_connection_owners'],1)

    def test_bad_new_bytes_leave_previous_owner_and_generation_untouched(self):
        complete_model(self.c,self.p);new=offer(self.c)
        new._parts['world.s14']=b'bad'
        with self.assertRaises(SyncError):self.room.install_offered_checkpoint(self.c,new)
        self.assertIs(self.room.artifacts,self.service)
        self.assertFalse(self.service.closed)
        self.assertEqual(self.room.checkpoint_status()['generation'],1)

    def test_disconnect_holds_coordinator_and_resume_does_not_restore_download_authority(self):
        self.authenticate(self.ticket()['download_token'],'download')
        self.room.disconnect('B','wrong-connection')
        self.assertEqual(self.c.connected,{'A','B'})
        self.room.disconnect('B','b')
        self.assertEqual(self.c.connected,{'A'})
        self.assertFalse(self.request_chunk(self.p,'download')['ok'])
        self.room.authenticate(dict(method='resume',credential=self.room.players['B']['token'],
            profile=self.room.manifest['profile']),'b2')
        reply=self.room.handle('B','b2',dict(action='checkpoint_download_offer',checkpoint_id=self.p.checkpoint_id))
        self.assertFalse(reply['ok'])
        self.assertEqual(self.room.checkpoint_status()['held_reason'],'CONTROL_CONNECTION_CHANGED')
        with self.assertRaises(RoomError):self.room.install_offered_checkpoint(self.c,self.p)

    def test_artifact_disconnect_does_not_hold_room(self):
        self.authenticate(self.ticket()['download_token'],'download')
        self.room.download_endpoint.disconnect('B','download')
        self.assertIsNone(self.room.checkpoint_status()['held_reason'])
        self.assertEqual(self.c.connected,{'A','B'})

    def test_coordinator_replacement_and_skipped_period_refused(self):
        other=coordinator_for(self.room);p=offer(other)
        with self.assertRaises(RoomError):self.room.install_offered_checkpoint(other,p)
        complete_model(self.c,self.p);self.c.period+=1;p=offer(self.c)
        with self.assertRaises(RoomError):self.room.install_offered_checkpoint(self.c,p)

    def test_receipt_attachment_and_scope_lineage_required(self):
        complete_model(self.c,self.p);new=offer(self.c)
        self.c.attachments['A']='e'*32
        with self.assertRaises(RoomError):self.room.install_offered_checkpoint(self.c,new)

    def test_status_is_authenticated_and_cannot_forge_loaded_or_publish(self):
        self.assertFalse(self.room.handle('B','foreign',{'action':'checkpoint_status'})['ok'])
        for action in ('checkpoint_loaded','publish_checkpoint','start_game'):
            self.assertFalse(self.room.handle('B','b',{'action':action})['ok'])
        reply=self.room.handle('B','b',{'action':'checkpoint_status'})
        self.assertEqual(reply['checkpoint']['period'],1)
        self.assertFalse(reply['checkpoint']['native_gameplay_enabled'])
        self.room.close_checkpoints()
        self.assertFalse(self.ticket()['ok'])

    def test_expired_router_connections_do_not_consume_new_capacity(self):
        now=[1.0];self.service.clock=lambda:now[0]
        for i in range(8):self.authenticate(self.ticket()['download_token'],'old'+str(i))
        now[0]=40
        self.authenticate(self.ticket()['download_token'],'fresh')
        self.assertEqual(self.room.download_endpoint.status()['active_connection_owners'],1)
        self.assertFalse(self.request_chunk(self.p,'old0')['ok'])
        self.assertTrue(self.request_chunk(self.p,'fresh')['ok'])

    def test_pre_first_checkpoint_disconnect_is_observed_and_cannot_be_auto_recovered(self):
        room=CheckpointRoom(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')))
        select_room(room);c=coordinator_for(room)
        room.disconnect('B','b')
        self.assertEqual(c.connected,{'A'})
        self.assertEqual(room.checkpoint_status()['held_reason'],'CONTROL_CONNECTION_CHANGED')
        room.authenticate(dict(method='resume',credential=room.players['B']['token'],
            profile=room.manifest['profile']),'replacement')
        with self.assertRaises(SyncError):c.set_ready('A',c.epoch,True)
        with self.assertRaises(RoomError):room.bind_coordinator(c)

    def test_ready_is_bound_to_authenticated_player_current_epoch_and_pending_commands(self):
        room=CheckpointRoom(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')))
        select_room(room);c=coordinator_for(room)
        req=dict(action='period_ready',epoch=c.epoch,ready=True)
        self.assertFalse(room.handle('B','foreign',req)['ok'])
        self.assertFalse(room.handle('B','b',{**req,'player':'A'})['ok'])
        self.assertFalse(room.handle('B','b',{**req,'epoch':'f'*32})['ok'])
        c.set_pending('B',c.epoch,{'e'*32})
        self.assertFalse(room.handle('B','b',req)['ok'])
        c.set_pending('B',c.epoch,set())
        self.assertEqual(room.handle('B','b',req)['ready'],['B'])
        self.assertEqual(room.handle('B','b',req)['ready'],['B'])
        self.assertEqual(room.handle('A','a',req)['ready'],['A','B'])
        self.assertEqual(c.phase,'PLANNING')
        self.assertEqual(room.handle('B','b',{**req,'ready':False})['ready'],['A'])

    def test_closing_revokes_readiness_and_already_sealed_simulation_permission(self):
        for sealed in (False,True):
            room=CheckpointRoom(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')))
            select_room(room);c=coordinator_for(room)
            for p in ('A','B'):c.set_ready(p,c.epoch,True)
            permit=c.seal_inputs() if sealed else None
            room.close_checkpoints()
            self.assertEqual(c.ready,set())
            self.assertEqual(c.connected,set())
            with self.assertRaises(SyncError):
                c.begin_simulation(permit) if sealed else c.seal_inputs()

    def test_initial_publication_cannot_skip_bound_period_or_replace_native_attachment(self):
        for skip in (False,True):
            room=CheckpointRoom(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')))
            select_room(room);c=coordinator_for(room)
            package=offer(c)
            if skip:
                complete_model(c,package)
                package=offer(c)
            else:c.attachments['A']='e'*32
            with self.assertRaises(RoomError):room.install_offered_checkpoint(c,package)
            self.assertIsNone(room.artifacts)
            self.assertEqual(room.checkpoint_status()['generation'],0)


class NetworkTests(unittest.TestCase):
    def test_same_two_control_connections_and_download_listener_across_two_model_periods(self):
        folder=HERE/'checkpoint_room_lifecycle_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        folder.mkdir(parents=True)
        room=CheckpointRoom(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')))
        cert,key,fp=make_certificate(folder/'tls');servers=[];clients=[];evidence=[]
        def server(owner):
            s=TrackingServer(('127.0.0.1',0),owner,cert,key)
            t=threading.Thread(target=s.serve_forever,kwargs={'poll_interval':.02},daemon=True)
            servers.append((s,t));t.start();return s.server_address[1]
        def client(port,method,credential):
            kind=Client if method=='checkpoint_download' else RoomConnection
            c=kind('127.0.0.1',port,fp,dict(method=method,credential=credential,profile=room.manifest['profile']))
            clients.append(c);return c
        try:
            control_port=server(room);download_port=server(room.download_endpoint)
            a=client(control_port,'host',room.host_token);b=client(control_port,'join',room.invite)
            for cl,f in ((a,12),(b,2)):
                self.assertTrue(cl.request(dict(action='select_force',force_id=f,
                    request_id=secrets.token_hex(16),expected_revision=room.revision))['ok'])
            for cl in (a,b):
                self.assertTrue(cl.request(dict(action='confirm_force',request_id=secrets.token_hex(16),
                    expected_revision=room.revision))['ok'])
            original={p:r['connection'] for p,r in room.players.items()}
            c=coordinator_for(room);old_download=None;old_package=None
            for period in (1,2):
                for cl in (a,b):
                    self.assertTrue(cl.request(dict(action='period_ready',epoch=c.epoch,ready=True))['ok'])
                self.assertEqual(c.phase,'PLANNING')
                package=offer(c,ready_from_network=True);room.install_offered_checkpoint(c,package)
                if old_download:
                    chunk=next(old_package.chunks())
                    reply=old_download.request(dict(action='checkpoint_chunk',
                        **{k:chunk[k] for k in ('checkpoint_id','part','index')}))
                    self.assertFalse(reply['ok'])
                status=b.request({'action':'checkpoint_status'})['checkpoint']
                self.assertEqual(status['period'],period)
                ticket=b.request(dict(action='checkpoint_download_offer',checkpoint_id=status['checkpoint_id']))
                download=client(download_port,'checkpoint_download',ticket['download_token'])
                receiver=receiver_for(c,package)
                transfer=receive_checkpoint(download,receiver,action='checkpoint_chunk')
                self.assertEqual(transfer['parts'],package._parts)
                self.assertEqual({p:r['connection'] for p,r in room.players.items()},original)
                for cl in (a,b):self.assertTrue(cl.request({'action':'status'})['ok'])
                # Leave one stream open to prove retirement denies the next generation.
                ticket=b.request(dict(action='checkpoint_download_offer',checkpoint_id=status['checkpoint_id']))
                old_download=client(download_port,'checkpoint_download',ticket['download_token'])
                old_package=package
                complete_model(c,package,receiver)
                evidence.append(dict(period=period,checkpoint_id=package.checkpoint_id,
                    world_sha256=package.manifest['parts']['world.s14']['sha256'],
                    actual_tls_transfer=True,synthetic_world_and_completion=True))
            self.assertNotEqual(evidence[0]['world_sha256'],evidence[1]['world_sha256'])
            self.assertEqual(c.period,3)
            self.assertFalse(room.view('B')['native_gameplay_enabled'])
        finally:
            room.close_checkpoints()
            for cl in reversed(clients):cl.close()
            for s,t in reversed(servers):
                s.shutdown();t.join(timeout=5);self.assertFalse(t.is_alive())
                self.assertTrue(s.wait_handlers());s.server_close()
        (folder/'network.json').write_text(json.dumps(dict(result='PASS',periods=evidence,
            game_access=False,actual_two_games=False,native_gameplay_enabled=False,
            scope='REAL_TLS_SYNTHETIC_WORLD_RECEIPTS',owned_resources_closed=True),indent=2),encoding='utf-8')


if __name__=='__main__':
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (LifecycleTests,NetworkTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    folder=HERE/'checkpoint_room_lifecycle_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    report=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),game_access=False,
        full_world_verified=False,scope='ACTUAL_TLS_WITH_SYNTHETIC_COMPLETION_RECEIPTS',
        source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in
            ('checkpoint_room_lifecycle.py','checkpoint_room_lifecycle_test.py','checkpoint_room_artifacts.py')})
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (OUT/'连续旬次通信测试结果.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(folder/'result.json')
    raise SystemExit(0 if result.wasSuccessful() else 1)
