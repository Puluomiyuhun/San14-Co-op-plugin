"""Durable checkpoint adversarial tests; fixture bytes, zero SAN14 access."""
from copy import deepcopy
from contextlib import closing
from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'outputs' / 'san14-link'
sys.path.insert(0, str(OUT))
from authoritative_sync import *
from checkpoint_journal import CheckpointJournal, LoadHeld
from test_authoritative_sync import bound_room, NODE, NEXT, OLD, HOST


def open_identity(path, identity, **kw):
    m = identity['manifest']
    return CheckpointJournal(path, identity['scope'], m, identity['checkpoint_id'],
                             m['epoch'], m['period'], m['cut'], identity['attachments'], **kw)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='checkpoint-journal-', dir=HERE)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'guest.sqlite'
        self.scope = scope_from_room(bound_room())
        self.c = PeriodCoordinator(self.scope, 'fixture-world.v1', digest(OLD),
                                   {'A': 'a' * 32, 'B': 'b' * 32}, NODE)
        for p in ('A', 'B'):
            self.c.set_ready(p, self.c.epoch, True)
        self.c.begin_simulation(self.c.seal_inputs())
        cut = {k: self.c.seal[k] for k in ('sequence', 'prefix_sha256')}
        self.package = CheckpointPackage(self.scope, self.c.epoch, self.c.period, cut,
            NEXT, self.c.state_contract, digest(HOST),
            {'world.s14': canonical(HOST), 'adapter.json': b'{"fixture":true}'}, source_player='A')
        self.c.offer_checkpoint('A', self.package.manifest)
        self.receiver = CheckpointReceiver(self.package.manifest, self.package.checkpoint_id,
                                           self.scope, self.c.epoch, self.c.period, cut)
        for ch in self.package.chunks():
            self.receiver.accept(ch)
        self.identity = {'scope': self.scope, 'manifest': self.package.manifest,
                         'checkpoint_id': self.package.checkpoint_id,
                         'attachments': deepcopy(self.c.attachments)}
        self.j = open_identity(self.path, self.identity, create=True)
        self.host = {'attachment': 'a' * 32, 'world_sha256': digest(HOST), 'node': NEXT}
        self.guest = {'attachment': 'b' * 32, 'viewer_force': 2, 'safe_boundary': True}
        self.token = 'f' * 32

    def reserve(self):
        self.j.stage(self.receiver)
        return self.j.reserve_load(self.token, self.host, self.guest)

    def receipt(self):
        return {'player': 'B', 'epoch': self.c.epoch, 'checkpoint_id': self.package.checkpoint_id,
                'intent': self.token, 'world_sha256': digest(HOST), 'viewer_force': 2,
                'attachment': 'c' * 32, 'host_observation': deepcopy(self.host)}

    def reopened(self):
        return open_identity(self.path, self.identity)

    def current_guest(self):
        return {'attachment': 'c' * 32, 'viewer_force': 2, 'world_sha256': digest(HOST),
                'node': NEXT, 'safe_boundary': True}

    def test_staged_bytes_survive_reopen(self):
        self.j.stage(self.receiver)
        self.assertEqual(self.reopened().verified_parts(), self.receiver.verified_parts())
        self.assertFalse(self.reopened().status()['native_attempt_reserved'])

    def test_repeated_stage_idempotent(self):
        self.j.stage(self.receiver)
        self.assertTrue(self.reopened().stage(self.receiver)['duplicate'])

    def test_missing_file_is_not_recreated(self):
        path = self.path.parent / 'missing.sqlite'
        with self.assertRaises(sqlite3.OperationalError):
            open_identity(path, self.identity)
        self.assertFalse(path.exists())

    def test_create_refuses_existing_history(self):
        with self.assertRaises(FileExistsError):
            open_identity(self.path, self.identity, create=True)

    def test_wrong_binding_reopen(self):
        changed = deepcopy(self.identity)
        changed['attachments']['B'] = 'd' * 32
        with self.assertRaises(SyncError):
            open_identity(self.path, changed)

    def test_foreign_scope_rejected(self):
        changed = deepcopy(self.identity)
        changed['scope']['room_id'] = 'e' * 32
        with self.assertRaises(SyncError):
            open_identity(self.path, changed)

    def test_wrong_epoch_or_cut_or_period_rejected(self):
        m = self.package.manifest
        for epoch, period, cut in [('e' * 32, m['period'], m['cut']),
                                  (m['epoch'], m['period'] + 1, m['cut']),
                                  (m['epoch'], m['period'], {'sequence': 1, 'prefix_sha256': 'a' * 64}),
                                  (m['epoch'], True, m['cut'])]:
            with self.assertRaises(SyncError):
                CheckpointJournal(self.path, self.scope, m, self.package.checkpoint_id,
                                  epoch, period, cut, self.identity['attachments'])

    def test_incomplete_receiver_not_staged(self):
        m = self.package.manifest
        r = CheckpointReceiver(m, self.package.checkpoint_id, self.scope,
                               self.c.epoch, self.c.period, m['cut'])
        r.accept(next(self.package.chunks()))
        with self.assertRaises(SyncError):
            self.j.stage(r)
        self.assertEqual(self.j.status()['status'], 'EMPTY')

    def test_bad_part_bytes_not_staged(self):
        parts = self.receiver.verified_parts()
        parts['world.s14'] = b'x' * len(parts['world.s14'])
        with self.assertRaises(SyncError):
            self.j.stage_parts(parts)
        self.assertEqual(self.j.status()['status'], 'EMPTY')

    def test_fixed_part_names_only(self):
        parts = self.receiver.verified_parts()
        parts['../world.s14'] = parts.pop('world.s14')
        with self.assertRaises(SyncError):
            self.j.stage_parts(parts)

    def test_staging_is_one_transaction(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER fail_world BEFORE INSERT ON parts WHEN NEW.name='world.s14' "
                       "BEGIN SELECT RAISE(ABORT,'simulated second-part failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.j.stage(self.receiver)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM parts').fetchone()[0], 0)
            db.execute('DROP TRIGGER fail_world')
        self.assertEqual(self.j.status()['status'], 'EMPTY')
        self.j.stage(self.receiver)

    def test_reserve_before_staging_rejected(self):
        with self.assertRaises(SyncError):
            self.j.reserve_load(self.token, self.host, self.guest)

    def test_changed_preload_observations_do_not_consume_intent(self):
        self.j.stage(self.receiver)
        bad_host = deepcopy(self.host); bad_host['attachment'] = 'd' * 32
        bad_guest = deepcopy(self.guest); bad_guest['attachment'] = 'd' * 32
        busy_guest = deepcopy(self.guest); busy_guest['safe_boundary'] = False
        wrong_force = deepcopy(self.guest); wrong_force['viewer_force'] = 12
        for host, guest in [(bad_host, self.guest), (self.host, bad_guest),
                            (self.host, busy_guest), (self.host, wrong_force)]:
            with self.assertRaises(SyncError):
                self.j.reserve_load(self.token, host, guest)
            self.assertEqual(self.j.status()['status'], 'STAGED')
        self.j.reserve_load(self.token, self.host, self.guest)

    def test_tampered_durable_bytes_block_permission(self):
        self.j.stage(self.receiver)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE parts SET data=? WHERE name='world.s14'", (b'bad',))
        with self.assertRaises(SyncError):
            self.j.reserve_load(self.token, self.host, self.guest)
        self.assertFalse(self.j.status()['native_attempt_reserved'])

    def test_reopened_intent_never_reserves_again(self):
        self.reserve()
        with self.assertRaises(LoadHeld):
            self.reopened().reserve_load(self.token, self.host, self.guest)
        with self.assertRaises(LoadHeld):
            self.reopened().reserve_load('e' * 32, self.host, self.guest)

    def test_native_callback_sees_committed_intent(self):
        self.j.stage(self.receiver)
        calls = []
        def invoke(permit, parts):
            self.assertTrue(self.reopened().status()['native_outcome_unknown'])
            self.assertEqual(parts, self.receiver.verified_parts())
            calls.append(permit)
            raise RuntimeError('simulated native failure/unknown outcome')
        with self.assertRaises(RuntimeError):
            self.j.invoke_once(self.token, self.host, self.guest, invoke)
        with self.assertRaises(LoadHeld):
            self.reopened().invoke_once(self.token, self.host, self.guest, invoke)
        self.assertEqual(len(calls), 1)

    def test_process_crash_after_reserve_holds_restart(self):
        self.j.stage(self.receiver)
        args = self.child_args('--crash-after-reserve')
        done = subprocess.run(args, capture_output=True, text=True, **subprocess_options())
        self.assertEqual(done.returncode, 17, done.stderr)
        with self.assertRaises(LoadHeld):
            self.reopened().reserve_load(self.token, self.host, self.guest)

    def child_args(self, action):
        params = {'identity': self.identity, 'host': self.host, 'guest': self.guest, 'token': self.token}
        data = self.path.parent / 'child-params.json'
        data.write_text(json.dumps(params), encoding='utf-8')
        return [sys.executable, str(Path(__file__).resolve()), action, str(self.path), str(data)]

    def test_two_processes_reserve_only_once(self):
        self.j.stage(self.receiver)
        args = self.child_args('--reserve')
        processes = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, **subprocess_options()) for _ in range(2)]
        outputs = []
        for p in processes:
            out, err = p.communicate(timeout=30)
            self.assertEqual(p.returncode, 0, err)
            outputs.append(out.strip())
        self.assertEqual(sorted(outputs), ['HELD', 'RESERVED'])

    def test_late_verified_receipt_completes_original_intent(self):
        self.reserve()
        self.reopened().complete(self.receipt())
        self.assertEqual(self.reopened().status()['status'], 'COMPLETED')
        with self.assertRaises(LoadHeld):
            self.reopened().reserve_load(self.token, self.host, self.guest)

    def test_receipt_without_intent_rejected(self):
        self.j.stage(self.receiver)
        with self.assertRaises(SyncError):
            self.j.complete(self.receipt())

    def test_equal_receipt_is_idempotent_after_reopen(self):
        self.reserve()
        self.j.complete(self.receipt())
        self.assertTrue(self.reopened().complete(self.receipt())['duplicate'])

    def test_conflicting_fresh_attachment_receipt_rejected(self):
        self.reserve()
        self.j.complete(self.receipt())
        receipt = self.receipt(); receipt['attachment'] = 'd' * 32
        with self.assertRaises(SyncError):
            self.reopened().complete(receipt)

    def test_pending_intent_cannot_supply_loaded_arguments(self):
        self.reserve()
        with self.assertRaises(SyncError):
            self.j.coordinator_arguments()

    def test_receipt_bridge_continues_existing_coordinator_once(self):
        self.j.stage(self.receiver)
        self.c.received('B', self.c.epoch, self.receiver)
        self.token = self.c.begin_guest_load('B', self.c.epoch)
        self.j.reserve_load(self.token, self.host, self.guest)
        self.j.complete(self.receipt())
        result = self.reopened().apply_to_coordinator(self.c, self.host, self.current_guest())
        self.assertFalse(result['duplicate'])
        self.assertEqual(self.c.phase, 'PLANNING')
        self.assertEqual(self.c.period, 2)
        self.assertEqual(self.c.attachments['B'], 'c' * 32)
        self.assertTrue(self.reopened().apply_to_coordinator(self.c, self.host, self.current_guest())['duplicate'])
        self.assertEqual(len(self.c.trace), 1)
        self.assertFalse(self.c.status()['native_gameplay_enabled'])

    def test_bridge_rejects_changed_old_guest_attachment(self):
        self.j.stage(self.receiver)
        self.c.received('B', self.c.epoch, self.receiver)
        self.token = self.c.begin_guest_load('B', self.c.epoch)
        self.j.reserve_load(self.token, self.host, self.guest)
        self.j.complete(self.receipt())
        self.c.attachments['B'] = 'e' * 32
        with self.assertRaises(SyncError):
            self.j.apply_to_coordinator(self.c, self.host, self.current_guest())
        self.assertEqual(self.c.phase, 'RECONCILING')

    def test_bridge_does_not_recover_new_host_coordinator(self):
        self.reserve(); self.j.complete(self.receipt())
        replacement = PeriodCoordinator(self.scope, self.c.state_contract, digest(OLD),
                                        self.identity['attachments'], NODE)
        with self.assertRaises(SyncError):
            self.j.apply_to_coordinator(replacement, self.host, self.current_guest())
        self.assertFalse(self.j.status()['host_restart_recovery_implemented'])

    def test_caller_mutations_cannot_rebind_identity(self):
        original = self.j.identity
        self.identity['attachments']['B'] = 'e' * 32
        self.scope['bindings']['B']['force_id'] = 3
        copy = self.j.identity; copy['attachments']['A'] = 'd' * 32
        self.assertEqual(self.j.identity, original)

    def test_completed_receipt_requires_fresh_live_games_on_delivery(self):
        self.j.stage(self.receiver)
        self.c.received('B', self.c.epoch, self.receiver)
        self.token = self.c.begin_guest_load('B', self.c.epoch)
        self.j.reserve_load(self.token, self.host, self.guest)
        self.j.complete(self.receipt())
        changed_host = deepcopy(self.host); changed_host['attachment'] = 'e' * 32
        changed_guest = self.current_guest(); changed_guest['attachment'] = 'd' * 32
        rollback_guest = self.current_guest(); rollback_guest['world_sha256'] = digest(OLD)
        for host, guest in [(changed_host, self.current_guest()),
                            (self.host, changed_guest), (self.host, rollback_guest)]:
            with self.assertRaises(SyncError):
                self.reopened().apply_to_coordinator(self.c, host, guest)
            self.assertEqual(self.c.phase, 'RECONCILING')


def receipt_rejection(name, mutate):
    def run(self):
        self.reserve(); receipt = self.receipt(); mutate(receipt)
        with self.assertRaises(SyncError):
            self.j.complete(receipt)
        self.assertTrue(self.reopened().status()['native_outcome_unknown'])
    run.__name__ = 'test_bad_receipt_' + name
    setattr(JournalTests, run.__name__, run)


for name, field, value in [('owner', 'player', 'A'), ('epoch', 'epoch', '0' * 32),
    ('checkpoint', 'checkpoint_id', '0' * 64), ('intent', 'intent', '0' * 32),
    ('world', 'world_sha256', '0' * 64), ('force', 'viewer_force', 12),
    ('force_type', 'viewer_force', 2.0), ('old_guest_attachment', 'attachment', 'b' * 32),
    ('host_attachment_reused', 'attachment', 'a' * 32)]:
    receipt_rejection(name, lambda r, f=field, v=value: r.__setitem__(f, v))
receipt_rejection('host_drift', lambda r: r['host_observation'].__setitem__('world_sha256', 'e' * 64))
receipt_rejection('host_reload', lambda r: r['host_observation'].__setitem__('attachment', 'e' * 32))
receipt_rejection('host_date', lambda r: r['host_observation'].__setitem__('node', NODE))
receipt_rejection('host_date_type', lambda r: r['host_observation']['node'].__setitem__('year', 203.0))
receipt_rejection('extra_field', lambda r: r.__setitem__('extra', True))


def subprocess_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('--reserve', '--crash-after-reserve'):
        params = json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))
        j = open_identity(sys.argv[2], params['identity'])
        try:
            j.reserve_load(params['token'], params['host'], params['guest'])
        except LoadHeld:
            print('HELD')
        else:
            if sys.argv[1] == '--crash-after-reserve':
                os._exit(17)
            print('RESERVED')
    else:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(JournalTests))
        (HERE / 'checkpoint-journal-tests.json').write_text(json.dumps({
            'schema': 'san14.checkpoint-journal-tests.v1', 'tests_run': result.testsRun,
            'failures': len(result.failures), 'errors': len(result.errors),
            'result': 'PASS' if result.wasSuccessful() else 'FAIL',
            'separate_process_concurrent_reservation': True,
            'abrupt_process_exit_after_committed_intent': True,
            'game_calls': 0, 'game_memory_writes': 0, 'game_files_changed': False,
            'host_restart_recovery_implemented': False,
            'limits': 'Fixture worlds and trusted fake observations. No native load, full-state proof or complete room recovery.'
        }, indent=2) + '\n', encoding='utf-8')
        sys.exit(not result.wasSuccessful())
