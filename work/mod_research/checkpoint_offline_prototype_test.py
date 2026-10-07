"""Fault injection for the offline launcher; only its own child is terminated."""
from datetime import datetime
import io
import json
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
import unittest

import checkpoint_offline_prototype as app
from checkpoint_test_bootstrap import WorkspaceFixtureBootstrap


class DiagnosticFaults(unittest.TestCase):
    def report(self):
        return json.loads((app.OUT/'离线原型最近诊断.json').read_text(encoding='utf-8'))

    def run_quietly(self):
        with redirect_stdout(io.StringIO()):
            return app.run()

    def test_changed_executable_is_rejected_before_process_start(self):
        original = app.file_sha
        def changed(path):
            return '0'*64 if path.name == 'checkpoint_session_ipc_fixture.exe' else original(path)
        with patch.object(app, 'file_sha', side_effect=changed), \
             patch.object(WorkspaceFixtureBootstrap, 'prepare_fixture') as prepare:
            self.assertEqual(self.run_quietly(), 1)
            prepare.assert_not_called()
        self.assertEqual(self.report()['result'], 'FAILED')

    def test_visual_hold_failure_cannot_report_pass(self):
        original = app.FakeTransport
        class BadHold(original):
            def send(self, value):
                if value['op'] == 'hold':
                    raise RuntimeError('Injected fixture visual hold failure')
                return super().send(value)
        with patch.object(app, 'FakeTransport', BadHold):
            self.assertEqual(self.run_quietly(), 1)
        report = self.report()
        self.assertFalse(report['checks']['hold_has_no_cleanup_errors'])
        self.assertNotEqual(report['result'], 'PASS_EXPECTED_HOLD')

    def test_owned_child_exit_after_arm_retains_intent(self):
        original = app.GuestTransition.poll
        killed = []
        def child_exit(flow):
            if not killed:
                process = flow.native.bootstrap.process
                process.terminate()
                process.wait(timeout=5)
                killed.append(process.pid)
            return original(flow)
        with patch.object(app.GuestTransition, 'poll', child_exit):
            self.assertEqual(self.run_quietly(), 1)
        report = self.report()
        self.assertEqual(len(killed), 1)
        self.assertTrue(report['checks']['durable_intent_before_native_arm'])
        self.assertEqual(report['journal_status'], 'INTENT')
        self.assertEqual(report['controller']['phase'], 'HELD')
        self.assertFalse(report['controller']['accept_planning_intents'])
        self.assertNotEqual(report['result'], 'PASS_EXPECTED_HOLD')


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DiagnosticFaults))
    folder = app.HERE/'checkpoint_offline_prototype_fault_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    report = dict(result='PASS' if result.wasSuccessful() else 'FAIL', cases=result.testsRun,
                  source_sha256={p.name: app.file_sha(p) for p in (
                      Path(__file__), app.HERE/'checkpoint_offline_prototype.py')},
                  game_accessed=False, provenance='FIXTURE_ONLY')
    (folder/'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(str(folder/'result.json'))
    raise SystemExit(0 if result.wasSuccessful() else 1)
