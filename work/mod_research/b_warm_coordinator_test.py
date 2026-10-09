"""Actual Windows staging/leases; the native coordinator port is a named double."""
import ctypes as C
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
sys.path[:0] = [str(PRIVATE/'python_deps'), str(ROOT/'outputs/san14-link')]
import b_warm_coordinator as coordinator
import b_warm_staging as files
from b_warm_profile_contract import Profile, Date, Identity, validate_profile

OUTPUT = None
EVIDENCE = []


def profile(data, before, loaded, current):
    value = Profile()
    value.file.name = files.NAME.encode('ascii')
    value.file.slot = 63; value.file.size = len(data)
    value.file.sha256[:] = hashlib.sha256(data).digest()
    value.before = Date(203, 8, before); value.loaded = Date(203, 8, loaded)
    value.source = Identity(666, 12, 11); value.target = Identity(952, 2, 2)
    value.currentForce = current
    return validate_profile(value)


def write_is_blocked(path):
    """Actual CreateFileW writer attempt, not a lease boolean substitute."""
    k = files.kernel()
    handle = k.CreateFileW(str(path), 0x40000000, 7, None, 3, 0, None)
    if handle not in (None, C.c_void_p(-1).value):
        k.CloseHandle(handle)
        return False
    return C.get_last_error() == 32


class NativePortDouble:
    """Only native loading/handover are substituted; real file API is untouched."""
    def __init__(self, case, target, first, second):
        self.case, self.target, self.first, self.second = case, target, first, second
        self.events = []; self.current = None; self.reader = None; self.finished = False
        self.abort_lease_blocked = None

    def open_bank(self, index):
        self.events.append(['open', index]); return index

    def authorize_second(self, bank, _):
        self.events.append(['handover', bank])
        if self.case == 'handover-refused': raise ValueError('Native handover double refuses')
        if self.case == 'first-drift': self.target.write_bytes(b'external changed first file')
        if self.case == 'stage-conflict': self.reader = files.Handle(self.target, share=1)

    def load(self, bank, p, data):
        self.current = bank; self.events.append(['load', bank])
        if data != (self.first if bank == 0 else self.second): raise AssertionError('Wrong actual staged bytes')
        if not write_is_blocked(self.target): raise AssertionError('Load is missing actual Windows lease')
        if self.case == 'second-load-failed' and bank == 1: raise RuntimeError('Native load double rejects')
        return dict(source='EXPLICIT_NATIVE_PORT_DOUBLE', attempt=bank+1,
                    file_sha256=bytes(p.file.sha256).hex(), receipt_key=str(bank+1)*64,
                    slots_restored=True, full_world_verified=False, room_ready=False)

    def abort(self):
        self.events.append(['abort', self.current])
        self.abort_lease_blocked = write_is_blocked(self.target)
        if not self.abort_lease_blocked: raise AssertionError('File lease released before abort')

    def finish(self):
        self.events.append(['finish']); self.finished = True

    def close(self):
        if self.reader: self.reader.close()


class Cases(unittest.TestCase):
    def fixture(self, name):
        folder = OUTPUT/name; folder.mkdir()
        target_folder = folder/'target'; target_folder.mkdir()
        target = target_folder/files.NAME
        first, second = b'owned diagnostic first'*97, b'owned diagnostic second'*113
        target.write_bytes(first)
        source = folder/'received-second.s14'; source.write_bytes(second)
        run = folder/'run'; run.mkdir()
        return folder, target, source, run, first, second, [profile(first, 1, 11, 12), profile(second, 11, 21, 2)]

    def test_two_loads_actual_backup_and_replacement(self):
        folder, target, source, run, first, second, profiles = self.fixture('two-loads')
        port = NativePortDouble('normal', target, first, second)
        notified = []
        result = coordinator.run_two(port, profiles, target, source, run,
                                     on_complete=lambda i, r: notified.append(i))
        self.assertEqual(result['result'], 'PASS_TWO_WARM_DIAGNOSTIC_LOADS')
        self.assertFalse(result['room_ready']); self.assertFalse(result['full_world_verified'])
        self.assertEqual(port.events, [['open', 0], ['load', 0], ['open', 1], ['handover', 1], ['load', 1], ['finish']])
        self.assertEqual(notified, [0, 1]); self.assertEqual(target.read_bytes(), second)
        staging = json.loads((run/'staging-result.json').read_text(encoding='utf-8'))
        self.assertEqual(staging['result'], 'STAGED'); self.assertTrue(staging['backup_byte_verified'])
        self.assertEqual(Path(staging['backup']).read_bytes(), first)
        self.assertEqual(staging['previous_identity'], result['completed'][0]['file_identity'])
        self.assertEqual(len(list((run/'staging').glob('*.verified-old.s14'))), 1)
        self.assertFalse(write_is_blocked(target))
        EVIDENCE.append(dict(case='two-loads', actual_replace=True, actual_backup=True,
                             native_port='DOUBLE', order=port.events, ready=False))

    def rejection(self, case):
        folder, target, source, run, first, second, profiles = self.fixture(case)
        port = NativePortDouble(case, target, first, second)
        try:
            with self.assertRaises(Exception): coordinator.run_two(port, profiles, target, source, run)
            self.assertFalse(port.finished)
            if case in ('handover-refused', 'first-drift'):
                self.assertFalse((run/'staging').exists())
                self.assertNotIn(['load', 1], port.events)
            if case == 'handover-refused': self.assertEqual(target.read_bytes(), first)
            if case == 'first-drift': self.assertEqual(target.read_bytes(), b'external changed first file')
            if case == 'stage-conflict':
                self.assertEqual(target.read_bytes(), first)
                self.assertNotIn(['load', 1], port.events)
                outcome = json.loads((run/'staging-result.json').read_text(encoding='utf-8'))
                self.assertNotEqual(outcome['result'], 'STAGED')
            if case == 'second-load-failed':
                self.assertEqual(target.read_bytes(), second)
                self.assertEqual(port.events[-1], ['abort', 1])
                self.assertIs(port.abort_lease_blocked, True)
                self.assertFalse(write_is_blocked(target))
                self.assertEqual(len(list((run/'staging').glob('*.verified-old.s14'))), 1)
            EVIDENCE.append(dict(case=case, order=port.events, native_port='DOUBLE',
                                 actual_abort_writer_blocked=port.abort_lease_blocked,
                                 finish_called=False, ready=False))
        finally: port.close()

    def test_handover_refused_before_stage(self): self.rejection('handover-refused')
    def test_first_file_drift_before_stage(self): self.rejection('first-drift')
    def test_actual_staging_reader_conflict(self): self.rejection('stage-conflict')
    def test_second_failure_aborts_while_actual_file_lease_held(self): self.rejection('second-load-failed')


def pins():
    names = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None)}
    names.add(Path(__file__).resolve())
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(names)
            if p.is_relative_to(ROOT) and p.suffix == '.py'}


if __name__ == '__main__':
    OUTPUT = PRIVATE/'b_warm_coordinator_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True)
    before = pins(); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    sources = pins(); stable = all(sources.get(k) == v for k, v in before.items())
    value = dict(family='san14.b-warm-coordinator-files.v1', result='PASS' if result.wasSuccessful() and result.testsRun == 5 and stable else 'FAIL',
                 tests=result.testsRun, sources=sources, inputs_unchanged=stable, cases=EVIDENCE,
                 native_port='EXPLICIT_DOUBLE', game_access=False, actual_windows_staging=True,
                 failures=[(str(t), detail) for t, detail in result.failures+result.errors])
    value['artifacts'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT/'result.json'); print(stream.getvalue())
    raise SystemExit(0 if value['result'] == 'PASS' else 1)
