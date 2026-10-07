"""Independent-channel authority and invalidation tests, no game access."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
import threading
import unittest
from unittest.mock import patch

from checkpoint_room_artifacts import *
from authoritative_sync import CheckpointPackage, PeriodCoordinator, scope_from_room, digest

HERE = Path(__file__).resolve().parent


def offered_fixture():
    room = ArtifactEnabledRoom(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')))
    room.authenticate(dict(method='host', credential=room.host_token, profile=room.manifest['profile']), 'a')
    room.authenticate(dict(method='join', credential=room.invite, profile=room.manifest['profile']), 'b')
    for player, connection, force in (('A','a',12), ('B','b',2)):
        assert room.handle(player, connection, dict(action='select_force', request_id=secrets.token_hex(16),
            expected_revision=room.revision, force_id=force))['ok']
    for player, connection in (('A','a'), ('B','b')):
        assert room.handle(player, connection, dict(action='confirm_force', request_id=secrets.token_hex(16),
            expected_revision=room.revision))['ok']
    scope = scope_from_room(room)
    node = dict(year=203, month=8, day=1, phase='PLANNING_BOUNDARY')
    c = PeriodCoordinator(scope, 'artifact-endpoint-fixture.v1', 'a'*64, {'A':'a'*32,'B':'b'*32}, node)
    for player in ('A','B'):
        c.set_ready(player, c.epoch, True)
    c.begin_simulation(c.seal_inputs())
    cut = {k:c.seal[k] for k in ('sequence','prefix_sha256')}
    package = CheckpointPackage(scope, c.epoch, 1, cut, {**node,'day':11}, c.state_contract,
        'a'*64, {'world.s14':b'x'*70000,'adapter.json':b'{"fixture_only":true}'}, source_player='A')
    c.offer_checkpoint('A', package.manifest)
    service = room.install_offered_checkpoint(c, package)
    return room, c, service, package


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.room, self.coordinator, self.service, self.package = offered_fixture()

    def ticket(self):
        return self.room.handle('B','b',dict(action='checkpoint_download_offer',
            checkpoint_id=self.package.checkpoint_id))

    def connect(self, token, connection='download'):
        return self.service.authenticate(dict(method='checkpoint_download', credential=token,
            profile=self.room.manifest['profile']), connection)

    def chunk(self, connection='download', **changes):
        packet = next(self.package.chunks())
        request = {k:packet[k] for k in ('checkpoint_id','part','index')}
        request['action'] = 'checkpoint_chunk'
        request.update(changes)
        return self.service.handle('B', connection, request)

    def test_artifact_disconnect_preserves_both_control_seats(self):
        ticket = self.ticket()
        self.connect(ticket['download_token'])
        self.assertTrue(self.chunk()['ok'])
        self.service.disconnect('B','download')
        self.assertEqual(self.room.players['A']['connection'], 'a')
        self.assertEqual(self.room.players['B']['connection'], 'b')
        self.assertEqual(self.room.handle('B','b',{'action':'status'})['state']['phase'], 'WAITING_NATIVE_ADAPTER')

    def test_foreign_seat_connection_or_checkpoint_cannot_get_ticket(self):
        for player, connection, checkpoint in (('A','a',self.package.checkpoint_id),
            ('B','other',self.package.checkpoint_id),('B','b','0'*64)):
            self.assertFalse(self.room.handle(player,connection,
                dict(action='checkpoint_download_offer',checkpoint_id=checkpoint))['ok'])
        self.assertEqual(self.service.ticket_count,0)

    def test_ticket_consumed_once_and_cannot_be_room_resume_secret(self):
        token = self.ticket()['download_token']
        self.connect(token)
        with self.assertRaises(RoomError):self.connect(token,'download2')
        with self.assertRaises(RoomError):self.room.authenticate(dict(method='resume',credential=token,
            profile=self.room.manifest['profile']),'forged')

    def test_control_disconnect_and_reconnect_invalidates_existing_download(self):
        self.connect(self.ticket()['download_token'])
        self.room.disconnect('B','b')
        self.assertFalse(self.chunk()['ok'])
        self.room.authenticate(dict(method='resume',credential=self.room.players['B']['token'],
            profile=self.room.manifest['profile']),'new-b')
        self.assertFalse(self.chunk()['ok'])

    def test_phase_change_and_load_reservation_block_further_bytes(self):
        self.connect(self.ticket()['download_token'])
        self.coordinator.load_intent = 'c'*32
        self.assertFalse(self.chunk()['ok'])
        self.coordinator.load_intent = None
        self.coordinator.phase = 'RUNNING'
        self.assertFalse(self.chunk()['ok'])

    def test_expired_ticket_and_active_lease_cannot_download(self):
        now = [1.0]
        self.service.clock = lambda:now[0]
        token = self.ticket()['download_token']
        now[0] = 40
        with self.assertRaises(RoomError):self.connect(token)
        token = self.ticket()['download_token']
        self.connect(token)
        now[0] = 80
        self.assertFalse(self.chunk()['ok'])
        self.assertNotIn('download', self.service.channels)

    def test_eight_expired_channels_release_capacity_without_reauthorizing_them(self):
        now = [1.0]
        self.service.clock = lambda:now[0]
        old_tokens = []
        for i in range(8):
            token = self.ticket()['download_token']
            old_tokens.append(token)
            self.connect(token, 'old-'+str(i))
        self.assertFalse(self.ticket()['ok'])
        now[0] = 40
        fresh = self.ticket()
        self.assertTrue(fresh['ok'])
        self.assertEqual(self.service.ticket_count, 9)
        self.assertEqual(self.service.status()['active_downloads'], 0)
        for i, token in enumerate(old_tokens):
            self.assertFalse(self.chunk('old-'+str(i))['ok'])
            with self.assertRaises(RoomError):
                self.connect(token, 'replay-'+str(i))
        self.connect(fresh['download_token'], 'fresh')
        self.assertTrue(self.chunk('fresh')['ok'])
        self.assertEqual(self.room.players['A']['connection'], 'a')
        self.assertEqual(self.room.players['B']['connection'], 'b')

    def test_non_ascii_credentials_are_rejected_without_consuming_a_valid_ticket(self):
        token = self.ticket()['download_token']
        for bad in ('\u00e9', '\u2603', '\ud800', ''):
            with self.subTest(credential_kind=ascii(bad)), self.assertRaises(RoomError):
                self.connect(bad, 'bad')
        self.connect(token)
        self.assertTrue(self.chunk()['ok'])

    def test_direct_construction_holds_both_locks_through_package_verification(self):
        entered, release = threading.Event(), threading.Event()
        original = CheckpointPackage.chunks
        results, errors = [], []

        def held_chunks(package):
            entered.set()
            if not release.wait(3):
                raise AssertionError('Constructor fixture release timed out')
            yield from original(package)

        def build():
            try:
                results.append(CheckpointArtifactService(self.room, self.coordinator, self.package))
            except BaseException as exc:
                errors.append(type(exc).__name__)

        with patch.object(CheckpointPackage, 'chunks', held_chunks):
            worker = threading.Thread(target=build)
            worker.start()
            try:
                self.assertTrue(entered.wait(3))
                for lock in (self.room.lock, self.coordinator.lock):
                    acquired = lock.acquire(blocking=False)
                    if acquired:
                        lock.release()
                    self.assertFalse(acquired, 'Boundary lock escaped during package iteration')
            finally:
                release.set()
                worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].connections, {'A':'a', 'B':'b'})

    def test_profile_and_packet_coordinates_rejected(self):
        token = self.ticket()['download_token']
        wrong = deepcopy(self.room.manifest['profile']);wrong['game_sha256']='0'*64
        with self.assertRaises(RoomError):self.service.authenticate(dict(method='checkpoint_download',
            credential=token,profile=wrong),'bad')
        self.connect(token)
        for changes in ({'index':True},{'index':-1},{'part':'../world.s14'},
                        {'checkpoint_id':'0'*64},{'action':'start_game'}):
            self.assertFalse(self.chunk(**changes)['ok'])

    def test_reply_mutation_and_source_package_mutation_cannot_change_pinned_bytes(self):
        self.connect(self.ticket()['download_token'])
        before = self.chunk()
        tampered = self.chunk();tampered['chunk']['data']='bad'
        self.package._parts['adapter.json']=b'new data'
        self.assertEqual(self.chunk(), before)
        self.assertFalse(self.service.status()['native_loaded'])

    def test_unoffered_package_is_rejected(self):
        self.coordinator.phase='RUNNING'
        with self.assertRaises(RoomError):CheckpointArtifactService(self.room,self.coordinator,self.package)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ArtifactTests))
    folder=HERE/'checkpoint_room_artifacts_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    report=dict(result='PASS' if result.wasSuccessful() else 'FAIL',cases=result.testsRun,
        game_accessed=False,native_gameplay_enabled=False,
        source_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
            for name in ('checkpoint_room_artifacts.py','checkpoint_room_artifacts_test.py')})
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(str(folder/'result.json'))
    raise SystemExit(0 if result.wasSuccessful() else 1)
