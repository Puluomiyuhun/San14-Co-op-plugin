"""Actual loopback TLS + existing binding/journal; native Save/load are doubles."""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys
import threading
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
sys.path[:0] = [str(PRIVATE/'python_deps'), str(ROOT/'outputs/san14-link')]
from b_warm_room import WarmRoom, receive_staged, report_warm_completion, ACTION
from checkpoint_fresh_save_binding_test import (manifest, make_coordinator, run_model, model_world,
    model_artifact, complete_model, OwnedServer, NATIVE_ID, NATIVE_EPOCH)
from checkpoint_fresh_save_binding import FreshSaveBinding
from checkpoint_room_client import RoomConnection
from room_transport import Client, make_certificate

OUTPUT = None
EVIDENCE = []


class RoomTests(unittest.TestCase):
    def setUp(self):
        self.folder = OUTPUT/self._testMethodName
        self.folder.mkdir()
        self.room = WarmRoom(manifest())
        self.servers = []
        self.clients = []
        cert, key, self.fp = make_certificate(self.folder/'tls')
        def serve(owner):
            server = OwnedServer(('127.0.0.1', 0), owner, cert, key)
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
            self.servers.append((server, thread)); thread.start()
            return server.server_address[1]
        self.port = serve(self.room)
        self.download = serve(self.room.download_endpoint)
        def control(method, token):
            client = RoomConnection('127.0.0.1', self.port, self.fp,
                dict(method=method, credential=token, profile=self.room.manifest['profile']))
            self.clients.append(client); return client
        self.a = control('host', self.room.host_token)
        self.b = control('join', self.room.invite)
        for client, force in ((self.a, 12), (self.b, 2)):
            self.assertTrue(client.request(dict(action='select_force', force_id=force,
                request_id=secrets.token_hex(16), expected_revision=self.room.revision))['ok'])
        for client in (self.a, self.b):
            self.assertTrue(client.request(dict(action='confirm_force', request_id=secrets.token_hex(16),
                expected_revision=self.room.revision))['ok'])
        self.c = make_coordinator(self.room)
        self.artifacts = {}
        self.binding = FreshSaveBinding(self.room, self.c, native_room_id=NATIVE_ID,
            native_room_epoch=NATIVE_EPOCH, artifact_reader=lambda gen: self.artifacts[gen], source_kind='FIXTURE_ONLY')

    def tearDown(self):
        self.room.close_checkpoints()
        for client in reversed(self.clients):
            client.close()
        for server, thread in reversed(self.servers):
            server.shutdown(); thread.join(timeout=5)
            self.assertFalse(thread.is_alive()); self.assertTrue(server.wait_handlers()); server.server_close()

    def offer(self, generation):
        run_model(self.c)
        world = model_world(self.c)
        reserved = self.binding.reserve(generation, f'mp{generation:08d}.s14', world)
        self.artifacts[generation] = model_artifact(reserved.request, generation)
        return self.binding.publish(generation, lambda: world)

    def receive(self, package, name='received'):
        def connect(token):
            return Client('127.0.0.1', self.download, self.fp,
                dict(method='checkpoint_download', credential=token, profile=self.room.manifest['profile']))
        return receive_staged(self.b, connect, checkpoint_id=package.checkpoint_id, scope=self.c.scope,
            epoch=self.c.epoch, period=self.c.period, cut=package.manifest['cut'], attachments=self.c.attachments,
            directory=self.folder/name)

    def args(self, package):
        return dict(profile_sha256='1'*64, receipt_key='2'*64, attempt=2**63+3, pid=123,
                    birth=2**60+7, loaded_date=package.manifest['node'], viewer_force=2, viewer_ruler=952)

    def test_two_tls_transfers_ack_never_advances(self):
        records = []
        old = None
        for generation in (1, 2):
            package = self.offer(generation)
            received = self.receive(package, f'received-{generation}')
            self.assertEqual(received.verified_file(), self.artifacts[generation].data)
            self.assertEqual(received.journal.status()['status'], 'STAGED')
            epoch = self.c.epoch
            reply = report_warm_completion(self.b, received, **self.args(package))
            self.assertFalse(reply['warm_completion']['next_period_authorized'])
            status = self.a.request(dict(action='status'))['state']['warm_completion']
            self.assertEqual(status, reply['warm_completion'])
            self.assertEqual((self.c.epoch, self.c.period, self.c.phase), (epoch, generation, 'RECONCILING'))
            self.assertEqual(len(self.c.applied_receipts), generation-1)
            self.assertFalse(self.b.request(dict(action='period_ready', epoch=epoch, ready=True))['ok'])
            with self.assertRaises(Exception):
                report_warm_completion(self.b, received, **self.args(package))
            if old:
                self.assertFalse(self.b.request(old)['ok'])
            old = reply['warm_completion']['packet']
            records.append(dict(period=generation, checkpoint_id=package.checkpoint_id,
                                file_sha256=package.manifest['parts']['world.s14']['sha256'],
                                journal='STAGED', ack_source=status['source']))
            if generation == 1:
                # Explicit old protocol MODEL receipt, not a warm ACK effect.
                complete_model(self.c, package)
                self.assertEqual(self.c.period, 2)
        EVIDENCE.append(dict(case='two_tls', deliveries=records, native_save='MODEL_ONLY',
            warm_load='MODEL_ONLY', between_periods='EXPLICIT_COMPLETE_MODEL', ready_from_warm_ack=False))

    def test_wrong_scope_sender_and_conflicting_ack_rejected(self):
        package = self.offer(1); received = self.receive(package)
        # The old download lease ends when a local load intent is reserved;
        # diagnostic completion is still valid at this same checkpoint.
        from authoritative_sync import CheckpointReceiver
        receiver = CheckpointReceiver(package.manifest, package.checkpoint_id, self.c.scope,
                                     self.c.epoch, self.c.period, package.manifest['cut'])
        for chunk in package.chunks(): receiver.accept(chunk)
        self.c.received('B', self.c.epoch, receiver)
        self.c.begin_guest_load('B', self.c.epoch)
        reply = report_warm_completion(self.b, received, **self.args(package))
        packet = reply['warm_completion']['packet']
        self.assertFalse(self.a.request(packet)['ok'])
        for key, value in [('epoch', '0'*32), ('scope_sha256', '0'*64), ('file_sha256', '0'*64),
                           ('viewer_force', 12), ('receipt_key', '3'*64), ('period', True),
                           ('file_size', True), ('pid', 2**32), ('attempt', '01')]:
            self.assertFalse(self.b.request({**packet, key: value})['ok'], key)
        self.assertTrue(self.b.request(packet)['duplicate'])
        self.assertEqual(self.c.period, 1)
        EVIDENCE.append(dict(case='reject_mismatch', duplicate_diagnostic_only=True))

    def test_changed_file_and_lost_reply_cannot_be_replayed(self):
        package = self.offer(1); received = self.receive(package)
        original = received.file.read_bytes(); received.file.write_bytes(original+b'drift')
        with self.assertRaises(Exception): report_warm_completion(self.b, received, **self.args(package))
        self.assertFalse(received.ack_attempted)
        received.file.write_bytes(original)
        class DropReply:
            player_id = 'B'
            def request(_, packet):
                self.b.request(packet)
                raise EOFError('Actual TLS request delivered; local adapter loses returned result')
        with self.assertRaises(EOFError): report_warm_completion(DropReply(), received, **self.args(package))
        self.assertTrue(received.ack_attempted)
        self.assertTrue((received.directory/'warm-ack-attempt.json').exists())
        with self.assertRaises(Exception): report_warm_completion(self.b, received, **self.args(package))
        self.assertEqual(self.c.period, 1)
        EVIDENCE.append(dict(case='local_changed_and_lost_reply', sent_once=True, ready=False))


def pins():
    paths = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None)}
    paths.add(Path(__file__).resolve())
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)
            if p.is_relative_to(ROOT) and p.suffix == '.py'}


if __name__ == '__main__':
    OUTPUT = PRIVATE/'b_warm_room_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True)
    before = pins(); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RoomTests))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    sources = pins()
    stable = all(sources.get(k) == v for k, v in before.items())
    report = dict(family='san14.b-warm-room.v1', result='PASS' if result.wasSuccessful() and result.testsRun == 3 and stable else 'FAIL',
                  tests=result.testsRun, sources=sources, inputs_unchanged=stable, cases=EVIDENCE,
                  game_access=False, actual_tls=True, native_save_load=False, native_ready=False,
                  failures=[(str(t), detail) for t, detail in result.failures+result.errors])
    report['artifacts'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT/'result.json'); print(stream.getvalue())
    raise SystemExit(0 if report['result'] == 'PASS' else 1)
