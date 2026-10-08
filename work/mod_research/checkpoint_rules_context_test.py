"""Real loopback TLS/context/SQLite plus self-owned RPM; no game/native loading.

The separate B process receives no host Room/coordinator object. Fixture memory
and identity/fence callbacks are explicit doubles, never game-ready evidence.
"""
from copy import deepcopy
import ctypes as C
from datetime import datetime
import json
from pathlib import Path
import queue
import secrets
import struct
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from checkpoint_rules_context import (RulesContextRoom, NativeRulesBinding, ContextSource,
    local_context, remote_context, context_from_room, Config, GAME_SHA, rules,
    RoomError, SyncError, CheckpointRoom, ProgressRoom, NextWorldRequest, WorldGeneration)
from checkpoint_room_client import RoomConnection
from authoritative_sync import (PeriodCoordinator, CheckpointPackage, CheckpointReceiver,
    canonical, digest, scope_from_room, next_node, sha)
from checkpoint_journal import CheckpointJournal
from checkpoint_transfer import receive_checkpoint
from room_transport import Client, Server, make_certificate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = None
EVIDENCE = []
SETTINGS = rules(0, 1)


def manifest():
    return dict(profile=dict(protocol='san14.room.v1', game_sha256=GAME_SHA,
        adapter_contract='research-no-native-room-adapter.v1', checkpoint_sha256='b'*64,
        rules_sha256=digest(SETTINGS)), forces=[dict(id=12, name='OWNED A', main_district_id=11),
        dict(id=2, name='OWNED B', main_district_id=2)], source={'fixture': 'No game catalog'})


def select(room):
    for player, method, credential in [('A', 'host', room.host_token), ('B', 'join', room.invite)]:
        room.authenticate(dict(method=method, credential=credential, profile=room.manifest['profile']), player)
    for p, force in [('A', 12), ('B', 2)]:
        assert room.handle(p, p, dict(action='select_force', force_id=force,
            request_id=secrets.token_hex(16), expected_revision=room.revision))['ok']
    for p in ('A', 'B'):
        assert room.handle(p, p, dict(action='confirm_force', request_id=secrets.token_hex(16),
            expected_revision=room.revision))['ok']


def coordinator(room):
    c = PeriodCoordinator(scope_from_room(room), 'OWNED_MEMORY_KNOWN_FIELDS_ONLY.v1', 'c'*64,
        {'A': 'a'*32, 'B': 'b'*32}, dict(year=203, month=8, day=11, phase='PLANNING_BOUNDARY'))
    room.bind_coordinator(c)
    return c


def offer(room, c):
    # MODEL protocol observations to reach the checkpoint boundary. No native readiness claim.
    for p in ('A', 'B'):
        c.set_ready(p, c.epoch, True)
    c.begin_simulation(c.seal_inputs())
    parts = {'world.s14': b'OWNED DIAGNOSTIC SAVE, NOT SAN DATA.' * 4096,
             'adapter.json': b'{"fixture":true}'}
    p = CheckpointPackage(c.scope, c.epoch, c.period,
        {k: c.seal[k] for k in ('sequence', 'prefix_sha256')}, next_node(c.node),
        c.state_contract, sha(parts['world.s14']), parts, source_player='A')
    c.offer_checkpoint('A', p.manifest)
    room.install_offered_checkpoint(c, p)
    return p


def stage(folder, scope, attachments, package):
    m = package.manifest
    r = CheckpointReceiver(m, package.checkpoint_id, scope, m['epoch'], m['period'], m['cut'])
    for chunk in package.chunks(): r.accept(chunk)
    j = CheckpointJournal(folder/'journal.sqlite', scope, m, package.checkpoint_id,
        m['epoch'], m['period'], m['cut'], attachments, create=True)
    j.stage(r)
    return j


K32 = C.WinDLL('kernel32', use_last_error=True)
K32.GetCurrentProcess.restype = C.c_void_p
K32.ReadProcessMemory.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
K32.ReadProcessMemory.restype = C.c_int


class OwnedMemory:
    def __init__(self, viewer=2):
        self.image_buffer = C.create_string_buffer(0x2238000)
        self.root_buffer = C.create_string_buffer(0x86000)
        self.world_buffer = C.create_string_buffer(0x1800)
        self.image = C.addressof(self.image_buffer)
        self.root = C.addressof(self.root_buffer)
        self.world = C.addressof(self.world_buffer)
        self.put(self.image + 0x1FCA1E0, '<Q', self.root)
        self.put(self.root + 0x85130, '<Q', self.world)
        self.put(self.image + 0x1FD0C5C, '<i', 1)
        self.put(self.image + 0x18EB628, '<I', 0)
        self.populate(self.world, viewer, 11)
        self.reads = 0
        self.local_holds = []

    def put(self, address, fmt, value):
        raw = struct.pack(fmt, value)
        C.memmove(address, raw, len(raw))

    def populate(self, world, viewer, day):
        for offset, fmt, value in [(0x34, '<H', 203), (0x36, '<B', 8), (0x37, '<B', day),
                                   (0x3A, '<B', viewer), (0x16A8, '<I', 1 << 8)]:
            self.put(world + offset, fmt, value)

    def replace(self):
        self.old_world = self.world_buffer
        self.world_buffer = C.create_string_buffer(0x1800)
        self.world = C.addressof(self.world_buffer)
        self.populate(self.world, 2, 21)
        self.put(self.root + 0x85130, '<Q', self.world)

    def read(self, address, size):
        regions = [(self.image, C.sizeof(self.image_buffer)), (self.root, C.sizeof(self.root_buffer)),
                   (self.world, C.sizeof(self.world_buffer))]
        assert any(start <= address and address + size <= start + count for start, count in regions)
        result = C.create_string_buffer(size); read = C.c_size_t()
        if not K32.ReadProcessMemory(K32.GetCurrentProcess(), address, result, size, C.byref(read)) or read.value != size:
            raise OSError('Owned memory read failed')
        self.reads += 1
        return result.raw

    def bind(self, source, **overrides):
        args = dict(image=self.image, read=self.read, identity_check=lambda: None,
                    guard_check=lambda: None, on_local_hold=self.local_holds.append)
        args.update(overrides)
        return NativeRulesBinding(source, SETTINGS, **args)


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.folder = OUTPUT/self._testMethodName; self.folder.mkdir()
        self.room = RulesContextRoom(manifest()); select(self.room)
        self.c = coordinator(self.room)

    def test_real_checkpoint_and_progress_room_export_supported(self):
        for cls in (CheckpointRoom, ProgressRoom, RulesContextRoom):
            room = cls(manifest()); select(room); c = coordinator(room)
            memory = OwnedMemory(viewer=12)
            binding = memory.bind(local_context(room, 'A'))
            raw = binding.export_current(); config = Config.from_buffer_copy(raw)
            self.assertEqual(bytes(config.epoch).hex(), room.binding_epoch)
            self.assertNotEqual(bytes(config.epoch).hex(), c.epoch)
            self.assertEqual(config.viewer, 12); self.assertGreater(memory.reads, 0)
            self.assertIsNone(c.load_intent); self.assertEqual(c.ready, set())

    def test_staged_target_uses_room_epoch_and_observes_new_pointer_after_load(self):
        p = offer(self.room, self.c); j = stage(self.folder, self.c.scope, self.c.attachments, p)
        memory = OwnedMemory(); binding = memory.bind(local_context(self.room, 'B', p.checkpoint_id))
        old = Config.from_buffer_copy(binding.export_current()).world
        request = binding.next_world_request(9, j)
        self.assertEqual(request.generation, 9); self.assertEqual(request.epoch.hex(), self.room.binding_epoch)
        self.assertNotEqual(request.epoch.hex(), self.c.epoch)
        memory.replace()  # Only owned memory changes; no loader is called.
        observed = binding.observe_loaded(request); binding.check_scope(observed)
        self.assertNotEqual(Config.from_buffer_copy(observed.config).world, old)
        self.assertEqual(j.status()['status'], 'STAGED')
        self.assertIsNone(self.c.load_intent); self.assertFalse(self.c.bytes_received)
        self.assertFalse(binding.status()['ready'])

    def test_scope_rejects_period_epoch_as_native_epoch(self):
        memory = OwnedMemory(); binding = memory.bind(local_context(self.room, 'B'))
        c = Config.from_buffer_copy(binding.export_current()); c.epoch[:] = bytes.fromhex(self.c.epoch)
        with self.assertRaises(RoomError): binding.check_scope(WorldGeneration(1, 'd'*64, bytes(c)))
        self.assertTrue(memory.local_holds); self.assertTrue(binding.status()['protocol_revocation_confirmed'])

    def test_wrong_viewer_retires_tickets_and_active_downloads(self):
        p = offer(self.room, self.c)
        source = local_context(self.room, 'B', p.checkpoint_id)
        tickets = [self.room.handle('B', 'B', dict(action='checkpoint_download_offer', checkpoint_id=p.checkpoint_id)) for _ in range(2)]
        endpoint = self.room.download_endpoint
        endpoint.authenticate(dict(method='checkpoint_download', credential=tickets[0]['download_token'],
            profile=self.room.manifest['profile']), 'old-stream')
        memory = OwnedMemory(viewer=12); binding = memory.bind(source)
        with self.assertRaises(RoomError): binding.export_current()
        self.assertTrue(source.revocation_confirmed); self.assertEqual(endpoint.status()['active_connection_owners'], 0)
        with self.assertRaises(RoomError): endpoint.authenticate(dict(method='checkpoint_download',
            credential=tickets[1]['download_token'], profile=self.room.manifest['profile']), 'late')
        self.assertFalse(endpoint.handle('B', 'old-stream', {})['ok'])
        self.assertEqual(self.c.ready, set()); self.assertIsNone(self.c.load_intent)

    def test_false_guard_and_local_hold_failure_are_visible(self):
        memory = OwnedMemory(); binding = memory.bind(local_context(self.room, 'B'),
            guard_check=lambda: False, on_local_hold=lambda _: False)
        with self.assertRaises(RoomError): binding.export_current()
        self.assertEqual(memory.reads, 0); self.assertIsNotNone(binding.status()['local_hold_error'])
        self.assertTrue(binding.status()['protocol_revocation_confirmed'])

    def test_context_change_blocks_native_read_without_repinning(self):
        memory = OwnedMemory(); source = local_context(self.room, 'B'); binding = memory.bind(source)
        self.c.attachments['B'] = 'e'*32
        with self.assertRaises(RoomError): binding.export_current()
        self.assertEqual(memory.reads, 0)
        with self.assertRaises(RoomError): binding.export_current()

    def test_world_change_during_read_is_rejected(self):
        memory = OwnedMemory()
        def changing(address, count):
            value = memory.read(address, count)
            if address == memory.world + 0x16A8: memory.replace()
            return value
        binding = memory.bind(local_context(self.room, 'B'), read=changing)
        with self.assertRaises(RoomError): binding.export_current()
        self.assertTrue(memory.local_holds)

    def test_no_checkpoint_cannot_make_target(self):
        memory = OwnedMemory(); binding = memory.bind(local_context(self.room, 'B'))
        with self.assertRaises(RoomError): binding.next_world_request(2, None)
        self.assertIsNone(self.c.load_intent)

    def test_unstaged_journal_cannot_make_target(self):
        p = offer(self.room, self.c); m = p.manifest
        j = CheckpointJournal(self.folder/'empty.sqlite', self.c.scope, m, p.checkpoint_id,
            m['epoch'], m['period'], m['cut'], self.c.attachments, create=True)
        memory = OwnedMemory(); binding = memory.bind(local_context(self.room, 'B', p.checkpoint_id))
        with self.assertRaises(RoomError): binding.next_world_request(2, j)
        self.assertEqual(j.status()['status'], 'EMPTY'); self.assertIsNone(self.c.load_intent)
        self.assertEqual(memory.reads, 0); self.assertTrue(memory.local_holds)

    def test_fault_cleanup_failure_is_not_success(self):
        memory = OwnedMemory(viewer=12); source = local_context(self.room, 'B'); binding = memory.bind(source)
        with patch.object(self.room, 'close_checkpoints', side_effect=RuntimeError('Fixture cleanup unavailable')):
            with self.assertRaises(RoomError): binding.export_current()
        self.assertFalse(source.revocation_confirmed); self.assertIn('cleanup unavailable', source.revocation_error)
        self.assertTrue(memory.local_holds)
        self.room.close_checkpoints()

    def test_network_ready_does_not_bypass_existing_native_barrier(self):
        result = self.room.handle('B', 'B', dict(action='period_ready', epoch=self.c.epoch, ready=True))
        self.assertTrue(result['ok']); self.assertEqual(self.c.ready, set())
        self.assertEqual(result['ready_barrier']['players']['B']['state'], 'HOLD_PENDING')
        self.assertFalse(self.room.handle('B', 'B', dict(action='rules_context', checkpoint_id=None, ready=True))['ok'])

    def test_context_fault_requires_issued_current_control_identity(self):
        value = self.room.handle('B', 'B', dict(action='rules_context', checkpoint_id=None, expected_context_sha256=None))
        packet = dict(action='rules_context_fault', checkpoint_id=None,
                      context_sha256=value['context_sha256'], reason='RULES_REBIND_FAILED')
        self.assertFalse(self.room.handle('B', 'wrong-control', packet)['ok'])
        self.assertFalse(self.room.handle('A', 'A', packet)['ok'])
        self.assertFalse(self.room.checkpoint_status()['closed'])
        self.assertTrue(self.room.handle('B', 'B', packet)['protocol_revocation_confirmed'])

    def test_explicit_context_handoff_preserves_old_module_config_and_new_lineage(self):
        memory = OwnedMemory(); binding = memory.bind(local_context(self.room, 'B'))
        original = WorldGeneration(1, 'd'*64, binding.export_current())
        p = offer(self.room, self.c)
        binding.adopt_context(local_context(self.room, 'B', p.checkpoint_id))
        binding.check_scope(original)  # Same callback now usable by old ResidentPort.restore.
        self.assertEqual(binding.export_current(), original.config)
        j = stage(self.folder, self.c.scope, self.c.attachments, p)
        q = binding.next_world_request(2, j); memory.replace(); observed = binding.observe_loaded(q)
        # Explicit MODEL completion only to exercise subsequent phase adoption.
        receiver = CheckpointReceiver(p.manifest, p.checkpoint_id, self.c.scope,
            self.c.epoch, self.c.period, p.manifest['cut'])
        for chunk in p.chunks(): receiver.accept(chunk)
        self.c.received('B', self.c.epoch, receiver)
        intent = self.c.begin_guest_load('B', self.c.epoch)
        attachment = 'e'*32
        self.c.loaded('B', self.c.epoch, p.checkpoint_id, intent, p.manifest['world_sha256'], 2,
            attachment, dict(attachment=self.c.attachments['A'], world_sha256=p.manifest['world_sha256'], node=p.manifest['node']))
        binding.adopt_context(local_context(self.room, 'B'), loaded_world=observed, new_attachment=attachment)
        binding.check_scope(observed)
        self.assertEqual(binding.export_current(), observed.config)
        self.assertEqual(self.c.ready, set()); self.assertFalse(binding.status()['ready'])
        self.assertFalse(self.room.checkpoint_status()['closed'])

    def test_context_adoption_rejects_foreign_room_before_using_native_world(self):
        memory = OwnedMemory(); binding = memory.bind(local_context(self.room, 'B'))
        foreign = RulesContextRoom(manifest()); select(foreign); coordinator(foreign)
        with self.assertRaises(RoomError): binding.adopt_context(local_context(foreign, 'B'))
        self.assertEqual(memory.reads, 0); self.assertTrue(memory.local_holds)
        self.assertTrue(self.room.checkpoint_status()['closed']); self.assertFalse(foreign.checkpoint_status()['closed'])

    def test_local_lock_order_supports_outer_room_owner_and_concurrent_check(self):
        memory = OwnedMemory(); source = local_context(self.room, 'B'); binding = memory.bind(source)
        # Every current callback must already hold the Room before the source.
        current = source._current
        def checked_current():
            self.assertTrue(self.room.lock._is_owned())
            return current()
        source._current = checked_current
        source.check()
        owned = threading.Event(); second_attempt = threading.Event(); done = threading.Event()
        failures = []
        def outer_owner():
            try:
                with self.room.lock:
                    owned.set()
                    self.assertTrue(second_attempt.wait(2))
                    binding.export_current()
            except BaseException as exc: failures.append(repr(exc))
            finally: done.set()
        def concurrent_check():
            try:
                self.assertTrue(owned.wait(2)); second_attempt.set(); source.check()
            except BaseException as exc: failures.append(repr(exc))
        one = threading.Thread(target=outer_owner, daemon=True)
        two = threading.Thread(target=concurrent_check, daemon=True)
        one.start(); two.start()
        self.assertTrue(done.wait(3), 'Room/source lock inversion')
        one.join(2); two.join(2)
        self.assertFalse(one.is_alive()); self.assertFalse(two.is_alive()); self.assertEqual(failures, [])

    def test_context_check_drift_keeps_old_remote_fault_identity(self):
        packet = dict(action='rules_context', checkpoint_id=None, expected_context_sha256=None)
        first = self.room.handle('B', 'B', packet)
        self.c.attachments['B'] = 'e'*32
        check = self.room.handle('B', 'B', {**packet, 'expected_context_sha256': first['context_sha256']})
        self.assertFalse(check['ok'])
        hold = self.room.handle('B', 'B', dict(action='rules_context_fault', checkpoint_id=None,
            context_sha256=first['context_sha256'], reason='NATIVE_CONTEXT_FAILED'))
        self.assertTrue(hold['protocol_revocation_confirmed'])


def child_main(path):
    cfg = json.loads(path.read_text())
    connection = RoomConnection('127.0.0.1', cfg['port'], cfg['fingerprint'],
        dict(method='join', credential=cfg['invite'], profile=cfg['profile']), heartbeat_seconds=1)
    def request(action, **fields):
        state = connection.request({'action': 'status'})['state']
        reply = connection.request(dict(action=action, request_id=secrets.token_hex(16),
            expected_revision=state['revision'], **fields))
        assert reply['ok'], reply
    try:
        request('select_force', force_id=2)
        print('SELECTED', flush=True)
        assert sys.stdin.readline().strip() == 'CONFIRM'
        request('confirm_force'); print('CONFIRMED', flush=True)
        command = json.loads(sys.stdin.readline())
        source = remote_context(connection, cfg['profile'], command['checkpoint_id'])
        value = source.value; p = value['checkpoint']; m = p['manifest']
        ticket = connection.request(dict(action='checkpoint_download_offer', checkpoint_id=p['id']))
        download = Client('127.0.0.1', cfg['download_port'], cfg['fingerprint'],
            dict(method='checkpoint_download', credential=ticket['download_token'], profile=cfg['profile']))
        receiver = CheckpointReceiver(m, p['id'], value['scope'], m['epoch'], m['period'], m['cut'])
        transfer = receive_checkpoint(download, receiver, action='checkpoint_chunk')
        journal = CheckpointJournal(path.parent/'guest.sqlite', value['scope'], m, p['id'], m['epoch'],
            m['period'], m['cut'], value['coordinator']['attachments'], create=True)
        journal.stage(receiver)
        memory = OwnedMemory(); binding = memory.bind(source)
        before = binding.export_current()
        target = binding.next_world_request(41, journal)
        memory.replace(); observed = binding.observe_loaded(target); binding.check_scope(observed)
        # A wrong local view must hold locally and actually revoke A's downloads over TLS.
        memory.put(memory.world + 0x3A, '<B', 12)
        try: binding.export_current()
        except RoomError: pass
        else: raise AssertionError('Wrong viewer accepted')
        assert binding.status()['protocol_revocation_confirmed']
        result = dict(case='SEPARATE_B_PROCESS_TLS_CONTEXT_AND_STAGED_TARGET', result='PASS',
            transferred_bytes=transfer['received_bytes'], integrity_verified=transfer['integrity_verified'],
            staged_status=journal.status()['status'], local_generation=target.generation,
            stable_binding_epoch=target.epoch.hex() == value['scope']['binding_epoch'],
            period_epoch_not_used=target.epoch.hex() != m['epoch'],
            postload_pointer_observed=Config.from_buffer_copy(before).world != Config.from_buffer_copy(observed.config).world,
            local_hold_called=bool(memory.local_holds), remote_fault_revoked=True,
            shared_host_room_object=False, native_load_called=False, full_world_verified=False,
            game_access=False, native_identity_and_fence='EXPLICIT_OWNED_TEST_DOUBLES')
        print(json.dumps(result), flush=True)
    finally:
        connection.close()


class NetworkTests(unittest.TestCase):
    def test_separate_guest_process_uses_tls_not_shared_host_object(self):
        folder = OUTPUT/self._testMethodName; folder.mkdir()
        room = RulesContextRoom(manifest()); cert, key, fingerprint = make_certificate(folder/'tls')
        servers = [Server(('127.0.0.1', 0), endpoint, cert, key) for endpoint in (room, room.download_endpoint)]
        threads = [threading.Thread(target=s.serve_forever, kwargs={'poll_interval': .05}, daemon=True) for s in servers]
        for t in threads: t.start()
        host = RoomConnection('127.0.0.1', servers[0].server_address[1], fingerprint,
            dict(method='host', credential=room.host_token, profile=room.manifest['profile']))
        child = None
        try:
            state = host.request({'action': 'status'})['state']
            assert host.request(dict(action='select_force', force_id=12, request_id=secrets.token_hex(16),
                                     expected_revision=state['revision']))['ok']
            cfg = folder/'private-child.json'
            cfg.write_text(json.dumps(dict(port=servers[0].server_address[1], download_port=servers[1].server_address[1],
                fingerprint=fingerprint, invite=room.invite, profile=room.manifest['profile'])), encoding='utf-8')
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--remote-child', str(cfg)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            lines = queue.Queue()
            reader = threading.Thread(target=lambda: [lines.put(line.rstrip()) for line in child.stdout], daemon=True)
            reader.start()
            self.assertEqual(lines.get(timeout=10), 'SELECTED')
            state = host.request({'action': 'status'})['state']
            self.assertTrue(host.request(dict(action='confirm_force', request_id=secrets.token_hex(16),
                expected_revision=state['revision']))['ok'])
            child.stdin.write('CONFIRM\n'); child.stdin.flush()
            self.assertEqual(lines.get(timeout=10), 'CONFIRMED')
            c = coordinator(room); p = offer(room, c)
            child.stdin.write(json.dumps(dict(checkpoint_id=p.checkpoint_id))+'\n'); child.stdin.flush()
            response = json.loads(lines.get(timeout=20))
            self.assertEqual(response['result'], 'PASS')
            child.wait(timeout=10); stderr = child.stderr.read()
            self.assertEqual(child.returncode, 0, stderr)
            self.assertTrue(room.checkpoint_status()['closed']); self.assertIsNone(c.load_intent)
            self.assertFalse(c.bytes_received); self.assertEqual(c.ready, set())
            self.assertEqual(room.download_endpoint.status()['active_connection_owners'], 0)
            EVIDENCE.append(response)
        finally:
            if child is not None:
                if child.poll() is None:
                    child.stdin.close()
                    try: child.wait(timeout=10)
                    except subprocess.TimeoutExpired: child.terminate(); child.wait(timeout=5)
                for stream in (child.stdin, child.stdout, child.stderr):
                    if not stream.closed: stream.close()
            host.close()
            for s in servers: s.shutdown(); s.server_close()
            for t in threads: t.join(timeout=5)

    def test_remote_profile_mismatch_and_lost_fault_ack_are_not_success(self):
        folder = OUTPUT/self._testMethodName; folder.mkdir()
        room = RulesContextRoom(manifest()); cert, key, fingerprint = make_certificate(folder/'tls')
        server = Server(('127.0.0.1', 0), room, cert, key)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, daemon=True); thread.start()
        clients = []
        try:
            for method, credential in [('host', room.host_token), ('join', room.invite)]:
                clients.append(RoomConnection('127.0.0.1', server.server_address[1], fingerprint,
                    dict(method=method, credential=credential, profile=room.manifest['profile'])))
            for conn, force in zip(clients, (12, 2)):
                state = conn.request({'action':'status'})['state']
                assert conn.request(dict(action='select_force', force_id=force, request_id=secrets.token_hex(16),
                    expected_revision=state['revision']))['ok']
            for conn in clients:
                state = conn.request({'action':'status'})['state']
                assert conn.request(dict(action='confirm_force', request_id=secrets.token_hex(16),
                    expected_revision=state['revision']))['ok']
            c = coordinator(room)
            with self.assertRaises(RoomError): remote_context(clients[1], {**room.manifest['profile'], 'rules_sha256': 'd'*64})
            source = remote_context(clients[1], room.manifest['profile'])
            memory = OwnedMemory(); binding = memory.bind(source)
            binding.export_current()
            clients[1].close()
            with self.assertRaises(RoomError): binding.export_current()
            self.assertTrue(memory.local_holds); self.assertFalse(source.revocation_confirmed)
            self.assertIsNotNone(source.revocation_error); self.assertIsNone(c.load_intent)
        finally:
            for conn in clients: conn.close()
            server.shutdown(); server.server_close(); thread.join(timeout=5)


def main():
    global OUTPUT
    if len(sys.argv) == 3 and sys.argv[1] == '--remote-child':
        child_main(Path(sys.argv[2])); return 0
    OUTPUT = HERE/'checkpoint_rules_context_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True)
    names = [HERE/'checkpoint_rules_context.py', Path(__file__).resolve(), HERE/'checkpoint_ready_barrier.py',
        HERE/'checkpoint_room_lifecycle.py', HERE/'checkpoint_room_progress.py', HERE/'checkpoint_room_artifacts.py',
        HERE/'checkpoint_room_client.py', HERE/'human_rules_activation_room.py', HERE/'human_rules_world_lifecycle.py']
    names += [ROOT/'outputs/san14-link'/name for name in ('authoritative_sync.py', 'room_session.py',
                                                       'room_transport.py', 'checkpoint_journal.py', 'checkpoint_transfer.py')]
    before = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in names}
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (LocalTests, NetworkTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    stable = all(sha((ROOT/name).read_bytes()) == digest_ for name, digest_ in before.items())
    report = dict(schema='san14.rules-context-tests.v1', result='PASS' if result.wasSuccessful() and stable else 'FAIL',
        tests_run=result.testsRun, errors=len(result.errors), failures=len(result.failures), skipped=len(result.skipped),
        sources_sha256=before, sources_unchanged=stable, cases=EVIDENCE,
        actual_loopback_tls=True, self_owned_memory_rpm=True, actual_game_load=False,
        native_identity_and_fence='EXPLICIT_OWNED_TEST_DOUBLES', game_access=False,
        actual_two_computers=False, ready=False)
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(result=report['result'], tests_run=result.testsRun, output=str(OUTPUT/'result.json'))))
    return 0 if report['result']=='PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
