"""Real loopback TLS and separate owned peers for observed reward Ready fences."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import argparse
import hashlib
import json
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import unittest

from reward_ready_flow_fixture import ReadyModelPort, capture_inputs
from reward_menu_capture import CaptureSession
from reward_room_flow_fixture import ROOT, CONTRACT
from reward_room_flow_test import manifest, GuestProcess
from reward_room_flow import FlowError, FlowServer, envelope
from reward_ready_flow import ReadyRewardFlow, proof
from room_session import Room
from room_transport import Client, make_certificate


class ReadyPeer(GuestProcess):
    def __init__(self, folder, native_exe):
        self.output = queue.Queue()
        self.stderr = (folder / 'peer.stderr.log').open('w', encoding='utf-8')
        self.process = subprocess.Popen([sys.executable, '-u', str(Path(__file__).with_name('reward_ready_flow_fixture.py')),
                '--owned-ready-peer'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.stderr, text=True, encoding='utf-8')
        def reader():
            for line in self.process.stdout:
                self.output.put(line)
        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()
        self.initial = self.call('open', native_exe=str(native_exe) if native_exe else None,
                                 run_dir=str(folder / 'native-B'))


class Harness:
    def __init__(self, folder, native_exe):
        self.folder = folder
        folder.mkdir(parents=True)
        self.room = Room(manifest())
        self.guest = ReadyPeer(folder, native_exe)
        if native_exe:
            from reward_ready_flow_native_port import ReadyNativePort
            self.port = ReadyNativePort(native_exe, 12, folder / 'native-A')
        else:
            self.port = ReadyModelPort(12)
        cert, key, fp = make_certificate(folder / 'tls')
        self.server = FlowServer(('127.0.0.1', 0), self.room, cert, key)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.02), daemon=True)
        self.thread.start()
        config = {'host': '127.0.0.1', 'port': self.server.server_address[1], 'fingerprint': fp,
                  'greeting': {'method': 'host', 'credential': self.room.host_token, 'profile': self.room.manifest['profile']}}
        self.host = Client(**config)
        config['greeting'] = {'method': 'join', 'credential': self.room.invite, 'profile': self.room.manifest['profile']}
        self.guest.call('connect', config=config)
        for seat, action, fields in [('A', 'select_force', {'force_id': 12}), ('B', 'select_force', {'force_id': 2}),
                                     ('A', 'confirm_force', {}), ('B', 'confirm_force', {})]:
            self.checked(seat, {'action': action, 'request_id': secrets.token_hex(16),
                               'expected_revision': self.room.revision, **fields})
        self.flow = ReadyRewardFlow(folder, self.room, self.port, self.guest.initial['attachment'], CONTRACT,
                {'year': 203, 'month': 8, 'day': 11, 'phase': 'PLANNING_BOUNDARY'},
                guest_report_key=bytes.fromhex(self.guest.initial.pop('trusted_report_key')), fence_revisions={'A': 1, 'B': 1})
        self.server.flow = self.flow
        result = self.guest.call('attach', journal=str(folder / 'guest-execution.sqlite'),
                fence_journal=str(folder / 'guest-fence.sqlite'), attachments=self.flow.period.attachments)
        if not result.get('ok'):
            raise AssertionError(result)

    def request(self, seat, packet):
        return self.host.request(packet) if seat == 'A' else self.guest.call('request', packet=packet)

    def checked(self, seat, packet):
        result = self.request(seat, packet)
        if not result.get('ok'):
            raise AssertionError(result)
        return result

    def submit(self, seat):
        return self.checked(seat, envelope(self.flow.scope, 'reward_submit', request_id=secrets.token_hex(16),
                district_id=11 if seat == 'A' else 2, officer_ids=[97] if seat == 'A' else [101]))

    def ready(self, seat):
        return self.checked(seat, envelope(self.flow.scope, 'reward_ready', value=True))

    def both_ready(self):
        self.ready('A')
        self.ready('B')

    def close(self):
        self.guest.close()
        self.host.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.port.close()


class Tests(unittest.TestCase):
    native_exe = None
    run_dir = None

    def setUp(self):
        self.h = Harness(self.run_dir / self._testMethodName, self.native_exe)
        self.addCleanup(self.h.close)

    def test_two_rewards_then_observed_native_fences(self):
        h = self.h
        for seat in ('A', 'B'):
            h.submit(seat)
            h.flow.pump_one()
            self.assertTrue(h.guest.call('consume_reward')['ack']['ok'])
        h.both_ready()
        start = h.flow.begin_seal()
        self.assertEqual(start['status'], 'WAITING_GUEST_OWNER_FENCE')
        self.assertEqual(h.flow.period.phase, 'PLANNING')
        self.assertEqual(h.port.fence_setters, 1)
        with self.assertRaises(FlowError):
            h.flow.complete_seal()
        guest = h.guest.call('consume_fence')
        self.assertTrue(guest['ack']['ok'])
        self.assertEqual(h.flow.period.phase, 'PLANNING')
        result = h.flow.complete_seal()
        self.assertEqual(result['status'], 'OWNER_FENCES_CONFIRMED')
        self.assertEqual(result['cut']['sequence'], 2)
        self.assertFalse(result['native_simulation_permit'])
        self.assertFalse(result['all_input_held'])
        self.assertEqual(h.port.sample(), h.guest.call('sample')['sample'])
        self.assertEqual(h.flow.period.phase, 'SEALED')
        self.assertEqual(h.port.fence_observations, 2)

    def test_captured_menus_submit_once_through_tls_to_native_and_fences(self):
        h = self.h
        capture = CaptureSession()
        preview, context = capture_inputs(h.flow.host)
        identity = secrets.token_hex(16)
        capture.capture(preview, context, capture_id=identity, now_tick=100)
        proposal = capture.confirm(identity, preview, context, now_tick=100)
        first = h.checked('A', proposal.packet())
        duplicate = h.checked('A', capture.confirm(identity, preview, context, now_tick=100).packet())
        self.assertEqual(first['ordinal'], duplicate['ordinal'])
        self.assertTrue(duplicate['duplicate'])
        guest = h.guest.call('capture_reward')
        repeated = h.guest.call('repeat_capture')
        self.assertTrue(guest['ok'] and repeated['ok'] and repeated['duplicate'])
        self.assertEqual(guest['request_id'], repeated['request_id'])
        self.assertEqual(h.flow.status()['request_count'], 2)
        for sequence in (1, 2):
            self.assertEqual(h.flow.pump_one()['sequence'], sequence)
            self.assertTrue(h.guest.call('consume_reward')['ack']['ok'])
        h.both_ready()
        h.flow.begin_seal()
        self.assertTrue(h.guest.call('consume_fence')['ack']['ok'])
        self.assertEqual(h.flow.complete_seal()['cut']['sequence'], 2)
        self.assertEqual(h.port.calls, 2)
        self.assertEqual(h.guest.call('sample')['calls'], 2)
        self.assertFalse(proposal.native_interception)

    def test_zero_command_boundary_and_duplicate_ack(self):
        h = self.h
        h.both_ready()
        h.flow.seal()  # successor cannot take predecessor's protocol-only shortcut
        first = h.guest.call('consume_fence')
        h.flow.complete_seal()
        again = h.guest.call('consume_fence')
        self.assertEqual(again['ack']['status'], 'ALREADY_CONFIRMED')
        self.assertEqual(again['setters'], 1)
        self.assertEqual(h.flow.complete_seal()['cut']['sequence'], 0)
        self.assertEqual(h.port.fence_setters, 1)

    def test_lost_fence_ack_does_not_repeat_setter(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        first = h.guest.call('consume_fence', drop_ack=True)
        self.assertEqual(first['setters'], 1)
        with self.assertRaises(FlowError):
            h.flow.complete_seal()
        second = h.guest.call('consume_fence')
        self.assertEqual(second['setters'], 1)
        self.assertEqual(second['observations'], 2)
        self.assertTrue(second['ack']['ok'])
        self.assertEqual(h.flow.complete_seal()['status'], 'OWNER_FENCES_CONFIRMED')

    def test_one_ready_does_not_apply_any_final_fence(self):
        h = self.h
        h.ready('A')
        with self.assertRaises(FlowError):
            h.flow.begin_seal()
        self.assertEqual(h.port.fence_setters, 0)
        h.submit('B')
        h.flow.pump_one()
        self.assertTrue(h.guest.call('consume_reward')['ack']['ok'])
        self.assertEqual(h.port.calls, 1)

    def test_pending_reward_blocks_ready_and_fence(self):
        h = self.h
        h.submit('B')
        self.assertFalse(h.request('B', envelope(h.flow.scope, 'reward_ready', value=True))['ok'])
        h.ready('A')
        with self.assertRaises(FlowError):
            h.flow.begin_seal()
        self.assertEqual(h.port.fence_setters, 0)

    def test_finalization_rejects_unready_and_new_input(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        self.assertFalse(h.request('A', envelope(h.flow.scope, 'reward_ready', value=False))['ok'])
        self.assertFalse(h.request('B', envelope(h.flow.scope, 'reward_submit', request_id=secrets.token_hex(16),
                district_id=2, officer_ids=[101]))['ok'])
        with self.assertRaises(FlowError):
            h.flow.pump_one()
        self.assertEqual(h.port.calls, 0)

    def test_player_credentials_do_not_attest_physical_fence(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        body = deepcopy(h.flow.host_fence.apply(h.flow.challenge))
        body['report'] = deepcopy(h.flow.last_guest)
        reply = h.request('B', envelope(h.flow.scope, 'reward_fence_report', body=body, proof='0' * 64))
        self.assertFalse(reply['ok'])
        self.assertEqual(h.flow.fence_phase, 'HELD')
        self.assertEqual(h.guest.call('sample')['setters'], 0)
        self.assertEqual(h.port.fence_setters, 1)  # no automatic un-fence

    def test_valid_signature_cannot_reuse_old_challenge(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        real = h.guest.call('consume_fence', drop_ack=True)['body']
        real['challenge']['epoch'] = secrets.token_hex(16)
        reply = h.request('B', envelope(h.flow.scope, 'reward_fence_report', body=real,
                          proof=proof(h.flow._guest_report_key, real)))
        self.assertFalse(reply['ok'])
        self.assertEqual(h.flow.fence_phase, 'HELD')

    def test_retirement_rejects_old_commands_and_fence_reports(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        real = h.guest.call('consume_fence', drop_ack=True)['body']
        signature = proof(h.flow._guest_report_key, real)
        h.flow.retire('owned test lifecycle retired; no load executed')
        reply = h.request('B', envelope(h.flow.scope, 'reward_fence_report', body=real, proof=signature))
        self.assertFalse(reply['ok'])
        self.assertFalse(h.request('A', envelope(h.flow.scope, 'reward_ready', value=True))['ok'])
        self.assertEqual(h.flow.fence_phase, 'RETIRED')
        self.assertEqual(h.flow._guest_report_key, b'')

    def test_fence_observation_does_not_allow_host_world_replacement(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        self.assertTrue(h.guest.call('consume_fence')['ack']['ok'])
        h.port.attachment_id = secrets.token_hex(16)
        with self.assertRaises(FlowError):
            h.flow.complete_seal()
        self.assertEqual(h.flow.fence_phase, 'HELD')
        self.assertEqual(h.flow.period.ready, set())
        self.assertEqual(h.port.fence_observations, 1)


class Failures(Tests):
    def test_setter_result_without_observed_callback_is_held(self):
        h = self.h
        h.port.fake_observation = True
        h.both_ready()
        with self.assertRaises(FlowError):
            h.flow.begin_seal()
        self.assertEqual(h.flow.host_fence.status()['status'], 'UNKNOWN')
        self.assertEqual(h.flow.fence_phase, 'HELD')
        self.assertEqual(h.port.fence_setters, 1)

    def test_exception_after_setter_never_retries(self):
        h = self.h
        h.port.fail_after_setter = True
        h.both_ready()
        with self.assertRaises(RuntimeError):
            h.flow.begin_seal()
        with self.assertRaises(FlowError):
            h.flow.host_fence.apply(h.flow.challenge)
        self.assertEqual(h.port.fence_setters, 1)
        self.assertTrue(h.port.fence_requested)

    def test_host_fence_lost_after_guest_receipt_is_detected(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        h.guest.call('consume_fence')
        h.port.fence_requested = False
        with self.assertRaises(FlowError):
            h.flow.complete_seal()
        self.assertEqual(h.flow.fence_phase, 'HELD')
        self.assertEqual(h.flow.period.phase, 'HELD')

    def test_no_shortcut_from_already_confirmed_state_after_drift(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        h.guest.call('consume_fence')
        h.flow.complete_seal()
        h.port.state['forces']['12']['gold'] -= 1
        with self.assertRaises(ValueError):
            h.flow.complete_seal()
        self.assertEqual(h.flow.fence_phase, 'HELD')

    def test_late_success_cannot_overwrite_unknown_fence_outcome(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        original = h.port.observe_fence
        def conflicting_observer(revision):
            with h.flow.host_fence._db() as db:
                db.execute("UPDATE fence SET status='UNKNOWN',error='other observer failed' WHERE id=1")
            return original(revision)
        h.port.observe_fence = conflicting_observer
        with self.assertRaises(FlowError):
            h.flow.host_fence.apply(h.flow.challenge)
        self.assertEqual(h.flow.host_fence.status(), {'status': 'UNKNOWN', 'error': 'other observer failed'})

    def test_concurrent_duplicate_observation_keeps_unknown_terminal(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        entered, release, second_started = threading.Event(), threading.Event(), threading.Event()
        observations = []
        def failed_observer(revision):
            observations.append(revision)
            entered.set()
            if not release.wait(timeout=3):
                raise RuntimeError('Test synchronization timeout')
            raise RuntimeError('Injected observation failure')
        h.port.observe_fence = failed_observer
        def second():
            second_started.set()
            return h.flow.host_fence.apply(h.flow.challenge)
        with ThreadPoolExecutor(2) as pool:
            first = pool.submit(h.flow.host_fence.apply, h.flow.challenge)
            self.assertTrue(entered.wait(timeout=3))
            later = pool.submit(second)
            self.assertTrue(second_started.wait(timeout=3))
            release.set()
            with self.assertRaises(RuntimeError):
                first.result(timeout=3)
            with self.assertRaises(FlowError):
                later.result(timeout=3)
        self.assertEqual(observations, [1])
        self.assertEqual(h.flow.host_fence.status()['status'], 'UNKNOWN')
        self.assertEqual(h.port.fence_setters, 1)

    def test_retirement_revokes_retained_coordinator_cut(self):
        h = self.h
        h.both_ready()
        h.flow.begin_seal()
        h.guest.call('consume_fence')
        result = h.flow.complete_seal()
        h.flow.retire('control scope retired')
        with self.assertRaises(ValueError):
            h.flow.period.begin_simulation(result['cut'])
        self.assertEqual(h.flow.period.phase, 'HELD')

    def test_attachment_changes_during_last_sample_even_with_same_hash(self):
        h = self.h
        h.both_ready()
        original = h.port.observe
        def switch_during_post_sample():
            digest = original()
            if h.port.fence_observations > 0:
                h.port.attachment_id = secrets.token_hex(16)
            return digest  # Equal content is not proof of the same loaded world.
        h.port.observe = switch_during_post_sample
        with self.assertRaisesRegex(FlowError, 'during observation'):
            h.flow.begin_seal()
        self.assertEqual(h.flow.host_fence.status()['status'], 'UNKNOWN')
        self.assertEqual(h.flow.fence_phase, 'HELD')
        self.assertEqual(h.port.fence_setters, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-fixture', type=Path)
    args = parser.parse_args()
    tag = 'native' if args.native_fixture else 'model'
    run = Path(__file__).with_name('reward_ready_flow_runs') / (
            datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + tag + '-' + secrets.token_hex(3))
    run.mkdir(parents=True)
    paths = [ROOT / 'outputs' / 'san14-link' / name for name in
             ('reward_ready_flow.py', 'reward_room_flow.py', 'authority_reward.py', 'execution_journal.py',
              'authoritative_sync.py', 'room_transport.py', 'room_session.py', 'reward_menu_capture.py')]
    paths += [Path(__file__).with_name(name) for name in ('reward_ready_flow_test.py', 'reward_ready_flow_fixture.py',
              'reward_ready_flow_native_port.py', 'reward_room_flow_test.py', 'reward_room_flow_fixture.py',
              'reward_room_flow_native_port.py') if Path(__file__).with_name(name).exists()]
    hashes = lambda: {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    before = hashes()
    Tests.run_dir, Tests.native_exe = run, args.native_fixture
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    if not args.native_fixture:
        Failures.run_dir, Failures.native_exe = run, None
        suite.addTests(Failures(name) for name in ('test_setter_result_without_observed_callback_is_held',
                'test_exception_after_setter_never_retries', 'test_host_fence_lost_after_guest_receipt_is_detected',
                'test_no_shortcut_from_already_confirmed_state_after_drift',
                'test_late_success_cannot_overwrite_unknown_fence_outcome',
                'test_concurrent_duplicate_observation_keeps_unknown_terminal',
                'test_retirement_revokes_retained_coordinator_cut',
                'test_attachment_changes_during_last_sample_even_with_same_hash'))
    with (run / 'tests.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    summary = {'schema': 'san14.reward-ready-flow-tests.v1', 'passed': result.wasSuccessful() and before == hashes(),
               'test_count': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'execution': 'owned-native-fixture' if args.native_fixture else 'python-business-substitute',
               'loopback_tls': True, 'independent_guest_process': True, 'game_access': False,
               'native_simulation_permit': False, 'all_input_held': False,
               'sources': before, 'sources_unchanged': before == hashes()}
    if args.native_fixture:
        summary['native_result_sha256'] = hashlib.sha256((args.native_fixture.parent / 'result.json').read_bytes()).hexdigest()
    (run / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({'run': str(run), **{k: v for k, v in summary.items() if k != 'sources'}}))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
