"""Offline tests: real loopback TLS + independent replica processes, no game."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
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
import time
import unittest

from reward_room_flow_fixture import ROOT, CONTRACT, ModelPort
import authority_reward as reward
import execution_journal as journal
from reward_room_flow import RewardFlow, Replica, FlowServer, FlowError, envelope, report_proof
from room_session import Room
from room_transport import Client, make_certificate


def manifest():
    return {'profile': {'protocol': 'san14.room.v1', 'game_sha256': reward.SUPPORTED_SHA256,
                       'adapter_contract': 'research-no-native-room-adapter.v1',
                       'checkpoint_sha256': 'c' * 64, 'rules_sha256': 'd' * 64},
            'forces': [{'id': 12, 'name': 'Fixture A', 'main_district_id': 11},
                       {'id': 2, 'name': 'Fixture B', 'main_district_id': 2}],
            'source': {'kind': 'owned-fixture-not-game'}}


class GuestProcess:
    def __init__(self, folder, native_exe=None):
        self.output = queue.Queue()
        self.stderr = (folder / 'guest.stderr.log').open('w', encoding='utf-8')
        self.process = subprocess.Popen([sys.executable, '-u', str(Path(__file__).with_name('reward_room_flow_fixture.py')),
                                        '--owned-guest-worker'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr, text=True, encoding='utf-8')
        def reader():
            for line in self.process.stdout:
                self.output.put(line)
        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()
        self.initial = self.call('open', native_exe=str(native_exe) if native_exe else None, run_dir=str(folder / 'native-B'))

    def call(self, op, **values):
        self.process.stdin.write(json.dumps({'op': op, **values}) + '\n')
        self.process.stdin.flush()
        answer = json.loads(self.output.get(timeout=20))
        if not answer['ok']:
            raise AssertionError(answer['error'])
        return answer['result']

    def close(self):
        if self.process.poll() is None:
            try:
                self.call('quit')
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()  # owned Python/fixture subprocess only
                self.process.wait(timeout=5)
        self.process.stdin.close()
        self.process.stdout.close()
        self.stderr.close()


class Harness:
    def __init__(self, folder, native_exe=None):
        self.folder = folder
        folder.mkdir(parents=True)
        self.room = Room(manifest())
        self.guest = GuestProcess(folder, native_exe)
        if native_exe:
            from reward_room_flow_native_port import NativePort
            self.port = NativePort(native_exe, 12, folder / 'native-A')
        else:
            self.port = ModelPort(12)
        cert, key, fingerprint = make_certificate(folder / 'tls')
        self.server = FlowServer(('127.0.0.1', 0), self.room, cert, key)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.02), daemon=True)
        self.thread.start()
        config = {'host': '127.0.0.1', 'port': self.server.server_address[1], 'fingerprint': fingerprint,
                  'greeting': {'method': 'host', 'credential': self.room.host_token, 'profile': self.room.manifest['profile']}}
        self.host = Client(**config)
        config['greeting'] = {'method': 'join', 'credential': self.room.invite, 'profile': self.room.manifest['profile']}
        self.guest.call('connect', config=config)
        for player, action, fields in [('A', 'select_force', {'force_id': 12}), ('B', 'select_force', {'force_id': 2}),
                                       ('A', 'confirm_force', {}), ('B', 'confirm_force', {})]:
            result = self.request(player, {'action': action, 'request_id': secrets.token_hex(16),
                                          'expected_revision': self.room.revision, **fields})
            if not result.get('ok'):
                raise AssertionError(result)
        self.flow = RewardFlow(folder, self.room, self.port, self.guest.initial['attachment'], CONTRACT,
                               {'year': 203, 'month': 8, 'day': 11, 'phase': 'PLANNING_BOUNDARY'},
                               guest_report_key=bytes.fromhex(self.guest.initial.pop('trusted_report_key')))
        self.server.flow = self.flow
        result = self.guest.call('attach', journal=str(folder / 'guest-execution.sqlite'))
        if not result.get('ok'):
            raise AssertionError(result)

    def request(self, player, packet):
        return self.host.request(packet) if player == 'A' else self.guest.call('request', packet=packet)

    def packet(self, player, **updates):
        return envelope(self.flow.scope, 'reward_submit', request_id=secrets.token_hex(16),
                        district_id=11 if player == 'A' else 2, officer_ids=[97] if player == 'A' else [101], **updates)

    def ready(self, player, value=True):
        return self.request(player, envelope(self.flow.scope, 'reward_ready', value=value))

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

    def test_concurrent_both_sides_and_independent_worlds(self):
        h = self.h
        packets = {p: h.packet(p) for p in ('A', 'B')}
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(h.request, p, packets[p]) for p in ('A', 'B')]
            results = [f.result() for f in futures]
        self.assertTrue(all(r['ok'] for r in results))
        self.assertEqual(sorted(r['ordinal'] for r in results), [1, 2])
        for sequence in (1, 2):
            self.assertEqual(h.flow.pump_one()['sequence'], sequence)
            self.assertEqual(h.flow.pump_one()['status'], 'WAITING_GUEST_APPLICATION')
            result = h.guest.call('consume')
            self.assertTrue(result['ack']['ok'])
            self.assertEqual(result['receipt']['sequence'], sequence)
        self.assertEqual(h.port.sample(), h.guest.call('sample')['sample'])
        self.assertEqual(h.port.calls, 2)
        self.assertEqual(h.guest.call('sample')['calls'], 2)
        self.assertTrue(h.ready('A')['ok'])
        self.assertTrue(h.ready('B')['ok'])
        sealed = h.flow.seal()
        self.assertEqual(sealed['cut']['sequence'], 2)
        self.assertFalse(sealed['native_gameplay_enabled'])
        self.assertFalse(sealed['native_ready_fence_verified'])
        self.assertEqual(h.room.view('A')['phase'], 'WAITING_NATIVE_ADAPTER')

    def test_lost_ack_and_duplicate_never_repeat_effects(self):
        h = self.h
        packet = h.packet('A')
        first = h.request('A', packet)
        duplicate = h.request('A', packet)
        self.assertEqual(first['ordinal'], duplicate['ordinal'])
        self.assertTrue(duplicate['duplicate'])
        h.flow.pump_one()
        applied = h.guest.call('consume', drop_ack=True)
        self.assertTrue(applied['receipt']['native_invoked'])
        self.assertFalse(h.ready('A')['ok'])
        replay = h.guest.call('consume')
        self.assertTrue(replay['receipt']['duplicate'])
        self.assertFalse(replay['receipt']['native_invoked'])
        self.assertEqual(h.port.calls, 1)
        self.assertEqual(replay['calls'], 1)
        self.assertTrue(h.guest.call('report')['ok'])
        self.assertEqual(h.request('A', packet)['status'], 'PAIRED')

    def test_one_player_ready_still_accepts_other_players_reward(self):
        h = self.h
        self.assertTrue(h.ready('A')['ok'])
        self.assertFalse(h.request('A', h.packet('A'))['ok'])
        self.assertTrue(h.request('B', h.packet('B'))['ok'])
        self.assertFalse(h.ready('B')['ok'])
        h.flow.pump_one()
        self.assertTrue(h.guest.call('consume')['ack']['ok'])
        self.assertEqual(h.flow.status()['ready'], ['A'])
        self.assertTrue(h.ready('B')['ok'])
        self.assertEqual(h.flow.seal()['cut']['sequence'], 1)

    def test_zero_commands_can_seal_without_faking_journal_seed(self):
        h = self.h
        self.assertTrue(h.ready('A')['ok'])
        self.assertTrue(h.ready('B')['ok'])
        sealed = h.flow.seal()
        self.assertEqual(sealed['cut']['sequence'], 0)
        self.assertNotEqual(h.flow.period.reports['A']['prefix_sha256'], h.flow.host.report()['prefix_sha256'])
        self.assertFalse(h.request('A', h.packet('A'))['ok'])

    def test_wrong_force_rejected_and_sequence_not_consumed(self):
        h = self.h
        packet = h.packet('A')
        packet['district_id'], packet['officer_ids'] = 2, [101]
        self.assertTrue(h.request('A', packet)['ok'])
        self.assertEqual(h.flow.pump_one()['status'], 'REJECTED')
        self.assertEqual(h.port.calls, 0)
        self.assertEqual(h.flow.host.journal.status()['sequence'], 0)
        h.request('A', h.packet('A'))
        self.assertEqual(h.flow.pump_one()['sequence'], 1)
        self.assertTrue(h.guest.call('consume')['ack']['ok'])

    def test_strict_requests_old_epoch_and_impersonation(self):
        h = self.h
        base = h.packet('A')
        changed = deepcopy(base)
        changed['force_id'] = 2
        self.assertFalse(h.request('A', changed)['ok'])
        changed = deepcopy(base)
        changed['epoch'] = 'f' * 32
        self.assertFalse(h.request('A', changed)['ok'])
        for ids in ([True], [97, 97], [], list(range(1, 18))):
            changed = deepcopy(base)
            changed['officer_ids'] = ids
            self.assertFalse(h.request('A', changed)['ok'])
        self.assertTrue(h.request('A', base)['ok'])
        changed = deepcopy(base)
        changed['officer_ids'] = [759]
        self.assertFalse(h.request('A', changed)['ok'])
        with self.assertRaises(FlowError):
            h.flow.handle('B', h.room.players['A']['connection'], base)
        self.assertEqual(h.port.calls, 0)

    def test_guest_mismatch_holds_after_actual_host_application(self):
        h = self.h
        h.request('A', h.packet('A'))
        h.flow.pump_one()
        result = h.guest.call('consume', drop_ack=True)
        bad = deepcopy(result['report'])
        bad['state_sha256'] = 'f' * 64
        # Fault injection by the trusted supervisor: a correctly attested but
        # divergent observation must fail independently of endpoint signatures.
        response = h.request('B', envelope(h.flow.scope, 'reward_report', report=bad,
                             proof=report_proof(h.flow._guest_report_key, bad)))
        self.assertFalse(response['ok'])
        self.assertEqual(h.flow.status()['flow_status'], 'HELD')
        with self.assertRaises(FlowError):
            h.flow.pump_one()
        self.assertFalse(h.ready('A')['ok'])
        self.assertEqual(h.port.calls, 1)

    def test_disconnect_does_not_replay_pending_native_command(self):
        h = self.h
        h.request('A', h.packet('A'))
        h.flow.pump_one()
        h.guest.call('disconnect')
        deadline = time.monotonic() + 3
        while h.flow.status()['flow_status'] != 'HELD' and time.monotonic() < deadline:
            threading.Event().wait(.01)
        self.assertEqual(h.flow.status()['flow_status'], 'HELD')
        with self.assertRaises(FlowError):
            h.flow.pump_one()
        self.assertEqual(h.port.calls, 1)

    def test_existing_execution_files_are_not_reset(self):
        h = self.h
        h.request('A', h.packet('A'))
        h.flow.pump_one()
        with self.assertRaises(FileExistsError):
            RewardFlow(h.folder, h.room, h.port, h.guest.initial['attachment'], CONTRACT,
                       {'year': 203, 'month': 8, 'day': 11, 'phase': 'PLANNING_BOUNDARY'},
                       guest_report_key=secrets.token_bytes(32))
        self.assertEqual(h.flow.status()['requests'][0]['status'], 'AWAITING_B')
        self.assertEqual(h.port.calls, 1)

    def test_authority_intent_rebuilt_for_guest_viewer(self):
        h = self.h
        h.request('B', h.packet('B'))
        h.flow.pump_one()
        with h.flow.db() as db:
            intent = json.loads(db.execute('SELECT intent FROM requests').fetchone()[0])
        self.assertEqual(intent['command']['force_id'], 2)
        result = h.guest.call('consume')
        self.assertTrue(result['ack']['ok'])
        self.assertEqual(result['receipt']['intent_sha256'], journal.digest(intent))
        self.assertEqual(h.port.viewer, 12)
        self.assertEqual(h.port.sample()['forces']['2']['ap'], 9)

    def test_room_client_cannot_forge_matching_guest_execution(self):
        h = self.h
        h.request('A', h.packet('A'))
        h.flow.pump_one()
        status = h.request('B', {'action': 'reward_status'})
        host = status['host']
        forged = {'schema': 'san14.applied-prefix.v1', 'scope_sha256': journal.digest(h.flow.scope),
                  'local_player': 'B', 'attachment_id': h.guest.initial['attachment'],
                  'sequence': host['sequence'], 'state_sha256': host['state_sha256'],
                  'prefix_sha256': host['prefix_sha256'], 'state_contract': CONTRACT}
        response = h.request('B', envelope(h.flow.scope, 'reward_report', report=forged, proof='0' * 64))
        self.assertFalse(response['ok'])
        self.assertIn('attestation', response['error'])
        self.assertEqual(h.guest.call('sample')['calls'], 0)
        self.assertEqual(h.flow.status()['requests'][0]['status'], 'AWAITING_B')
        with self.assertRaises(FlowError):
            h.flow.seal()

    def test_signed_report_bound_to_guest_attachment(self):
        h = self.h
        original = deepcopy(h.flow.last_guest)
        original['attachment_id'] = secrets.token_hex(16)
        reply = h.request('B', envelope(h.flow.scope, 'reward_report', report=original,
                          proof=report_proof(h.flow._guest_report_key, original)))
        self.assertFalse(reply['ok'])
        self.assertIn('attachment', reply['error'])
        self.assertEqual(h.port.calls, 0)

    def test_old_confirmed_ack_does_not_poison_next_pending_command(self):
        h = self.h
        h.request('A', h.packet('A'))
        h.flow.pump_one()
        first = h.guest.call('consume')
        h.request('B', h.packet('B'))
        h.flow.pump_one()
        old = first['report']
        response = h.request('B', envelope(h.flow.scope, 'reward_report', report=old,
                            proof=report_proof(h.flow._guest_report_key, old)))
        self.assertTrue(response['ok'])
        self.assertEqual(response['status'], 'ALREADY_CONFIRMED')
        self.assertEqual(h.flow.status()['requests'][-1]['status'], 'AWAITING_B')
        self.assertEqual(h.flow.status()['flow_status'], 'PLANNING')
        self.assertTrue(h.guest.call('consume')['ack']['ok'])
        self.assertEqual(h.port.calls, 2)
        self.assertEqual(h.guest.call('sample')['calls'], 2)


class ModelFailures(Tests):
    """Injected failures only available in the Python business substitute."""
    # Only explicitly named methods below are loaded for this subclass.
    def test_unknown_after_native_write_never_retries(self):
        h = self.h
        h.port.fail_after_effect = True
        h.request('A', h.packet('A'))
        with self.assertRaises(journal.ExecutionHeld):
            h.flow.pump_one()
        self.assertEqual(h.flow.status()['flow_status'], 'HELD')
        self.assertEqual(h.flow.host.journal.status()['unknown_sequences'], [1])
        with self.assertRaises(FlowError):
            h.flow.pump_one()
        self.assertEqual(h.port.calls, 1)

    def test_host_state_drift_before_dispatch_holds(self):
        h = self.h
        h.request('A', h.packet('A'))
        h.port.state['forces']['12']['gold'] -= 1
        with self.assertRaises(journal.ExecutionHeld):
            h.flow.pump_one()
        self.assertEqual(h.flow.status()['flow_status'], 'HELD')
        self.assertEqual(h.port.calls, 0)

    def test_replica_out_of_order_intent_rejected_without_invocation(self):
        h = self.h
        command = h.flow.host.command(12, 11, [97])
        intent = journal.make_intent(h.flow.scope, 2, 'A', secrets.token_hex(16), command, h.port.observe())
        with self.assertRaises(journal.JournalError):
            h.flow.host.apply(intent)
        self.assertEqual(h.port.calls, 0)

    def test_attachment_change_holds_dispatch(self):
        h = self.h
        h.request('A', h.packet('A'))
        h.port.attachment_id = secrets.token_hex(16)
        with self.assertRaises(FlowError):
            h.flow.pump_one()
        self.assertEqual(h.flow.status()['flow_status'], 'HELD')
        self.assertEqual(h.flow.status()['requests'][0]['status'], 'QUEUED')
        self.assertEqual(h.port.calls, 0)

    def test_attachment_change_holds_ready_and_clears_other_ready(self):
        h = self.h
        self.assertTrue(h.ready('B')['ok'])
        h.port.attachment_id = secrets.token_hex(16)
        self.assertFalse(h.ready('A')['ok'])
        self.assertEqual(h.flow.status()['flow_status'], 'HELD')
        self.assertEqual(h.flow.status()['ready'], [])

    def test_attachment_change_holds_seal(self):
        h = self.h
        self.assertTrue(h.ready('A')['ok'])
        self.assertTrue(h.ready('B')['ok'])
        h.port.attachment_id = secrets.token_hex(16)
        with self.assertRaises(FlowError):
            h.flow.seal()
        self.assertEqual(h.flow.status()['flow_status'], 'HELD')
        self.assertEqual(h.flow.status()['ready'], [])

    def test_state_drift_holds_ready(self):
        h = self.h
        h.port.state['forces']['12']['gold'] -= 1
        self.assertFalse(h.ready('A')['ok'])
        self.assertEqual(h.flow.status()['flow_status'], 'HELD')

    def test_unknown_context_failure_is_not_player_rejection(self):
        h = self.h
        h.request('A', h.packet('A'))
        h.port.context = lambda force: {}  # trusted adapter malfunction
        with self.assertRaises(KeyError):
            h.flow.pump_one()
        self.assertEqual(h.flow.status()['flow_status'], 'HELD')
        self.assertEqual(h.flow.status()['requests'][0]['status'], 'QUEUED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-fixture', type=Path)
    args = parser.parse_args()
    run = Path(__file__).with_name('reward_room_flow_runs') / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    sources = [ROOT / 'outputs' / 'san14-link' / name for name in
               ('reward_room_flow.py', 'authority_reward.py', 'execution_journal.py',
                'authoritative_sync.py', 'room_session.py', 'room_transport.py')]
    sources += [Path(__file__).with_name(name) for name in
                ('reward_room_flow_test.py', 'reward_room_flow_fixture.py', 'reward_room_flow_native_port.py')]
    fingerprints = lambda: {str(p.relative_to(ROOT)).replace('\\', '/'):
                            hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    before = fingerprints()
    Tests.run_dir, Tests.native_exe = run, args.native_fixture
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    if not args.native_fixture:
        ModelFailures.run_dir, ModelFailures.native_exe = run, None
        suite.addTests(ModelFailures(name) for name in ('test_unknown_after_native_write_never_retries',
                       'test_host_state_drift_before_dispatch_holds', 'test_replica_out_of_order_intent_rejected_without_invocation',
                       'test_attachment_change_holds_dispatch', 'test_attachment_change_holds_ready_and_clears_other_ready',
                       'test_attachment_change_holds_seal', 'test_state_drift_holds_ready',
                       'test_unknown_context_failure_is_not_player_rejection'))
    with (run / 'tests.log').open('w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    summary = {'schema': 'san14.reward-room-flow-offline.v1', 'passed': result.wasSuccessful(),
               'test_count': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'execution': 'owned-native-fixture' if args.native_fixture else 'python-business-substitute',
               'loopback_tls': True, 'independent_guest_process': True,
               'game_accessed': False, 'full_world_verified': False, 'native_gameplay_enabled': False,
               'sources': before, 'sources_unchanged': before == fingerprints(),
               'trusted_guest_report_key_provisioning': 'owned-stdio-supervisor-only;not-production-bootstrap',
               'native_ready_fence_verified': False}
    if args.native_fixture:
        summary['native_fixture_result_sha256'] = hashlib.sha256(
                (args.native_fixture.parent / 'result.json').read_bytes()).hexdigest()
    summary['passed'] = summary['passed'] and summary['sources_unchanged']
    (run / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({'run': str(run), **{k: v for k, v in summary.items() if k != 'sources'}}))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
