"""Re-use the full Ready/TLS suite with the broader owned native interlock.

Explicit test dependency substitution only: unchanged Room/Ready code and
unchanged suite, two actual native children, independent B Python consumer.
No game discovery, no automatic native permit, no source files rewritten.
"""
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
import unittest

from reward_room_flow_fixture import ROOT
from reward_interlock_native_port import InterlockNativePort, validate_interlock


def bind_test_port():
    import reward_ready_flow_native_port as original_port
    original_port.ReadyNativePort = InterlockNativePort


def peer():
    bind_test_port()
    from reward_ready_flow_fixture import worker
    worker()


class EvidenceTests(unittest.TestCase):
    def test_each_missing_consumer_is_rejected(self):
        valid = dict(input_missing_mask=31, input_interlock_error=0, input_gate_revision=2,
                     input_interlock_uncertain=False, all_input_held=False, room_ready=False,
                     save_authorized=False, native_gameplay_enabled=False, input_coverage_mask=7,
                     input_observation=1, game_finally_delta=1, global_ui_suppressed_delta=1,
                     panel_suppressed_delta=1)
        validate_interlock(valid, observed=True)
        for field in ('game_finally_delta', 'global_ui_suppressed_delta', 'panel_suppressed_delta'):
            with self.subTest(field=field):
                bad = deepcopy(valid)
                bad[field] = 0
                with self.assertRaises(ValueError):
                    validate_interlock(bad, observed=True)

    def test_partial_coverage_cannot_promote_capabilities(self):
        valid = dict(input_missing_mask=31, input_interlock_error=0, input_gate_revision=2,
                     input_interlock_uncertain=False, all_input_held=False, room_ready=False,
                     save_authorized=False, native_gameplay_enabled=False, input_coverage_mask=0,
                     game_finally_delta=0, global_ui_suppressed_delta=0, panel_suppressed_delta=0)
        validate_interlock(valid, observed=False)
        for field, value in [('input_missing_mask', 0), ('input_interlock_uncertain', True),
                             ('input_interlock_error', 1), ('input_gate_revision', True),
                             ('input_coverage_mask', 7), ('game_finally_delta', 1),
                             ('all_input_held', True), ('room_ready', True),
                             ('save_authorized', True), ('native_gameplay_enabled', True)]:
            with self.subTest(field=field):
                bad = deepcopy(valid)
                bad[field] = value
                with self.assertRaises(ValueError):
                    validate_interlock(bad, observed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-fixture', type=Path, required=True)
    args = parser.parse_args()
    import reward_ready_flow_test as previous
    from reward_room_flow_test import GuestProcess
    class InterlockPeer(GuestProcess):
        def __init__(self, folder, native_exe):
            self.output = queue.Queue()
            self.stderr = (folder / 'peer.stderr.log').open('w', encoding='utf-8')
            self.process = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()),
                    '--owned-interlock-peer'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=self.stderr, text=True, encoding='utf-8')
            def reader():
                for line in self.process.stdout:
                    self.output.put(line)
            self.reader = threading.Thread(target=reader, daemon=True)
            self.reader.start()
            self.initial = self.call('open', native_exe=str(native_exe), run_dir=str(folder / 'native-B'))
    bind_test_port()
    previous.ReadyPeer = InterlockPeer
    run = Path(__file__).with_name('reward_interlock_flow_runs') / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + secrets.token_hex(3))
    run.mkdir(parents=True)
    paths = [ROOT / 'outputs/san14-link' / n for n in ('reward_ready_flow.py', 'reward_room_flow.py',
             'authority_reward.py', 'execution_journal.py', 'authoritative_sync.py', 'room_transport.py',
             'room_session.py', 'reward_menu_capture.py')]
    paths += [Path(__file__).with_name(n) for n in ('reward_interlock_flow_test.py', 'reward_interlock_native_port.py',
              'reward_ready_flow_test.py', 'reward_ready_flow_fixture.py', 'reward_ready_flow_native_port.py',
              'reward_room_flow_test.py', 'reward_room_flow_fixture.py', 'reward_room_flow_native_port.py')]
    hashes = lambda: {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    before = hashes()
    previous.Tests.run_dir, previous.Tests.native_exe = run, args.native_fixture
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(previous.Tests)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(EvidenceTests))
    with (run / 'tests.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    # Independently inspect actual per-process transcripts; mere setter returns
    # never count as Game/UI/panel observations. Not all negative cases set fences.
    evidence_rows = []
    for path in sorted(run.glob('*/native-*/ipc.jsonl')):
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        observations = []
        for row in rows:
            # The frozen NativePort transcript has request/reply pairs.
            response = row['packet'] if row.get('direction') == 'response' else {}
            if response.get('observed') is True:
                validate_interlock(response, observed=True)
                observations.append(response['input_observation'])
        evidence_rows.append(dict(path=path.relative_to(run).as_posix(), observations=observations))
    unchanged = before == hashes()
    observed_sides = {Path(r['path']).parts[-2] for r in evidence_rows if r['observations']}
    observed_both = observed_sides == {'native-A', 'native-B'}
    summary = dict(schema='san14.reward-interlock-flow-tests.v1', passed=result.wasSuccessful() and unchanged and observed_both,
                   test_count=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                   tls_native_cases=11, structural_evidence_cases=2, sources=before, sources_unchanged=unchanged,
                   native_result_sha256=hashlib.sha256((args.native_fixture.parent / 'result.json').read_bytes()).hexdigest(),
                   loopback_tls=True, independent_guest_process=True, two_owned_native_children=True,
                   extended_evidence=evidence_rows, extended_observed_both_sides=observed_both,
                   game_access=False, all_input_held=False,
                   native_simulation_permit=False, wire_coverage='user-callback-and-reward-save-admission.v1',
                   extra_coverage_local_only=True)
    (run / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'run': str(run), **{k: v for k, v in summary.items() if k not in ('sources', 'extended_evidence')}}))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--owned-interlock-peer']:
        peer()
    else:
        raise SystemExit(main())
