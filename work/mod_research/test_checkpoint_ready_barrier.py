"""Real room/TLS integration, explicitly synthetic native input/world receipts."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
import tempfile
import threading
import unittest

from checkpoint_ready_barrier import ReadyBarrierRoom, NativeReadyAction, RoomError, SyncError
from checkpoint_room_lifecycle_test import select_room, coordinator_for, complete_model
from checkpoint_room_artifacts import OUT
from checkpoint_connected_prototype import TrackingServer
from checkpoint_room_client import RoomConnection
from room_transport import make_certificate
from authoritative_sync import CheckpointPackage, next_node, scope_from_room, PeriodCoordinator

HERE = Path(__file__).resolve().parent


def new_room(**kwargs):
    room = ReadyBarrierRoom(json.loads((OUT / '房间势力目录.json').read_text(encoding='utf-8')), **kwargs)
    select_room(room)
    return room, coordinator_for(room)


def request(room, c, player, value):
    return room.handle(player, player.lower(), dict(action='period_ready', epoch=c.epoch, ready=value))


def native_receipt(action):
    # Deliberate adapter double. This function never inspects a game process.
    receipt = dict(binding=json.loads(action.binding), generation=action.generation,
        operation=action.operation, input_held=action.operation != 'RELEASE',
        planning_boundary=True, pending_local_commands=0)
    if action.operation == 'DRAIN':
        receipt['pending_replays'] = 0
    return receipt


def acknowledge(room, player):
    action = room.take_native_action(player)
    room.acknowledge_native_action(action, native_receipt(action))
    return action


def drain(room):
    room.begin_ready_drain()
    for player in ('A', 'B'):
        acknowledge(room, player)


class BarrierTests(unittest.TestCase):
    def test_native_fault_and_late_command_change_hold_room(self):
        room, c = new_room()
        request(room, c, 'A', True)
        action = room.take_native_action('A')
        room.native_fault(action)
        self.assertEqual(c.phase, 'HELD')
        room, c = new_room()
        for player in ('A', 'B'):
            request(room, c, player, True)
            acknowledge(room, player)
        drain(room)
        c.reports['A']['sequence'] += 1
        with self.assertRaises((RoomError, SyncError)):
            room.seal_ready_inputs()
        self.assertEqual(c.phase, 'HELD')
        self.assertIsNone(c.seal)

    def test_network_intent_cannot_ready_without_local_ack(self):
        room, c = new_room()
        for player in ('A', 'B'):
            self.assertTrue(request(room, c, player, True)['ok'])
        self.assertEqual(c.ready, set())
        with self.assertRaises((RoomError, SyncError)):
            room.seal_ready_inputs()
        acknowledge(room, 'A')
        self.assertEqual(c.ready, {'A'})
        acknowledge(room, 'B')
        with self.assertRaises((RoomError, SyncError)):
            room.seal_ready_inputs()
        drain(room)
        permit = room.seal_ready_inputs()
        self.assertEqual(c.phase, 'SEALED')
        self.assertEqual(permit, c.seal)
        self.assertFalse(room.ready_status()['native_simulation_started'])
        with self.assertRaises((RoomError, SyncError)):
            room.seal_ready_inputs()

    def test_cancel_revokes_ready_before_release_then_new_hold(self):
        room, c = new_room()
        request(room, c, 'A', True)
        acknowledge(room, 'A')
        self.assertTrue(request(room, c, 'A', False)['ok'])
        self.assertEqual(c.ready, set())
        self.assertEqual(room.ready_status()['players']['A']['state'], 'RELEASE_PENDING')
        self.assertFalse(request(room, c, 'A', True)['ok'])
        acknowledge(room, 'A')
        self.assertTrue(request(room, c, 'A', True)['ok'])
        self.assertEqual(c.ready, set())
        acknowledge(room, 'A')
        self.assertEqual(c.ready, {'A'})

    def test_claim_once_and_cancel_during_execution_refused(self):
        room, c = new_room()
        request(room, c, 'A', True)
        action = room.take_native_action('A')
        self.assertFalse(request(room, c, 'A', False)['ok'])
        with self.assertRaises((RoomError, SyncError)):
            room.take_native_action('A')
        room.acknowledge_native_action(action, native_receipt(action))
        with self.assertRaises((RoomError, SyncError)):
            room.acknowledge_native_action(action, native_receipt(action))
        self.assertEqual(c.phase, 'HELD')

    def test_uncertain_ack_holds_instead_of_enabling_input(self):
        for field, value in [('pending_local_commands', 1), ('input_held', False), ('planning_boundary', False)]:
            with self.subTest(field=field):
                room, c = new_room()
                request(room, c, 'A', True)
                action = room.take_native_action('A')
                receipt = native_receipt(action)
                receipt[field] = value
                with self.assertRaises((RoomError, SyncError)):
                    room.acknowledge_native_action(action, receipt)
                self.assertEqual(c.ready, set())
                self.assertEqual(c.phase, 'HELD')
                self.assertTrue(room.ready_status()['request_native_hold_all'])
                self.assertFalse(room.ready_status()['native_pause_confirmed'])

    def test_changes_during_action_or_clone_cannot_ack(self):
        for change in ('attachment', 'clone'):
            room, c = new_room()
            request(room, c, 'A', True)
            action = room.take_native_action('A')
            if change == 'attachment':
                c.attachments['A'] = 'e' * 32
            else:
                action = NativeReadyAction(action.player, action.operation, action.generation, action.binding)
            with self.assertRaises((RoomError, SyncError)):
                room.acknowledge_native_action(action, native_receipt(action))
            self.assertEqual(c.phase, 'HELD')

    def test_timeout_and_disconnect_do_not_auto_resume(self):
        now = [10.0]
        room, c = new_room(clock=lambda: now[0], acknowledgement_timeout=2)
        request(room, c, 'A', True)
        now[0] = 12.0
        self.assertEqual(room.ready_status()['held_reason'], 'NATIVE_READY_ACK_TIMEOUT')
        self.assertEqual(c.phase, 'HELD')
        room, c = new_room()
        request(room, c, 'A', True)
        acknowledge(room, 'A')
        room.disconnect('B', 'b')
        self.assertEqual(c.ready, set())
        self.assertTrue(room.ready_status()['request_native_hold_all'])
        room.authenticate(dict(method='resume', credential=room.players['B']['token'],
            profile=room.manifest['profile']), 'b2')
        self.assertFalse(room.handle('B', 'b2', dict(action='period_ready', epoch=c.epoch, ready=True))['ok'])

    def test_old_ready_does_not_cross_two_verified_model_periods(self):
        room, c = new_room()
        for _ in range(2):
            for p in ('A', 'B'):
                request(room, c, p, True)
                acknowledge(room, p)
            drain(room)
            old_epoch = c.epoch
            c.begin_simulation(room.seal_ready_inputs())  # Explicit synthetic native start.
            parts = {'world.s14': ('SYNTHETIC-' + str(c.period)).encode(), 'adapter.json': b'{}'}
            package = CheckpointPackage(c.scope, c.epoch, c.period,
                {k: c.seal[k] for k in ('sequence', 'prefix_sha256')}, next_node(c.node),
                c.state_contract, hashlib.sha256(parts['world.s14']).hexdigest(), parts, source_player='A')
            c.offer_checkpoint('A', package.manifest)
            room.install_offered_checkpoint(c, package)
            complete_model(c, package)
            self.assertFalse(request(room, c, 'A', True)['ok'])
            room.adopt_verified_planning_epoch({p: dict(binding=room._binding(p), input_held=False,
                planning_boundary=True, pending_commands=0) for p in ('A', 'B')})
            self.assertEqual(c.ready, set())
            self.assertEqual(room.ready_status()['players']['B']['state'], 'OPEN')
            self.assertFalse(room.handle('A', 'a', dict(action='period_ready', epoch=old_epoch, ready=True))['ok'])
        self.assertEqual(c.period, 3)

    def test_actual_tls_has_no_native_ack_or_start_endpoint(self):
        room = ReadyBarrierRoom(json.loads((OUT / '房间势力目录.json').read_text(encoding='utf-8')))
        with tempfile.TemporaryDirectory(prefix='ready-barrier-') as temp:
            cert, key, fingerprint = make_certificate(Path(temp))
            server = TrackingServer(('127.0.0.1', 0), room, cert, key)
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02})
            thread.start()
            clients = []
            try:
                for method, credential in (('host', room.host_token), ('join', room.invite)):
                    clients.append(RoomConnection('127.0.0.1', server.server_address[1], fingerprint,
                        dict(method=method, credential=credential, profile=room.manifest['profile']), heartbeat_seconds=1))
                for client, force in zip(clients, (12, 2)):
                    state = client.request({'action': 'status'})['state']
                    self.assertTrue(client.request(dict(action='select_force', force_id=force,
                        request_id=secrets.token_hex(16), expected_revision=state['revision']))['ok'])
                for client in clients:
                    state = client.request({'action': 'status'})['state']
                    self.assertTrue(client.request(dict(action='confirm_force', request_id=secrets.token_hex(16),
                        expected_revision=state['revision']))['ok'])
                c = PeriodCoordinator(scope_from_room(room), 'SYNTHETIC-INPUT-GATE', 'a' * 64,
                    {'A': 'a' * 32, 'B': 'b' * 32}, dict(year=203, month=8, day=1, phase='PLANNING_BOUNDARY'))
                room.bind_coordinator(c)
                for client in clients:
                    reply = client.request(dict(action='period_ready', epoch=c.epoch, ready=True))
                    self.assertTrue(reply['ok'])
                    for op in ('native_ready_ack', 'start_simulation', 'native_input_released'):
                        self.assertFalse(client.request(dict(action=op))['ok'])
                self.assertEqual(c.ready, set())
                for player in ('A', 'B'):
                    acknowledge(room, player)
                for client in clients:
                    reply = client.request({'action': 'period_ready_status'})
                    self.assertEqual(reply['ready_barrier']['ready'], ['A', 'B'])
                    self.assertFalse(reply['ready_barrier']['native_backend_connected'])
            finally:
                for client in clients:
                    client.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                self.assertTrue(server.wait_handlers())

    def test_early_ready_accepts_peer_commands_then_fresh_drain(self):
        room, c = new_room()
        request(room, c, 'A', True)
        hold_a = room.take_native_action('A')
        # A is locking local input while B continues to submit legitimate work.
        c.set_pending('B', c.epoch, {'f' * 32})
        c.applied_prefix('A', c.epoch, 1, 'd' * 64, 'c' * 64, c.attachments['A'])
        room.acknowledge_native_action(hold_a, native_receipt(hold_a))
        self.assertEqual(c.ready, {'A'})
        self.assertFalse(request(room, c, 'B', True)['ok'])
        c.set_pending('B', c.epoch, set())
        request(room, c, 'B', True)
        acknowledge(room, 'B')
        # B's final replay has not yet reached the same prefix.
        with self.assertRaises((RoomError, SyncError)):
            room.begin_ready_drain()
        self.assertEqual(c.phase, 'PLANNING')
        c.applied_prefix('B', c.epoch, 1, 'd' * 64, 'c' * 64, c.attachments['B'])
        drain(room)
        permit = room.seal_ready_inputs()
        self.assertEqual(permit['sequence'], 1)
        self.assertEqual(permit['world_sha256'], 'c' * 64)

    def test_drain_cannot_use_changed_prefix_or_pending_replays(self):
        for change in ('prefix_before_claim', 'prefix_during_action', 'pending_replays'):
            room, c = new_room()
            for player in ('A', 'B'):
                request(room, c, player, True)
                acknowledge(room, player)
            room.begin_ready_drain()
            if change == 'prefix_before_claim':
                c.applied_prefix('A', c.epoch, 1, 'd' * 64, 'c' * 64, c.attachments['A'])
                with self.assertRaises((RoomError, SyncError)):
                    room.take_native_action('A')
            else:
                action = room.take_native_action('A')
                receipt = native_receipt(action)
                if change == 'prefix_during_action':
                    c.applied_prefix('A', c.epoch, 1, 'd' * 64, 'c' * 64, c.attachments['A'])
                else:
                    receipt['pending_replays'] = 1
                with self.assertRaises((RoomError, SyncError)):
                    room.acknowledge_native_action(action, receipt)
            self.assertEqual(c.phase, 'HELD')
            self.assertIsNone(c.seal)

    def test_cancel_invalidates_final_drain_and_waits_for_executing_peer(self):
        room, c = new_room()
        for player in ('A', 'B'):
            request(room, c, player, True)
            acknowledge(room, player)
        room.begin_ready_drain()
        action_b = room.take_native_action('B')
        self.assertFalse(request(room, c, 'A', False)['ok'])
        self.assertEqual(c.ready, {'A', 'B'})
        room.acknowledge_native_action(action_b, native_receipt(action_b))
        self.assertTrue(request(room, c, 'A', False)['ok'])
        self.assertEqual(c.ready, {'B'})
        self.assertEqual(room.ready_status()['players']['B']['state'], 'READY_HELD')
        acknowledge(room, 'A')
        request(room, c, 'A', True)
        acknowledge(room, 'A')
        drain(room)
        self.assertIsNotNone(room.seal_ready_inputs())

    def test_hold_failure_still_stops_after_remote_prefix_changes(self):
        room, c = new_room()
        request(room, c, 'A', True)
        action = acknowledge(room, 'A')
        c.applied_prefix('A', c.epoch, 1, 'd' * 64, 'c' * 64, c.attachments['A'])
        room.native_fault(action)
        self.assertEqual(c.phase, 'HELD')
        self.assertEqual(c.ready, set())


if __name__ == '__main__':
    suite = unittest.main(verbosity=2, exit=False).result
    report = dict(result='PASS' if suite.wasSuccessful() else 'FAIL', tests=suite.testsRun,
        real_loopback_tls=True, synthetic_native_input_receipts=True, synthetic_world_receipts=True,
        game_access=False, native_input_hold_installed=False, two_real_clients=False)
    run = HERE / 'checkpoint_ready_barrier_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    (run / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(folder=str(run), **report)))
    raise SystemExit(0 if suite.wasSuccessful() else 1)
