"""Real SQLite bootstrap journal/loaded checks; all native observations are models."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import threading
import unittest

from authoritative_sync import (CheckpointPackage, CheckpointReceiver, PeriodCoordinator,
                                POLICY, SyncError, canonical)
from checkpoint_journal import CheckpointJournal, LoadHeld
from checkpoint_bootstrap_journal import BootstrapCheckpointJournal, SCHEMA

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
OUTPUT = None
EVIDENCE = []


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixture(period=1):
    scope = dict(schema='san14.authoritative-sync-scope.v1', room_id='1'*32, binding_epoch='2'*32,
        profile=dict(protocol='san14.room.v1', game_sha256='a'*64,
            adapter_contract='research-no-native-room-adapter.v1', checkpoint_sha256='b'*64, rules_sha256='c'*64),
        bindings={'A': dict(force_id=12, main_district_id=11), 'B': dict(force_id=2, main_district_id=2)},
        authority='A', policy=POLICY)
    attachments = {'A': '3'*32, 'B': '4'*32}; node = dict(year=203, month=8, day=1, phase='PLANNING_BOUNDARY')
    c = PeriodCoordinator(scope, 'EXPLICIT_BOOTSTRAP_TEST_PROJECTION', '5'*64, attachments, node)
    for side in ('A', 'B'):
        c.applied_prefix(side, c.epoch, 1, '6'*64, '5'*64, attachments[side]); c.set_ready(side, c.epoch, True)
    c.begin_simulation(c.seal_inputs())
    cut = dict(sequence=1, prefix_sha256='6'*64); loaded = {**node, 'day': 11}
    package = CheckpointPackage(scope, c.epoch, period, cut, loaded, c.state_contract, '7'*64,
        {'world.s14': b'EXPLICIT SYNTHETIC SAVE'*97, 'adapter.json': b'{}'}, source_player='A')
    receiver = CheckpointReceiver(package.manifest, package.checkpoint_id, scope, c.epoch, period, cut)
    for chunk in package.chunks(): receiver.accept(chunk)
    args = (scope, package.manifest, package.checkpoint_id, c.epoch, period, cut, attachments)
    if period == 1:
        c.offer_checkpoint('A', package.manifest); c.received('B', c.epoch, receiver)
    return c, package, receiver, args


class Cases(unittest.TestCase):
    def make(self, name, kind=BootstrapCheckpointJournal):
        folder = OUTPUT/name; folder.mkdir(); c, package, receiver, args = fixture()
        path = folder/'checkpoint.sqlite'; j = kind(path, *args, create=True); j.stage(receiver)
        return c, package, receiver, args, path, j

    def evidence(self, c, package, intent):
        host = dict(attachment=c.attachments['A'], world_sha256=package.manifest['world_sha256'], node=package.manifest['node'])
        guest = dict(attachment=c.attachments['B'], viewer_force=12, safe_boundary=True)
        receipt = dict(player='B', epoch=c.epoch, checkpoint_id=package.checkpoint_id, intent=intent,
            world_sha256=package.manifest['world_sha256'], viewer_force=2, attachment='8'*32, host_observation=host)
        return host, guest, receipt

    def test_truthful_source_to_target_and_actual_loaded(self):
        c, p, rx, args, path, j = self.make('success')
        intent = c.begin_guest_load('B', c.epoch); host, guest, receipt = self.evidence(c, p, intent)
        permit = j.reserve_load(intent, host, guest)
        self.assertTrue(permit['native_load_permitted_once']); self.assertEqual(j.identity['pre_load_viewer_force'], 12)
        self.assertEqual(j.identity['schema'], SCHEMA)
        j = BootstrapCheckpointJournal(path, *args)
        with self.assertRaises(LoadHeld): j.reserve_load(intent, host, guest)
        j.complete(receipt); j = BootstrapCheckpointJournal(path, *args)
        before_epoch = c.epoch
        result = j.apply_to_coordinator(c, host, dict(attachment='8'*32, viewer_force=2,
            world_sha256=p.manifest['world_sha256'], node=p.manifest['node'], safe_boundary=True))
        self.assertEqual(j.status()['status'], 'COMPLETED'); self.assertEqual((c.period, c.phase), (2, 'PLANNING'))
        self.assertNotEqual(c.epoch, before_epoch); self.assertFalse(c.ready)
        self.assertFalse(result['native_gameplay_enabled'])
        self.assertTrue(j.apply_to_coordinator(c, host, dict(attachment='8'*32, viewer_force=2,
            world_sha256=p.manifest['world_sha256'], node=p.manifest['node'], safe_boundary=True))['duplicate'])
        EVIDENCE.append(dict(case='source-before-target-after', before=guest, after=receipt,
                             actual_journal_loaded=True, native_observation='EXPLICIT_MODEL', ready=False))

    def test_target_before_and_source_after_are_rejected(self):
        c, p, rx, args, path, j = self.make('wrong-viewer')
        intent = c.begin_guest_load('B', c.epoch); host, guest, receipt = self.evidence(c, p, intent)
        with self.assertRaises(SyncError): j.reserve_load(intent, host, {**guest, 'viewer_force': 2})
        self.assertEqual(j.status()['status'], 'STAGED')
        j.reserve_load(intent, host, guest)
        with self.assertRaises(SyncError): j.complete({**receipt, 'viewer_force': 12})
        self.assertEqual(j.status()['status'], 'INTENT'); self.assertEqual(c.period, 1)
        # Corrupt only this owned database to prove reopen validates stored pre-view.
        with sqlite3.connect(path) as db:
            stored = json.loads(db.execute('SELECT intent FROM metadata').fetchone()[0])
            stored['guest_observation']['viewer_force'] = 2
            db.execute('UPDATE metadata SET intent=?', (canonical(stored),))
        with self.assertRaises(SyncError): BootstrapCheckpointJournal(path, *args)
        EVIDENCE.append(dict(case='opposite-viewers-refused', fake_target_before=False, source_completion=False,
                             tampered_intent_reopen=False))

    def test_callback_failure_and_reopen_never_retry(self):
        c, p, rx, args, path, j = self.make('uncertain')
        intent = c.begin_guest_load('B', c.epoch); host, guest, receipt = self.evidence(c, p, intent); calls = []
        def invoke(permit, parts):
            calls.append(permit); self.assertEqual(parts, rx.verified_parts()); raise RuntimeError('Native outcome unknown model')
        with self.assertRaises(RuntimeError): j.invoke_once(intent, host, guest, invoke)
        j = BootstrapCheckpointJournal(path, *args)
        with self.assertRaises(LoadHeld): j.invoke_once(intent, host, guest, invoke)
        self.assertEqual(len(calls), 1); self.assertTrue(j.status()['native_outcome_unknown'])
        with self.assertRaises(SyncError): j.coordinator_arguments()
        EVIDENCE.append(dict(case='uncertain-reopen', native_model_invocations=1, status='INTENT'))

    def test_ordinary_and_bootstrap_databases_mutually_reject(self):
        for label, kind, other, force in (('ordinary', CheckpointJournal, BootstrapCheckpointJournal, 2),
                                          ('bootstrap', BootstrapCheckpointJournal, CheckpointJournal, 12)):
            with self.subTest(kind=label):
                c, p, rx, args, path, j = self.make(label, kind)
                intent = c.begin_guest_load('B', c.epoch); host, guest, _ = self.evidence(c, p, intent)
                j.reserve_load(intent, host, {**guest, 'viewer_force': force})
                before = sha(path)
                with self.assertRaises(SyncError): other(path, *args)
                with self.assertRaises(FileExistsError): other(path, *args, create=True)
                self.assertEqual(sha(path), before); self.assertEqual(kind(path, *args).status()['status'], 'INTENT')
        EVIDENCE.append(dict(case='schema-mutual-refusal', ordinary_and_bootstrap_unchanged=True))

    def test_first_period_and_context_are_pinned(self):
        folder = OUTPUT/'period'; folder.mkdir(); c, p, rx, args = fixture(2)
        with self.assertRaises(SyncError): BootstrapCheckpointJournal(folder/'period2.sqlite', *args, create=True)
        self.assertFalse((folder/'period2.sqlite').exists())
        c, p, rx, args, path, j = self.make('context')
        changed = deepcopy(args[0]); changed['bindings']['A']['force_id'] = 13
        with self.assertRaises(SyncError): BootstrapCheckpointJournal(path, changed, *args[1:])
        # Even a manually altered SQL version cannot turn bootstrap identity into ordinary.
        with sqlite3.connect(path) as db: db.execute('PRAGMA user_version=1')
        with self.assertRaises(SyncError): CheckpointJournal(path, *args)
        EVIDENCE.append(dict(case='period-context-schema-pinned', period2_file_created=False))

    def test_two_connections_reserve_exactly_once(self):
        c, p, rx, args, path, j = self.make('concurrent')
        intent = c.begin_guest_load('B', c.epoch); host, guest, _ = self.evidence(c, p, intent)
        second = BootstrapCheckpointJournal(path, *args); barrier = threading.Barrier(2)
        def reserve(journal):
            barrier.wait(timeout=5)
            try: return journal.reserve_load(intent, host, guest)
            except LoadHeld: return 'HELD'
        with ThreadPoolExecutor(max_workers=2) as workers:
            rows = list(workers.map(reserve, (j, second)))
        self.assertEqual(sum(type(v) is dict for v in rows), 1); self.assertEqual(rows.count('HELD'), 1)
        self.assertEqual(BootstrapCheckpointJournal(path, *args).status()['status'], 'INTENT')
        EVIDENCE.append(dict(case='concurrent-reservation', permits=1, held=1))


if __name__ == '__main__':
    OUTPUT = PRIVATE/'checkpoint_bootstrap_journal_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True)
    paths = [Path(__file__).resolve(), HERE/'checkpoint_bootstrap_journal.py', HERE/'checkpoint_journal.py', HERE/'authoritative_sync.py']
    sources = {str(p): sha(p) for p in paths}; stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    stable = all(sha(p)==h for p,h in sources.items())
    report = dict(family='san14.checkpoint-bootstrap-journal.v1', result='PASS' if result.wasSuccessful() and result.testsRun==6 and stable else 'FAIL',
        tests=result.testsRun, sources=sources, inputs_unchanged=stable, cases=EVIDENCE,
        game_access=False, actual_sqlite=True, native_observations='EXPLICIT_MODEL',
        failures=[(str(t), text) for t,text in result.failures+result.errors])
    report['artifacts'] = {str(p): sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT/'result.json'); print(stream.getvalue())
    raise SystemExit(0 if report['result']=='PASS' else 1)
