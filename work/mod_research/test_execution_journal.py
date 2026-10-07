"""Protocol failure tests use synthetic hashes/callbacks, never the game."""
from copy import deepcopy
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
sys.path.insert(0, str(OUT))
from execution_journal import (ExecutionJournal, JournalError, ExecutionHeld,
                               compare_applied_prefixes, digest, make_intent, scope_from_room)
from room_session import Room


def bound_room():
    room = Room(json.loads((OUT / '房间势力目录.json').read_text(encoding='utf-8')))
    for p, mode, credential in [('A', 'host', room.host_token), ('B', 'join', room.invite)]:
        room.authenticate({'method': mode, 'credential': credential, 'profile': room.manifest['profile']}, p)
    for action in ('select_force', 'confirm_force'):
        for player, force in [('A', 12), ('B', 2)]:
            request = {'action': action, 'request_id': secrets.token_hex(16), 'expected_revision': room.revision}
            if action == 'select_force':
                request['force_id'] = force
            assert room.handle(player, player, request)['ok']
    return room


def command(scope, player='B'):
    return {'schema': 'san14.authority-reward-command.v1',
            'force_id': scope['bindings'][player]['force_id'],
            'game_sha256': scope['profile']['game_sha256']}


def worker(mode, folder):
    folder = Path(folder)
    data = json.loads((folder / 'worker.json').read_text(encoding='utf-8'))
    journal = ExecutionJournal(folder / 'A.sqlite', data['scope'], 'A', data['attachment'])
    def observe():
        return digest('after1') if (folder / 'effect.txt').exists() else digest('before')
    def invoke():
        if mode == '--crash-before':
            os._exit(71)
        with (folder / 'effect.txt').open('a') as stream:
            stream.write('native effect\n')
            stream.flush()
            os.fsync(stream.fileno())
        if mode == '--crash-after':
            os._exit(72)
        time.sleep(.15)
        return {'verified': True}
    try:
        receipt = journal.execute(data['intent'], observe, invoke)
        print(json.dumps({'outcome': 'applied' if receipt['native_invoked'] else 'duplicate'}))
    except ExecutionHeld:
        print(json.dumps({'outcome': 'held'}))


class JournalTests(unittest.TestCase):
    def setUp(self):
        test_root = ROOT / 'execution-journal-test-runs'
        test_root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=test_root)
        assert Path(self.temp.name).resolve().is_relative_to(test_root.resolve())
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.room = bound_room()
        self.scope = scope_from_room(self.room, secrets.token_hex(16), 'synthetic-test-state.v1', digest('before'))
        self.attachment = secrets.token_hex(16)
        self.journal = ExecutionJournal(self.path / 'A.sqlite', self.scope, 'A', self.attachment, create=True)
        self.world = digest('before')
        self.calls = 0

    def intent(self, sequence=1, player='B', request_id=None):
        return make_intent(self.scope, sequence, player, request_id or ('%032x' % sequence),
                           command(self.scope, player), self.world)

    def observe(self):
        return self.world

    def invoke(self):
        self.calls += 1
        self.world = digest('after%d' % self.calls)
        return {'verified': True, 'calls': self.calls}

    def execute(self, intent=None):
        return self.journal.execute(intent or self.intent(), self.observe, self.invoke)

    def reopen(self, **changes):
        args = {'scope': self.scope, 'local_player': 'A', 'attachment_id': self.attachment, **changes}
        return ExecutionJournal(self.path / 'A.sqlite', **args)

    def prepare_worker(self):
        (self.path / 'worker.json').write_text(json.dumps({'scope': self.scope, 'attachment': self.attachment,
                                                        'intent': self.intent()}), encoding='utf-8')

    def run_worker(self, mode):
        self.prepare_worker()
        return subprocess.run([sys.executable, '-X', 'utf8', __file__, mode, str(self.path)],
                              capture_output=True, text=True, timeout=15,
                              creationflags=subprocess.CREATE_NO_WINDOW)

    def test_bound_identity_does_not_start_game(self):
        self.assertEqual(self.room.view('A')['phase'], 'WAITING_NATIVE_ADAPTER')
        self.assertFalse(self.journal.status()['native_gameplay_enabled'])

    def test_duplicate_receipt_survives_reopen(self):
        intent = self.intent()
        first = self.execute(intent)
        second = self.reopen().execute(intent, self.observe, self.invoke)
        self.assertTrue(second['duplicate'])
        self.assertFalse(second['native_invoked'])
        self.assertEqual(first['native_result'], second['native_result'])
        self.assertEqual(self.calls, 1)

    def test_prior_duplicate_after_later_command_uses_current_tip(self):
        first = self.intent()
        self.execute(first)
        self.execute(self.intent(2, 'A'))
        self.assertTrue(self.execute(first)['duplicate'])
        self.assertEqual(self.calls, 2)

    def test_duplicate_changed_command_rejected(self):
        intent = self.intent()
        self.execute(intent)
        intent['command']['officer_ids'] = [99]
        with self.assertRaises(JournalError):
            self.execute(intent)
        self.assertEqual(self.calls, 1)

    def test_same_request_cannot_get_second_sequence(self):
        self.execute()
        with self.assertRaises(JournalError):
            self.execute(self.intent(2, request_id='%032x' % 1))
        self.assertEqual(self.calls, 1)

    def test_request_ids_are_player_scoped(self):
        self.execute()
        self.execute(self.intent(2, 'A', '%032x' % 1))
        self.assertEqual(self.calls, 2)

    def test_sequence_gap_rejected(self):
        with self.assertRaises(JournalError):
            self.execute(self.intent(2))
        self.assertEqual(self.calls, 0)

    def test_bool_sequence_rejected(self):
        with self.assertRaises(JournalError):
            self.intent(True)

    def test_wrong_player_force_rejected(self):
        intent = self.intent()
        intent['command']['force_id'] = 12
        with self.assertRaises(JournalError):
            self.execute(intent)
        self.assertEqual(self.calls, 0)

    def test_old_timeline_rejected(self):
        intent = self.intent()
        intent['scope_sha256'] = digest('old timeline')
        with self.assertRaises(JournalError):
            self.execute(intent)

    def test_attachment_change_refused(self):
        with self.assertRaises(JournalError):
            self.reopen(attachment_id=secrets.token_hex(16))

    def test_local_player_change_refused(self):
        with self.assertRaises(JournalError):
            self.reopen(local_player='B')

    def test_journal_cannot_overwrite_or_silently_recreate(self):
        with self.assertRaises(FileExistsError):
            ExecutionJournal(self.path / 'A.sqlite', self.scope, 'A', self.attachment, create=True)
        with self.assertRaises(sqlite3.OperationalError):
            ExecutionJournal(self.path / 'absent.sqlite', self.scope, 'A', self.attachment)

    def test_wrong_precondition_does_not_reserve_or_execute(self):
        intent = self.intent()
        intent['pre_state_sha256'] = digest('wrong')
        with self.assertRaises(JournalError):
            self.execute(intent)
        self.assertEqual(self.journal.status()['sequence'], 0)
        self.assertEqual(self.calls, 0)

    def test_world_drift_latches_hold_before_execution(self):
        intent = self.intent()
        self.world = digest('untracked UI write')
        with self.assertRaises(ExecutionHeld):
            self.execute(intent)
        self.world = digest('before')
        with self.assertRaises(ExecutionHeld):
            self.execute(intent)
        self.assertEqual(self.calls, 0)

    def test_loaded_old_save_cannot_reuse_applied_receipt(self):
        intent = self.intent()
        self.execute(intent)
        self.world = digest('before')
        with self.assertRaises(ExecutionHeld):
            self.reopen().execute(intent, self.observe, self.invoke)
        self.assertEqual(self.calls, 1)

    def test_failure_after_effect_never_retries(self):
        intent = self.intent()
        def failing():
            self.invoke()
            raise OSError('Lost native response')
        with self.assertRaises(ExecutionHeld):
            self.journal.execute(intent, self.observe, failing)
        with self.assertRaises(ExecutionHeld):
            self.reopen().execute(intent, self.observe, self.invoke)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.journal.status()['unknown_sequences'], [1])

    def test_post_observation_failure_never_retries(self):
        intent = self.intent()
        def observe():
            if self.calls:
                raise OSError('Cannot sample after effect')
            return self.world
        with self.assertRaises(ExecutionHeld):
            self.journal.execute(intent, observe, self.invoke)
        with self.assertRaises(ExecutionHeld):
            self.execute(intent)
        self.assertEqual(self.calls, 1)

    def test_receipt_commit_failure_never_retries(self):
        intent = self.intent()
        with closing(sqlite3.connect(self.path / 'A.sqlite')) as db:
            db.execute("CREATE TRIGGER reject_result BEFORE UPDATE OF receipt ON entries "
                       "BEGIN SELECT RAISE(ABORT, 'injected receipt failure'); END")
            db.commit()
        with self.assertRaises(ExecutionHeld):
            self.execute(intent)
        with self.assertRaises(ExecutionHeld):
            self.reopen().execute(intent, self.observe, self.invoke)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.journal.status()['unknown_sequences'], [1])

    def test_unknown_command_also_blocks_following_commands(self):
        def failing():
            self.invoke()
            raise OSError('Lost native response')
        with self.assertRaises(ExecutionHeld):
            self.journal.execute(self.intent(), self.observe, failing)
        with self.assertRaises(ExecutionHeld):
            self.execute(self.intent(2, 'A'))
        self.assertEqual(self.calls, 1)

    def test_changed_timeline_cannot_reopen_old_log(self):
        new_scope = deepcopy(self.scope)
        new_scope['timeline_epoch'] = secrets.token_hex(16)
        with self.assertRaises(JournalError):
            self.reopen(scope=new_scope)

    def test_missing_replica_cannot_pass_prefix_check(self):
        with self.assertRaises(JournalError):
            compare_applied_prefixes(self.scope, 0, {'A': self.journal.report(self.observe)})

    def test_hard_exit_before_effect_preserves_unknown_intent(self):
        result = self.run_worker('--crash-before')
        self.assertEqual(result.returncode, 71, result.stderr)
        self.assertFalse((self.path / 'effect.txt').exists())
        with self.assertRaises(ExecutionHeld):
            self.reopen().execute(self.intent(), self.observe, self.invoke)
        self.assertEqual(self.calls, 0)

    def test_hard_exit_after_effect_preserves_unknown_intent(self):
        result = self.run_worker('--crash-after')
        self.assertEqual(result.returncode, 72, result.stderr)
        self.assertEqual((self.path / 'effect.txt').read_text().count('native effect'), 1)
        self.world = digest('after1')
        with self.assertRaises(ExecutionHeld):
            self.reopen().execute(self.intent(), self.observe, self.invoke)
        self.assertEqual(self.calls, 0)

    def test_four_processes_cannot_duplicate_callback(self):
        self.prepare_worker()
        processes = [subprocess.Popen([sys.executable, '-X', 'utf8', __file__, '--race', str(self.path)],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                      creationflags=subprocess.CREATE_NO_WINDOW) for _ in range(4)]
        outcomes = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr)
            outcomes.append(json.loads(stdout)['outcome'])
        self.assertEqual(outcomes.count('applied'), 1)
        self.assertEqual((self.path / 'effect.txt').read_text().count('native effect'), 1)
        self.assertEqual(self.reopen().status()['sequence'], 1)

    def reports(self):
        a = self.journal.report(self.observe)
        b = {**a, 'local_player': 'B', 'attachment_id': secrets.token_hex(16)}
        return {'A': a, 'B': b}

    def test_both_applied_prefixes_match_but_do_not_enable_gameplay(self):
        self.execute()
        match = compare_applied_prefixes(self.scope, 1, self.reports())
        self.assertFalse(match['native_gameplay_enabled'])
        self.assertFalse(match['full_world_synchronization_proven'])

    def test_slow_replica_cannot_pass_barrier(self):
        reports = self.reports()
        with self.assertRaises(JournalError):
            compare_applied_prefixes(self.scope, 1, reports)

    def test_same_state_with_different_history_rejected(self):
        reports = self.reports()
        reports['B']['prefix_sha256'] = digest('other command history')
        with self.assertRaises(JournalError):
            compare_applied_prefixes(self.scope, 0, reports)

    def test_different_result_rejected(self):
        reports = self.reports()
        reports['B']['state_sha256'] = digest('other result')
        with self.assertRaises(JournalError):
            compare_applied_prefixes(self.scope, 0, reports)

    def test_unauthorized_replica_report_rejected(self):
        reports = self.reports()
        reports['B']['local_player'] = 'A'
        with self.assertRaises(JournalError):
            compare_applied_prefixes(self.scope, 0, reports)

    def test_different_hash_coverage_rejected(self):
        reports = self.reports()
        reports['B']['state_contract'] = 'exclude_more_fields'
        with self.assertRaises(JournalError):
            compare_applied_prefixes(self.scope, 0, reports)

    def test_report_detects_external_write(self):
        self.world = digest('unexpected change')
        with self.assertRaises(ExecutionHeld):
            self.journal.report(self.observe)
        self.assertEqual(self.journal.status()['phase'], 'HOLD')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] in ('--crash-before', '--crash-after', '--race'):
        worker(sys.argv[1], sys.argv[2])
    else:
        result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(JournalTests))
        report = {'result': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests_run': result.testsRun,
                  'failures': len(result.failures), 'errors': len(result.errors),
                  'scope': 'Durable execution gate with synthetic callbacks; includes abrupt OS-process exits and four-process contention. No game access.'}
        (ROOT / 'execution-journal-tests.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))
        raise SystemExit(0 if result.wasSuccessful() else 1)
