"""Local binding checks plus real TLS; all world observations are MODEL_ONLY.

Optional --owner-run is an explicit self-owned native fixture output directory
containing success/first.packet and success/second.packet, never a game save.
No process access, native calls, live script imports or historical data lookup.
"""
from dataclasses import replace
from datetime import datetime
import argparse
import json
from pathlib import Path
import re
import secrets
import threading
from types import MappingProxyType
import unittest
from unittest.mock import patch

from checkpoint_fresh_save_binding import (FreshSaveBinding, FreshSaveBindingError,
    LocalWorldObservation)
from checkpoint_fresh_save_packet import DecodedArtifact, decode_packet
from checkpoint_room_lifecycle import CheckpointRoom
from checkpoint_room_client import RoomConnection
from authoritative_sync import (CheckpointReceiver, PeriodCoordinator, digest,
    next_node, scope_from_room, sha)
from checkpoint_transfer import receive_checkpoint
from checkpoint_journal import CheckpointJournal
from room_transport import Client, Server, make_certificate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = None
OWNER_RUN = None
OWNER_EVIDENCE = None
NETWORK_EVIDENCE = []
CONTRACT = 'MODEL_ONLY_fresh_binding_known_fields.v1'
NATIVE_ID = b'\x01' + bytes(31)
NATIVE_EPOCH = 7


def validate_owner_run(folder):
    """Local diagnostic consistency, not cryptographic source attestation."""
    raw = (folder / 'result.json').read_bytes()
    report = json.loads(raw)
    if (report.get('schema') != 'san14.a-save-user-owner.v1' or report.get('result') != 'PASS'
            or report.get('sources_unchanged') is not True or report.get('game_access') is not False):
        raise ValueError('Owner run is not a passing offline source-stable check')
    sources = report.get('sources')
    required = {'a_save_user_owner_test.py', 'a_save_user_owner.cpp',
                'a_save_user_owner_fixture.cpp', 'checkpoint_fresh_save_packet.cpp'}
    if type(sources) is not dict or not required <= set(sources) or not 4 <= len(sources) <= 128:
        raise ValueError('Owner run has no complete source fingerprint map')
    for name, expected in sources.items():
        if (type(name) is not str or re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', name) is None
                or Path(name).name != name or Path(name).suffix not in ('.h', '.cpp', '.asm', '.py')
                or type(expected) is not str or re.fullmatch('[0-9a-f]{64}', expected) is None):
            raise ValueError('Invalid owner source identity')
        if sha((HERE / name).read_bytes()) != expected:
            raise ValueError('Current owner source differs: ' + name)
    for filename, field in (('fixture.exe', 'fixture_sha256'), ('a_save_user_owner.lib', 'production_sha256')):
        if sha((folder / filename).read_bytes()) != report.get(field):
            raise ValueError('Owner binary differs: ' + filename)
    rows = report.get('cases')
    if type(rows) is not list or not rows or not all(type(row) is dict and
            row.get('result') == 'PASS' and row.get('exit') == 0 and row.get('game_access') is False
            for row in rows):
        raise ValueError('Owner fixture cases did not all pass')
    success = [row for row in rows if row.get('case') == 'success']
    if len(success) != 1 or any(success[0].get(k) != 2 for k in ('binds', 'queues', 'completed')):
        raise ValueError('Owner run did not complete two exports')
    for name in ('first.packet', 'second.packet'):
        if not (folder / 'success' / name).is_file():
            raise ValueError('Owner run is missing success/' + name)
    return dict(result_sha256=sha(raw), fixture_sha256=report['fixture_sha256'],
        production_sha256=report['production_sha256'], source_count=len(sources),
        sources_match_current=True, diagnostic_consistency_only=True, producer_authenticated=False)


def manifest():
    return dict(profile=dict(protocol='san14.room.v1', game_sha256='a'*64,
        adapter_contract='research-no-native-room-adapter.v1', checkpoint_sha256='b'*64,
        rules_sha256='c'*64), forces=[dict(id=12, name='MODEL A', main_district_id=11),
        dict(id=2, name='MODEL B', main_district_id=2)],
        source={'fixture': 'Synthetic catalog, no game state'})


def select_direct(room):
    room.authenticate(dict(method='host', credential=room.host_token, profile=room.manifest['profile']), 'a')
    room.authenticate(dict(method='join', credential=room.invite, profile=room.manifest['profile']), 'b')
    for p, conn, force in (('A', 'a', 12), ('B', 'b', 2)):
        assert room.handle(p, conn, dict(action='select_force', force_id=force,
            request_id=secrets.token_hex(16), expected_revision=room.revision))['ok']
    for p, conn in (('A', 'a'), ('B', 'b')):
        assert room.handle(p, conn, dict(action='confirm_force',
            request_id=secrets.token_hex(16), expected_revision=room.revision))['ok']


def make_coordinator(room):
    c = PeriodCoordinator(scope_from_room(room), CONTRACT, 'd'*64,
        {'A': 'a'*32, 'B': 'b'*32}, dict(year=203, month=8, day=1, phase='PLANNING_BOUNDARY'))
    room.bind_coordinator(c)
    # Fixed synthetic already-applied prefix, matching the native owner fixture.
    for p in ('A', 'B'):
        c.applied_prefix(p, c.epoch, 9, 'e'*64, 'd'*64, c.attachments[p])
    return c


def run_model(c):
    for p in ('A', 'B'):
        c.set_ready(p, c.epoch, True)
    c.begin_simulation(c.seal_inputs())


def model_world(c):
    node = next_node(c.node)
    return LocalWorldObservation(c.attachments['A'], node['year'], node['month'], node['day'],
        12, 666, CONTRACT, sha(('MODEL WORLD PERIOD ' + str(c.period)).encode()), True)


def model_artifact(request, ordinal, *, data=None):
    """Explicit test double for the already decoded trusted local export."""
    q = dict(request)
    r = dict(status=5, error=0, generation=q['generation'], active=0, entries=7, exits=7,
        abnormal=0, first_call=ordinal*2, last_call=ordinal*2+1, save_state=0x123400,
        intents=1, flushed=1, binds=1, queues=1, phase_mask=31, worker_started=1,
        worker_joined=1, native_success=1, finalizer_returned=1, return_matched=1,
        original_returned=7, stop_after_commit=0, executor_thread=123, completed_requests=ordinal,
        full_world=False, room_ready=False, file_bytes_verified=True)
    data = data if data is not None else ('MODEL SAVE PERIOD ' + str(q['period'])).encode()*6000
    return DecodedArtifact(MappingProxyType(q), MappingProxyType(r), data, sha(data))


class Fixture:
    def __init__(self, reader=None):
        self.room = CheckpointRoom(manifest())
        select_direct(self.room)
        self.c = make_coordinator(self.room)
        self.artifacts = {}
        self.reads = []
        def local_reader(generation):
            self.reads.append(generation)
            return reader(generation) if reader else self.artifacts[generation]
        self.binding = FreshSaveBinding(self.room, self.c, native_room_id=NATIVE_ID,
            native_room_epoch=NATIVE_EPOCH, artifact_reader=local_reader, source_kind='FIXTURE_ONLY')
        run_model(self.c)
        self.world = model_world(self.c)

    def reserve(self, generation=1):
        reservation = self.binding.reserve(generation, f'mp{generation:08x}.s14', self.world)
        self.artifacts[generation] = model_artifact(reservation.request, self.c.period)
        return reservation

    def publish(self, generation=1):
        return self.binding.publish(generation, lambda: self.world)


def complete_model(c, package, receiver=None):
    """Synthetic load/world receipt solely to exercise protocol rotation."""
    if receiver is None:
        receiver = CheckpointReceiver(package.manifest, package.checkpoint_id, c.scope, c.epoch,
            c.period, package.manifest['cut'])
        for chunk in package.chunks():
            receiver.accept(chunk)
    c.received('B', c.epoch, receiver)
    intent = c.begin_guest_load('B', c.epoch)
    c.loaded('B', c.epoch, package.checkpoint_id, intent, package.manifest['world_sha256'], 2,
        secrets.token_hex(16), dict(attachment=c.attachments['A'],
            world_sha256=package.manifest['world_sha256'], node=package.manifest['node']))


class BindingTests(unittest.TestCase):
    def test_reservation_is_immutable_and_has_full_binding_without_authority(self):
        f = Fixture(); reservation = f.reserve()
        self.assertEqual(reservation.request['room_epoch'], NATIVE_EPOCH)
        self.assertEqual(reservation.request['room_id'], NATIVE_ID)
        with self.assertRaises(TypeError):
            reservation.request['period'] = 999
        p = f.publish()
        adapter = json.loads(p._parts['adapter.json'])
        self.assertEqual(adapter['binding']['boundary']['epoch'], f.c.epoch)
        self.assertEqual(adapter['binding']['boundary']['scope'], f.c.scope)
        self.assertEqual(adapter['binding']['boundary']['cut'], p.manifest['cut'])
        self.assertEqual(digest(adapter['binding']), reservation.binding_sha256)
        self.assertEqual(adapter['current_host_observation']['world_sha256'], f.world.world_sha256)
        self.assertNotEqual(f.world.world_sha256, p.manifest['parts']['world.s14']['sha256'])
        self.assertFalse(any(adapter[k] for k in ('full_world_verified', 'native_load_authorized',
            'native_gameplay_enabled', 'ready_authorized')))
        self.assertEqual(f.c.phase, 'RECONCILING')
        self.assertFalse(f.c.bytes_received)
        self.assertIsNone(f.c.load_intent)

    def test_no_observation_or_untyped_claim_cannot_publish(self):
        for observer in (None, {'safe_boundary': True}, lambda: {'safe_boundary': True}):
            f = Fixture(); f.reserve()
            with self.subTest(observer=type(observer).__name__), self.assertRaises(FreshSaveBindingError):
                f.binding.publish(1, observer)
            self.assertIsNone(f.room.artifacts)
            self.assertEqual(f.c.phase, 'HELD' if callable(observer) else 'RUNNING')

    def test_observation_is_taken_after_copy_and_requires_unchanged_world(self):
        f = Fixture(); f.reserve()
        def observe():
            self.assertEqual(f.reads, [1])
            return replace(f.world, world_sha256='f'*64)
        with self.assertRaises(FreshSaveBindingError):
            f.binding.publish(1, observe)
        self.assertIsNone(f.room.artifacts)
        self.assertIsNotNone(f.binding.status()['held_reason'])

    def test_native_request_mismatch_is_held_before_offer(self):
        changes = dict(generation=2, room_epoch=8, period=2, cut=10, room_id=bytes([2])*32,
            year=204, month=9, day=21, force=2, ruler=952, reserved=1, filename='mp00000002.s14')
        for field, value in changes.items():
            f = Fixture(); f.reserve(); a = f.artifacts[1]
            f.artifacts[1] = replace(a, request=MappingProxyType({**a.request, field: value}))
            with self.subTest(field=field), self.assertRaises(FreshSaveBindingError):
                f.publish()
            self.assertEqual(f.c.phase, 'HELD'); self.assertIsNone(f.room.artifacts)

    def test_incomplete_stopped_or_overstated_report_is_held(self):
        changes = dict(status=4, error=1, generation=2, active=1, entries=8, exits=6, abnormal=1,
            first_call=0, last_call=1, save_state=0, intents=0, flushed=0, binds=2, queues=2,
            phase_mask=15, worker_started=0, worker_joined=0, native_success=0,
            finalizer_returned=0, return_matched=0, original_returned=6, stop_after_commit=1,
            executor_thread=0, completed_requests=2, full_world=True, room_ready=True,
            file_bytes_verified=False)
        for field, value in changes.items():
            f = Fixture(); f.reserve(); a = f.artifacts[1]
            f.artifacts[1] = replace(a, report=MappingProxyType({**a.report, field: value}))
            with self.subTest(field=field), self.assertRaises(FreshSaveBindingError):
                f.publish()
            self.assertIsNone(f.room.artifacts)

    def test_unrelated_balanced_callbacks_are_permitted(self):
        f = Fixture(); f.reserve(); a = f.artifacts[1]
        f.artifacts[1] = replace(a, report=MappingProxyType({**a.report, 'entries': 9, 'exits': 9}))
        self.assertTrue(f.publish().checkpoint_id)

    def test_tampered_or_mutable_export_is_rejected(self):
        for change in ('hash', 'data', 'mutable_data', 'mutable_report', 'network_json', 'bool_int'):
            f = Fixture(); f.reserve(); a = f.artifacts[1]
            if change == 'hash': bad = replace(a, sha256='0'*64)
            elif change == 'data': bad = replace(a, data=a.data+b'changed')
            elif change == 'mutable_data': bad = replace(a, data=bytearray(a.data))
            elif change == 'mutable_report': bad = replace(a, report=dict(a.report))
            elif change == 'network_json': bad = dict(request=dict(a.request), report=dict(a.report))
            else: bad = replace(a, request=MappingProxyType({**a.request, 'generation': True}))
            f.artifacts[1] = bad
            with self.subTest(change=change), self.assertRaises(FreshSaveBindingError): f.publish()
            self.assertIsNone(f.room.artifacts)

    def test_captured_protocol_boundary_cannot_change(self):
        mutations = (lambda f: setattr(f.c, 'epoch', secrets.token_hex(16)),
            lambda f: f.c.seal.update(sequence=10), lambda f: f.c.seal.update(prefix_sha256='f'*64),
            lambda f: f.c.attachments.update(A='c'*32), lambda f: f.c.attachments.update(B='c'*32),
            lambda f: setattr(f.c, 'phase', 'WAITING_EVENT'),
            lambda f: f.room.players['B'].update(connection='new-b'),
            lambda f: f.c.inflight['A'].add('e'*32))
        for index, mutate in enumerate(mutations):
            f = Fixture(); f.reserve(); mutate(f)
            with self.subTest(index=index), self.assertRaises(ValueError): f.publish()
            self.assertEqual(f.reads, [])
            self.assertIsNotNone(f.binding.status()['held_reason'])

    def test_disconnect_during_copy_is_detected_after_copy(self):
        f = Fixture(); f.reserve(); original = f.binding._reader
        def read(generation):
            a = original(generation)
            f.room.disconnect('B', 'b')
            return a
        f.binding._reader = read
        with self.assertRaises(ValueError): f.publish()
        self.assertEqual(f.reads, [1])
        self.assertIsNone(f.room.artifacts)
        self.assertIsNotNone(f.binding.status()['held_reason'])

    def test_late_world_observer_failure_is_held_and_not_replayed(self):
        f = Fixture(); f.reserve()
        def fail(): raise RuntimeError('Own synthetic observation failed')
        with self.assertRaises(RuntimeError): f.binding.publish(1, fail)
        with self.assertRaises(FreshSaveBindingError): f.publish()
        self.assertEqual(f.reads, [1])

    def test_pending_reservation_blocks_another_native_request(self):
        f = Fixture(); f.reserve()
        with self.assertRaises(FreshSaveBindingError): f.reserve(2)
        self.assertEqual(len(f.binding.status()['reservations']), 1)

    def test_duplicate_publication_does_not_read_again_or_renew_tickets(self):
        f = Fixture(); f.reserve(); p = f.publish()
        ticket = f.room.handle('B', 'b', dict(action='checkpoint_download_offer', checkpoint_id=p.checkpoint_id))
        self.assertTrue(ticket['ok'])
        with self.assertRaises(FreshSaveBindingError): f.publish()
        self.assertEqual(f.reads, [1]); self.assertEqual(f.room.artifacts.ticket_count, 1)

    def test_second_period_keeps_native_epoch_but_binds_new_full_epoch(self):
        f = Fixture(); first = f.reserve(); p1 = f.publish(); epoch1 = f.c.epoch
        complete_model(f.c, p1); run_model(f.c); f.world = model_world(f.c)
        second = f.reserve(2); p2 = f.publish(2)
        self.assertEqual(first.request['room_epoch'], second.request['room_epoch'])
        self.assertNotEqual(epoch1, f.c.epoch)
        self.assertEqual(p2.manifest['epoch'], f.c.epoch)
        self.assertNotEqual(p1.checkpoint_id, p2.checkpoint_id)
        complete_model(f.c, p2); run_model(f.c); f.world = model_world(f.c)
        with self.assertRaises(FreshSaveBindingError): f.reserve(3)

    def test_previous_artifact_cannot_be_relabelled_as_next_period(self):
        f = Fixture(); f.reserve(); p = f.publish(); old = f.artifacts[1]
        complete_model(f.c, p); run_model(f.c); f.world = model_world(f.c); f.reserve(2)
        f.artifacts[2] = old
        with self.assertRaises(FreshSaveBindingError): f.publish(2)
        self.assertEqual(f.room.checkpoint_status()['generation'], 1)

    def test_install_failure_after_offer_is_held_without_rollback(self):
        f = Fixture(); f.reserve()
        with patch.object(f.room, 'install_offered_checkpoint', side_effect=RuntimeError('Own fault')):
            with self.assertRaises(RuntimeError): f.publish()
        self.assertEqual(f.c.phase, 'RECONCILING')
        self.assertIsNone(f.room.artifacts)
        with self.assertRaises(FreshSaveBindingError): f.publish()
        self.assertEqual(f.reads, [1])

    def test_post_install_failure_revokes_issued_ticket_and_live_channel(self):
        f = Fixture(); f.reserve(); install = f.room.install_offered_checkpoint
        captured = {}
        def install_then_fail(c, p):
            service = install(c, p); captured['service'] = service
            captured['ticket'] = f.room.handle('B', 'b', dict(action='checkpoint_download_offer',
                checkpoint_id=p.checkpoint_id))['download_token']
            token = f.room.handle('B', 'b', dict(action='checkpoint_download_offer',
                checkpoint_id=p.checkpoint_id))['download_token']
            f.room.download_endpoint.authenticate(dict(method='checkpoint_download', credential=token,
                profile=f.room.manifest['profile']), 'already-authenticated')
            captured['chunk'] = next(p.chunks())
            raise RuntimeError('Own post-install failure')
        with patch.object(f.room, 'install_offered_checkpoint', side_effect=install_then_fail):
            with self.assertRaises(RuntimeError): f.publish()
        self.assertEqual(f.c.phase, 'RECONCILING')
        self.assertTrue(f.binding.status()['publication_cleanup']['closed'])
        self.assertFalse(f.room.checkpoint_status()['download_available'])
        self.assertTrue(captured['service'].closed)
        with self.assertRaises(ValueError):
            f.room.download_endpoint.authenticate(dict(method='checkpoint_download',
                credential=captured['ticket'], profile=f.room.manifest['profile']), 'late-download')
        chunk = captured['chunk']
        self.assertFalse(f.room.download_endpoint.handle('B', 'already-authenticated',
            dict(action='checkpoint_chunk', **{k: chunk[k] for k in ('checkpoint_id', 'part', 'index')}))['ok'])

    def test_publication_cleanup_failure_is_reported_without_claiming_closed(self):
        f = Fixture(); f.reserve(); install = f.room.install_offered_checkpoint
        def install_then_fail(c, p):
            install(c, p)
            raise RuntimeError('Own post-install failure')
        with patch.object(f.room, 'install_offered_checkpoint', side_effect=install_then_fail), \
             patch.object(f.room, 'close_checkpoints', side_effect=RuntimeError('Own cleanup failure')):
            with self.assertRaises(RuntimeError): f.publish()
        status = f.binding.status()
        self.assertIsNotNone(status['held_reason'])
        self.assertEqual(status['publication_cleanup'], dict(attempted=True, closed=False, error='RuntimeError'))
        f.room.close_checkpoints()  # Explicit fixture cleanup, not an automatic publication retry.

    def test_constructor_and_reservation_reject_invalid_local_configuration(self):
        for overrides in ({'native_room_id': bytes(32)}, {'native_room_epoch': True},
                          {'source_kind': 'NETWORK'}, {'artifact_reader': None}):
            room = CheckpointRoom(manifest()); select_direct(room); c = make_coordinator(room)
            args = dict(native_room_id=NATIVE_ID, native_room_epoch=NATIVE_EPOCH,
                artifact_reader=lambda _: None, source_kind='FIXTURE_ONLY'); args.update(overrides)
            with self.subTest(overrides=tuple(overrides)), self.assertRaises(FreshSaveBindingError):
                FreshSaveBinding(room, c, **args)
        f = Fixture()
        for generation, name in ((True, 'mp00000001.s14'), (0, 'mp00000001.s14'),
                                 (1, '../world.s14'), (1, 'mpAAAAAAAA.s14')):
            with self.subTest(generation=generation, name=name), self.assertRaises(FreshSaveBindingError):
                f.binding.reserve(generation, name, f.world)
        with self.assertRaises(FreshSaveBindingError):
            f.binding.reserve(1, 'mp00000001.s14', replace(f.world, safe_boundary=False))


class OwnedServer(Server):
    """Wait for test-owned handlers, including the artifact one-shot close."""
    def __init__(self, *args):
        self._active = 0
        self._condition = threading.Condition()
        super().__init__(*args)

    def process_request(self, request, address):
        with self._condition: self._active += 1
        try: super().process_request(request, address)
        except BaseException:
            with self._condition:
                self._active -= 1; self._condition.notify_all()
            raise

    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally:
            with self._condition:
                self._active -= 1; self._condition.notify_all()

    def wait_handlers(self):
        with self._condition:
            return self._condition.wait_for(lambda: self._active == 0, timeout=5)


class NetworkTests(unittest.TestCase):
    def exchange(self, *, native_packets):
        label = 'native-owner-export' if native_packets else 'model-export'
        folder = OUTPUT / label
        folder.mkdir(parents=True)
        room = CheckpointRoom(manifest())
        cert, key, fingerprint = make_certificate(folder / 'tls')
        servers, clients, evidence = [], [], []
        artifacts, pinned_packets = {}, {}
        if native_packets:
            for generation, filename in ((1, 'first.packet'), (2, 'second.packet')):
                raw = (OWNER_RUN / 'success' / filename).read_bytes()
                decoded = decode_packet(raw)
                self.assertEqual(decoded.request['generation'], generation)
                pinned_packets[generation] = (filename, sha(raw))
        def serve(owner):
            s = OwnedServer(('127.0.0.1', 0), owner, cert, key)
            t = threading.Thread(target=s.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
            servers.append((s, t)); t.start()
            return s.server_address[1]
        def connect(port, method, credential):
            cls = Client if method == 'checkpoint_download' else RoomConnection
            client = cls('127.0.0.1', port, fingerprint,
                dict(method=method, credential=credential, profile=room.manifest['profile']))
            clients.append(client)
            return client
        def local_copy(generation):
            if native_packets:
                name, expected = pinned_packets[generation]
                raw = (OWNER_RUN / 'success' / name).read_bytes()
                self.assertEqual(sha(raw), expected, 'Explicit native fixture packet changed')
                return decode_packet(raw)
            return artifacts[generation]
        try:
            control_port = serve(room); artifact_port = serve(room.download_endpoint)
            a = connect(control_port, 'host', room.host_token)
            b = connect(control_port, 'join', room.invite)
            for client, force in ((a, 12), (b, 2)):
                self.assertTrue(client.request(dict(action='select_force', force_id=force,
                    request_id=secrets.token_hex(16), expected_revision=room.revision))['ok'])
            for client in (a, b):
                self.assertTrue(client.request(dict(action='confirm_force',
                    request_id=secrets.token_hex(16), expected_revision=room.revision))['ok'])
            c = make_coordinator(room)
            binding = FreshSaveBinding(room, c, native_room_id=NATIVE_ID, native_room_epoch=NATIVE_EPOCH,
                artifact_reader=local_copy, source_kind='FIXTURE_ONLY')
            original_connections = {p: row['connection'] for p, row in room.players.items()}
            old_channel = old_package = None
            previous_full_epoch = None
            for generation in (1, 2):
                for client in (a, b):
                    self.assertTrue(client.request(dict(action='period_ready', epoch=c.epoch, ready=True))['ok'])
                c.begin_simulation(c.seal_inputs())
                world = model_world(c)
                reservation = binding.reserve(generation, f'mp{generation:08x}.s14', world)
                if not native_packets:
                    artifacts[generation] = model_artifact(reservation.request, generation)
                package = binding.publish(generation, lambda: world)
                self.assertEqual(package.manifest['epoch'], c.epoch)
                if previous_full_epoch:
                    self.assertNotEqual(previous_full_epoch, c.epoch)
                    chunk = next(old_package.chunks())
                    self.assertFalse(old_channel.request(dict(action='checkpoint_chunk',
                        **{k: chunk[k] for k in ('checkpoint_id', 'part', 'index')}))['ok'])
                    self.assertFalse(b.request(dict(action='checkpoint_download_offer',
                        checkpoint_id=old_package.checkpoint_id))['ok'])
                previous_full_epoch = c.epoch
                ticket = b.request(dict(action='checkpoint_download_offer', checkpoint_id=package.checkpoint_id))
                self.assertTrue(ticket['ok'])
                download = connect(artifact_port, 'checkpoint_download', ticket['download_token'])
                receiver = CheckpointReceiver(ticket['manifest'], package.checkpoint_id, c.scope,
                    c.epoch, c.period, package.manifest['cut'])
                transfer = receive_checkpoint(download, receiver, action='checkpoint_chunk', window=4)
                self.assertEqual(transfer['parts'], package._parts)
                journal_path = folder / f'guest-period-{generation}.sqlite'
                journal = CheckpointJournal(journal_path, c.scope, package.manifest,
                    package.checkpoint_id, c.epoch, c.period, package.manifest['cut'],
                    c.attachments, create=True)
                journal.stage(receiver)
                reopened = CheckpointJournal(journal_path, c.scope, package.manifest,
                    package.checkpoint_id, c.epoch, c.period, package.manifest['cut'], c.attachments)
                self.assertEqual(reopened.status()['status'], 'STAGED')
                self.assertEqual(reopened.verified_parts(), transfer['parts'])
                self.assertEqual({p: row['connection'] for p, row in room.players.items()}, original_connections)
                for client in (a, b): self.assertTrue(client.request({'action': 'status'})['ok'])
                adapter = json.loads(transfer['parts']['adapter.json'])
                self.assertEqual(adapter['binding_sha256'], reservation.binding_sha256)
                self.assertEqual(adapter['binding']['boundary']['epoch'], c.epoch)
                self.assertEqual(adapter['source_kind'], 'FIXTURE_ONLY')
                ticket2 = b.request(dict(action='checkpoint_download_offer', checkpoint_id=package.checkpoint_id))
                old_channel = connect(artifact_port, 'checkpoint_download', ticket2['download_token'])
                old_package = package
                complete_model(c, package, receiver)
                evidence.append(dict(period=generation, checkpoint_id=package.checkpoint_id,
                    transferred_bytes=transfer['received_bytes'], chunks=transfer['chunks'],
                    world_save_bytes=len(transfer['parts']['world.s14']),
                    save_sha256=package.manifest['parts']['world.s14']['sha256'],
                    artifact_source='OWN_NATIVE_FIXTURE_PACKET' if native_packets else 'MODEL_DECODED_EXPORT',
                    native_packet_sha256=pinned_packets[generation][1] if native_packets else None,
                    actual_loopback_tls=True, durable_journal_reopened_status='STAGED',
                    journal_load_attempted=False, world_observations='MODEL_ONLY', load_receipt='MODEL_ONLY'))
            self.assertEqual(c.period, 3)
            self.assertNotEqual(evidence[0]['save_sha256'], evidence[1]['save_sha256'])
            self.assertFalse(binding.status()['native_gameplay_enabled'])
            self.assertFalse(room.view('B')['native_gameplay_enabled'])
        finally:
            room.close_checkpoints()
            for client in reversed(clients): client.close()
            for server, thread in reversed(servers):
                server.shutdown(); thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
                self.assertTrue(server.wait_handlers())
                server.server_close()
        NETWORK_EVIDENCE.append(dict(case=label, periods=evidence, resources_closed=True,
            game_access=False, actual_two_games=False, native_save_business='TEST_DOUBLES',
            native_exports_created_before_model_reservation=native_packets,
            dynamic_native_submit_binding_validated=False,
            full_world_verified=False, native_gameplay_enabled=False))

    def test_two_model_exports_cross_existing_tls_channel(self):
        self.exchange(native_packets=False)

    def test_two_actual_owned_native_packets_cross_existing_tls_channel(self):
        if OWNER_RUN is None:
            self.skipTest('Supply --owner-run explicitly to verify actual native fixture exports')
        self.exchange(native_packets=True)


def main():
    global OUTPUT, OWNER_RUN, OWNER_EVIDENCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-run', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    OWNER_RUN = args.owner_run.resolve() if args.owner_run else None
    if OWNER_RUN is not None:
        try:
            OWNER_EVIDENCE = validate_owner_run(OWNER_RUN)
        except (OSError, ValueError, TypeError) as exc:
            parser.error('Explicit owner run failed local provenance checks: ' + str(exc))
    OUTPUT = args.output.resolve() if args.output else HERE / 'checkpoint_fresh_save_binding_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
        for cls in (BindingTests, NetworkTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = dict(schema='san14.fresh-save-binding-check.v1',
        result='PASS' if result.wasSuccessful() else 'FAIL', tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        actual_native_fixture_packets_checked=any(row['case'] == 'native-owner-export'
            for row in NETWORK_EVIDENCE), owner_run_evidence=OWNER_EVIDENCE, network_cases=NETWORK_EVIDENCE,
        game_access=False, actual_two_games=False, full_world_verified=False,
        native_gameplay_enabled=False, native_ipc_connected=False,
        source_sha256={name: sha((HERE / name).read_bytes()) for name in
            ('checkpoint_fresh_save_binding.py', 'checkpoint_fresh_save_binding_test.py',
             'checkpoint_fresh_save_packet.py', 'checkpoint_room_artifacts.py',
             'checkpoint_room_lifecycle.py', 'checkpoint_room_client.py')})
    (OUTPUT / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(result=report['result'], path=str(OUTPUT / 'result.json'))))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
