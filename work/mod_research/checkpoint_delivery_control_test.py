"""Real separate-B TLS/SQLite byte acknowledgement, no native/game access.

Coordinator simulation/world transitions below are explicitly MODEL setup.
Production delivery code never obtains native permission or completes a load.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import queue
import secrets
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from checkpoint_delivery_control import (DeliveryControlEndpoint, GuestDelivery,
    RulesContextRoom, RoomConnection, CheckpointJournal, RoomError, SyncError)
from checkpoint_rules_context import remote_context, GAME_SHA, rules
from authoritative_sync import (CheckpointPackage, CheckpointReceiver, PeriodCoordinator,
    canonical, digest, scope_from_room, next_node, sha)
from room_transport import Server, Client, make_certificate
from checkpoint_transfer import receive_checkpoint

HERE = Path(__file__).resolve().parent
OUTPUT = None
EVIDENCE = []


def manifest():
    return dict(profile=dict(protocol='san14.room.v1', game_sha256=GAME_SHA,
        adapter_contract='research-no-native-room-adapter.v1', checkpoint_sha256='b'*64,
        rules_sha256=digest(rules(0, 1))), forces=[dict(id=12, name='OWNED A', main_district_id=11),
        dict(id=2, name='OWNED B', main_district_id=2)], source={'fixture': 'No game catalog'})


def offer(room, c):
    # MODEL input/simulation observations, not production/native Ready.
    for p in ('A', 'B'): c.set_ready(p, c.epoch, True)
    c.begin_simulation(c.seal_inputs())
    parts = {'world.s14': b'OWNED DIAGNOSTIC BYTES, NOT A GAME SAVE.' * 2048,
             'adapter.json': b'{"fixture":"byte-acknowledgement-only"}'}
    package = CheckpointPackage(c.scope, c.epoch, c.period,
        {k: c.seal[k] for k in ('sequence', 'prefix_sha256')}, next_node(c.node),
        c.state_contract, sha(parts['world.s14']), parts, source_player='A')
    c.offer_checkpoint('A', package.manifest)
    room.install_offered_checkpoint(c, package)
    return package


def coordinator(room):
    c = PeriodCoordinator(scope_from_room(room), 'MODEL_BYTE_ROUNDTRIP_ONLY.v1', 'c'*64,
        {'A': 'a'*32, 'B': 'b'*32}, dict(year=203, month=8, day=11, phase='PLANNING_BOUNDARY'))
    room.bind_coordinator(c)
    return c


class Fixture:
    def __init__(self):
        self.room = RulesContextRoom(manifest())
        self.endpoint = DeliveryControlEndpoint(self.room)
        for p, method, credential in [('A', 'host', self.room.host_token), ('B', 'join', self.room.invite)]:
            self.endpoint.authenticate(dict(method=method, credential=credential,
                profile=self.room.manifest['profile']), p)
        for p, force in [('A', 12), ('B', 2)]:
            assert self.endpoint.handle(p, p, dict(action='select_force', force_id=force,
                request_id=secrets.token_hex(16), expected_revision=self.room.revision))['ok']
        for p in ('A', 'B'):
            assert self.endpoint.handle(p, p, dict(action='confirm_force',
                request_id=secrets.token_hex(16), expected_revision=self.room.revision))['ok']
        self.c = coordinator(self.room)
        self.package = offer(self.room, self.c)
        self.pin()

    def pin(self):
        reply = self.endpoint.handle('B', 'B', dict(action='rules_context',
            checkpoint_id=self.package.checkpoint_id, expected_context_sha256=None))
        assert reply['ok']
        self.common = dict(checkpoint_id=self.package.checkpoint_id,
                           context_sha256=reply['context_sha256'])
        self.begin_packet = dict(action='checkpoint_delivery_begin',
                                request_id=secrets.token_hex(16), **self.common)

    def begin(self):
        reply = self.endpoint.handle('B', 'B', self.begin_packet)
        assert reply['ok'], reply
        self.tx = reply['transaction']
        return reply

    def chunk(self, chunk):
        return dict(action='checkpoint_delivery_chunk', transaction=self.tx, chunk=chunk, **self.common)

    def send(self):
        for chunk in self.package.chunks():
            reply = self.endpoint.handle('B', 'B', self.chunk(chunk))
            assert reply['ok'], reply

    def finish_packet(self):
        return dict(action='checkpoint_delivery_finish', transaction=self.tx, **self.common)

    def finish(self):
        return self.endpoint.handle('B', 'B', self.finish_packet())

    def assert_held(self, test):
        test.assertEqual(self.endpoint.status()['state'], 'HELD')
        test.assertTrue(self.room.checkpoint_status()['closed'])
        test.assertFalse(self.room.checkpoint_status()['download_available'])
        test.assertEqual(self.room.download_endpoint.status()['active_connection_owners'], 0)
        test.assertFalse(self.endpoint.status()['native_pause_confirmed'])


class DeliveryTests(unittest.TestCase):
    def setUp(self): self.f = Fixture()
    def tearDown(self): self.f.room.close_checkpoints()

    def test_complete_duplicates_and_concurrent_finish_once(self):
        f = self.f; first = f.begin()
        ready_before = set(f.c.ready)  # Prior MODEL simulation setup retains its old ready set.
        again = f.endpoint.handle('B', 'B', f.begin_packet)
        self.assertEqual(first['transaction'], again['transaction']); self.assertTrue(again['duplicate'])
        chunk = next(f.package.chunks())
        self.assertTrue(f.endpoint.handle('B', 'B', f.chunk(chunk))['ok'])
        self.assertTrue(f.endpoint.handle('B', 'B', f.chunk(chunk))['duplicate'])
        f.send()
        with patch.object(f.c, 'received', wraps=f.c.received) as received:
            with ThreadPoolExecutor(max_workers=4) as pool:
                replies = list(pool.map(lambda _: f.finish(), range(8)))
            self.assertEqual(received.call_count, 1)
        self.assertTrue(all(r['ok'] for r in replies))
        self.assertEqual(sum(not r['duplicate'] for r in replies), 1)
        self.assertTrue(f.c.bytes_received); self.assertIsNone(f.c.load_intent)
        self.assertEqual(f.c.applied_receipts, {}); self.assertEqual(f.c.ready, ready_before)
        self.assertEqual(f.c.phase, 'RECONCILING')

    def test_wrong_role_foreign_token_and_replacement_do_not_retire(self):
        f = self.f
        self.assertFalse(f.endpoint.handle('A', 'A', f.begin_packet)['ok']); f.begin()
        packet = f.finish_packet(); packet['transaction'] = 'f'*32
        self.assertFalse(f.endpoint.handle('B', 'B', packet)['ok'])
        replacement = {**f.begin_packet, 'request_id': 'f'*32}
        self.assertFalse(f.endpoint.handle('B', 'B', replacement)['ok'])
        self.assertFalse(f.room.checkpoint_status()['closed'])
        f.send(); self.assertTrue(f.finish()['ok'])

    def test_empty_return_and_public_digest_are_not_verified_bytes(self):
        f = self.f; f.begin()
        packet = {**f.finish_packet(), 'verified': True, 'sha256': f.package.checkpoint_id}
        self.assertFalse(f.endpoint.handle('B', 'B', packet)['ok'])
        f.assert_held(self); self.assertFalse(f.c.bytes_received)

    def test_missing_adapter_blocks_finish(self):
        f = self.f; f.begin()
        for chunk in f.package.chunks():
            if chunk['part'] == 'world.s14': self.assertTrue(f.endpoint.handle('B', 'B', f.chunk(chunk))['ok'])
        self.assertFalse(f.finish()['ok']); f.assert_held(self)
        self.assertFalse(f.c.bytes_received)

    def test_corrupt_bytes_never_set_received(self):
        import base64
        f = self.f; f.begin()
        chunks = list(f.package.chunks()); raw = bytearray(base64.b64decode(chunks[0]['data'])); raw[0] ^= 1
        chunks[0]['data'] = base64.b64encode(raw).decode('ascii')
        for chunk in chunks: self.assertTrue(f.endpoint.handle('B', 'B', f.chunk(chunk))['ok'])
        self.assertFalse(f.finish()['ok']); f.assert_held(self)
        self.assertFalse(f.c.bytes_received)

    def test_conflicting_duplicate_is_terminal(self):
        import base64
        f = self.f; f.begin(); chunk = next(f.package.chunks())
        self.assertTrue(f.endpoint.handle('B', 'B', f.chunk(chunk))['ok'])
        raw = bytearray(base64.b64decode(chunk['data'])); raw[0] ^= 1
        chunk['data'] = base64.b64encode(raw).decode('ascii')
        self.assertFalse(f.endpoint.handle('B', 'B', f.chunk(chunk))['ok']); f.assert_held(self)
        self.assertFalse(f.finish()['ok'])

    def test_attachment_context_drift_retires_owned_transaction(self):
        f = self.f; f.begin(); f.c.attachments['B'] = 'd'*32
        self.assertFalse(f.finish()['ok']); f.assert_held(self)

    def test_disconnect_revokes_old_download_ticket(self):
        f = self.f; f.begin()
        ticket = f.room.artifacts.issue_ticket('B', 'B')
        f.endpoint.disconnect('A', 'A'); f.assert_held(self)
        with self.assertRaises((RoomError, SyncError)):
            f.room.download_endpoint.authenticate(dict(method='checkpoint_download',
                credential=ticket['download_token'], profile=f.room.manifest['profile']), 'old-download')

    def test_external_intent_preserved_but_old_transaction_rejected(self):
        f = self.f; f.begin(); f.send()
        # MODEL an independent owner already reserved; module must not reset it.
        f.c.bytes_received = True
        intent = f.c.begin_guest_load('B', f.c.epoch)
        self.assertFalse(f.finish()['ok']); f.assert_held(self)
        self.assertEqual(f.c.load_intent, intent)

    def test_prior_received_bool_does_not_create_remote_receipt(self):
        f = self.f; f.c.bytes_received = True
        self.assertFalse(f.endpoint.handle('B', 'B', f.begin_packet)['ok'])
        self.assertEqual(f.endpoint.status()['state'], 'EMPTY')

    def test_external_close_reports_not_current_and_blocks_finish(self):
        f = self.f; f.begin(); f.send(); f.room.close_checkpoints()
        self.assertFalse(f.endpoint.status()['current'])
        self.assertFalse(f.endpoint.status()['can_return_bytes'])
        self.assertFalse(f.finish()['ok']); self.assertFalse(f.c.bytes_received)

    def test_unexpected_received_failure_retires_without_rollback(self):
        f = self.f; f.begin(); f.send(); original = f.c.received
        def fail(*args):
            original(*args)
            raise RuntimeError('owned injected failure after mutation')
        with patch.object(f.c, 'received', side_effect=fail):
            with self.assertRaises(RuntimeError): f.finish()
        f.assert_held(self); self.assertTrue(f.c.bytes_received)
        self.assertIsNone(f.c.load_intent)

    def test_second_generation_requires_independent_model_load_completion(self):
        f = self.f; f.begin(); f.send(); self.assertTrue(f.finish()['ok'])
        old_packet = f.finish_packet(); old_id = f.package.checkpoint_id; m = f.package.manifest
        # MODEL ONLY: production endpoint has no loaded action. Establish prior lineage.
        intent = f.c.begin_guest_load('B', f.c.epoch)
        f.c.loaded('B', f.c.epoch, old_id, intent, m['world_sha256'], 2, 'd'*32,
            dict(attachment=f.c.attachments['A'], world_sha256=m['world_sha256'], node=m['node']))
        f.package = offer(f.room, f.c); f.pin(); f.begin(); f.send()
        self.assertFalse(f.endpoint.handle('B', 'B', old_packet)['ok'])
        self.assertFalse(f.room.checkpoint_status()['closed'])
        self.assertTrue(f.finish()['ok']); self.assertIsNone(f.c.load_intent)
        self.assertEqual(f.endpoint.status()['previous']['checkpoint_id'], old_id)

    def test_raw_load_and_ready_messages_cannot_bypass_native_ports(self):
        f = self.f
        for action in ('checkpoint_loaded', 'begin_guest_load', 'loaded', 'checkpoint_delivery_load'):
            self.assertFalse(f.endpoint.handle('B', 'B', dict(action=action, verified=True))['ok'])
        self.assertFalse(f.endpoint.handle('B', 'B',
            dict(action='period_ready', epoch=f.c.epoch, ready=True))['ok'])
        self.assertIsNone(f.c.load_intent); self.assertEqual(f.c.applied_receipts, {})


def child(config_path):
    cfg = json.loads(Path(config_path).read_text(encoding='utf-8'))
    b = RoomConnection('127.0.0.1', cfg['port'], cfg['fingerprint'],
        dict(method='join', credential=cfg['invite'], profile=cfg['profile']))
    try:
        state = b.request({'action': 'status'})['state']
        assert b.request(dict(action='select_force', force_id=2, request_id=secrets.token_hex(16),
            expected_revision=state['revision']))['ok']
        state = b.request({'action': 'status'})['state']
        assert b.request(dict(action='confirm_force', request_id=secrets.token_hex(16),
            expected_revision=state['revision']))['ok']
        print(json.dumps({'connected': True}), flush=True)
        command = json.loads(sys.stdin.readline()); checkpoint_id = command['checkpoint_id']
        source = remote_context(b, cfg['profile'], checkpoint_id); value = source.value
        reply = b.request(dict(action='checkpoint_download_offer', checkpoint_id=checkpoint_id)); assert reply['ok']
        m = value['checkpoint']['manifest']
        r = CheckpointReceiver(m, checkpoint_id, value['scope'], m['epoch'], m['period'], m['cut'])
        download = Client('127.0.0.1', cfg['download_port'], cfg['fingerprint'],
            dict(method='checkpoint_download', credential=reply['download_token'], profile=cfg['profile']))
        transfer = receive_checkpoint(download, r, action='checkpoint_chunk')
        j = CheckpointJournal(Path(config_path).parent/'b-journal.sqlite', value['scope'], m,
            checkpoint_id, m['epoch'], m['period'], m['cut'], value['coordinator']['attachments'], create=True)
        mode = cfg['mode']
        if mode != 'empty': j.stage(r)
        if mode == 'corrupt':
            with sqlite3.connect(j.path) as db:
                original = j.verified_parts()['world.s14']
                db.execute("UPDATE parts SET data=? WHERE name='world.s14'", (b'!'+original[1:],))
        profile = deepcopy(cfg['profile'])
        if mode == 'wrong-profile': profile['game_sha256'] = 'e'*64
        delivery = None; error = None
        repeated_without_request = None
        try:
            delivery = GuestDelivery(b, profile, j); outcome = delivery.run()
        except (RoomError, SyncError, EOFError, OSError) as exc:
            error = type(exc).__name__; outcome = delivery.status() if delivery else None
            if delivery:
                count = b.status()['successful_requests']
                try: delivery.run()
                except (RoomError, SyncError):
                    repeated_without_request = b.status()['successful_requests'] == count
        print(json.dumps(dict(mode=mode, delivery=outcome, error=error, journal_status=j.status()['status'],
            transferred_bytes=transfer['received_bytes'], control_open=b.status()['transport_open'],
            repeated_without_request=repeated_without_request, no_host_object=True)), flush=True)
        assert sys.stdin.readline().strip() == 'close'
    finally: b.close()


class SeparateProcessTests(unittest.TestCase):
    def _run(self, mode):
        folder = OUTPUT/mode; folder.mkdir()
        room = RulesContextRoom(manifest()); endpoint = DeliveryControlEndpoint(room)
        class DropFinishReply:
            def authenticate(self, *args): return endpoint.authenticate(*args)
            def disconnect(self, *args): return endpoint.disconnect(*args)
            def handle(self, player, connection, packet):
                reply = endpoint.handle(player, connection, packet)
                if packet.get('action') == 'checkpoint_delivery_finish' and reply.get('ok'):
                    raise EOFError('owned dropped reply after successful receipt')
                return reply
        server_endpoint = DropFinishReply() if mode == 'lost-reply' else endpoint
        cert, key, fingerprint = make_certificate(folder)
        with Server(('127.0.0.1', 0), server_endpoint, cert, key) as control, \
             Server(('127.0.0.1', 0), room.download_endpoint, cert, key) as download:
            threads = [threading.Thread(target=s.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
                       for s in (control, download)]
            for t in threads: t.start()
            a = None; proc = None; lines = queue.Queue()
            try:
                a = RoomConnection('127.0.0.1', control.server_address[1], fingerprint,
                    dict(method='host', credential=room.host_token, profile=room.manifest['profile']))
                state = a.request({'action': 'status'})['state']
                self.assertTrue(a.request(dict(action='select_force', force_id=12,
                    request_id=secrets.token_hex(16), expected_revision=state['revision']))['ok'])
                config = dict(port=control.server_address[1], download_port=download.server_address[1],
                    fingerprint=fingerprint, invite=room.invite, profile=room.manifest['profile'], mode=mode)
                config_path = folder/'private.json'; config_path.write_text(json.dumps(config), encoding='utf-8')
                proc = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), '--child', str(config_path)],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                def read():
                    for line in proc.stdout: lines.put(line)
                reader = threading.Thread(target=read, daemon=True); reader.start()
                self.assertTrue(json.loads(lines.get(timeout=30))['connected'])
                state = a.request({'action': 'status'})['state']
                self.assertTrue(a.request(dict(action='confirm_force', request_id=secrets.token_hex(16),
                    expected_revision=state['revision']))['ok'])
                c = coordinator(room); p = offer(room, c)
                ready_before = set(c.ready)
                proc.stdin.write(json.dumps({'checkpoint_id': p.checkpoint_id})+'\n'); proc.stdin.flush()
                result = json.loads(lines.get(timeout=30))
                (folder/'child-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
                self.assertIsNone(c.load_intent); self.assertEqual(c.applied_receipts, {})
                self.assertEqual(c.ready, set() if room.checkpoint_status()['closed'] else ready_before)
                self.assertEqual(c.phase, 'HELD' if room.checkpoint_status()['closed'] else 'RECONCILING')
                if mode == 'success':
                    self.assertTrue(c.bytes_received)
                    self.assertEqual(result['delivery']['state'], 'RECEIVED')
                    self.assertEqual(result['journal_status'], 'STAGED')
                    self.assertTrue(result['control_open'])
                elif mode == 'lost-reply':
                    self.assertTrue(c.bytes_received)
                    self.assertEqual(result['delivery']['state'], 'HELD')
                    self.assertEqual(result['journal_status'], 'STAGED')
                    self.assertFalse(result['control_open'])
                    self.assertFalse(result['delivery']['protocol_revocation_confirmed'])
                    self.assertIsNotNone(result['delivery']['protocol_revocation_error'])
                    self.assertTrue(result['repeated_without_request'])
                    self.assertEqual(endpoint.status()['state'], 'HELD')
                    self.assertTrue(room.checkpoint_status()['closed'])
                else:
                    self.assertFalse(c.bytes_received); self.assertIsNotNone(result['error'])
                    self.assertEqual(endpoint.status()['state'], 'EMPTY')
                    self.assertEqual(room.checkpoint_status()['closed'], mode != 'wrong-profile')
                EVIDENCE.append(result)
                proc.stdin.write('close\n'); proc.stdin.flush(); proc.wait(timeout=10)
                stderr = proc.stderr.read(); (folder/'child.stderr.txt').write_text(stderr, encoding='utf-8')
                self.assertEqual(proc.returncode, 0, stderr)
            finally:
                if proc and proc.poll() is None:
                    # Only our explicitly created fixture process, no native hook.
                    proc.terminate(); proc.wait(timeout=10)
                if a: a.close()
                room.close_checkpoints()
                for s in (control, download): s.shutdown()
                for t in threads: t.join(timeout=5)

    def test_separate_b_actual_tls_sqlite_return(self): self._run('success')
    def test_empty_sqlite_never_begins_return(self): self._run('empty')
    def test_corrupt_sqlite_never_begins_return(self): self._run('corrupt')
    def test_wrong_profile_does_not_retire_room(self): self._run('wrong-profile')
    def test_lost_real_tls_reply_never_replays_or_claims_ack(self): self._run('lost-reply')


def main():
    global OUTPUT
    OUTPUT = HERE/'checkpoint_delivery_control_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True)
    source_files = [Path(__file__).resolve(), HERE/'checkpoint_delivery_control.py',
                   HERE/'checkpoint_rules_context.py', HERE/'checkpoint_room_client.py',
                   HERE/'checkpoint_room_lifecycle.py', HERE/'checkpoint_room_artifacts.py',
                   HERE/'checkpoint_ready_barrier.py', HERE/'checkpoint_room_progress.py']
    source_files += [HERE.parents[1]/'outputs/san14-link'/name for name in
                     ('authoritative_sync.py', 'checkpoint_journal.py', 'checkpoint_transfer.py', 'room_transport.py')]
    before = {p.relative_to(HERE.parents[1]).as_posix(): sha(p.read_bytes()) for p in source_files}
    with (OUTPUT/'tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    after = {p.relative_to(HERE.parents[1]).as_posix(): sha(p.read_bytes()) for p in source_files}
    report = dict(schema='san14.delivery-control-owned.v1', result='PASS' if result.wasSuccessful() and before == after else 'FAIL',
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        sources_unchanged=before == after, sources_sha256=after, separate_process=EVIDENCE,
        game_access=False, native_execution=False, load_intent_created_by_module=False,
        full_world_verified=False, room_ready=False,
        scope='Actual loopback TLS/independent B process/SQLite byte return; no game or native callback. Coordinator advance/setup explicitly modeled.')
    (OUTPUT/'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'result': report['result'], 'tests_run': result.testsRun, 'failures': len(result.failures),
                      'errors': len(result.errors), 'path': str(OUTPUT/'result.json')}))
    if report['result'] != 'PASS':
        print((OUTPUT/'tests.txt').read_text(encoding='utf-8'))
        raise SystemExit(1)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child': child(sys.argv[2])
    else: main()
