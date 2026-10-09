"""Actual owned rules publisher + Windows staging; warm native load is a double."""
import ctypes as C
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
sys.path[:0] = [str(PRIVATE/'python_deps'), str(ROOT/'outputs/san14-link')]
import human_rules_world_lifecycle_test as native
from human_rules_world_lifecycle import Config, WorldLifecycle, LifecycleError
from b_warm_profile_contract import Profile, Date, Identity
import b_warm_staging as files
from b_warm_rules_bridge import WarmRulesBridge

PRIOR = HERE/'human_rules_world_lifecycle_runs/20261008-100221-226218'
PRIOR_SHA = '2061b5b4dff4b4e73f6d27db8cff30e375c4df3795284d65579ef547717f7b87'
OUTPUT = None
EVIDENCE = []


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_build(folder):
    import pefile
    from human_rules_activation_publish_v2_counter_profile import generate
    if sha(PRIOR/'result.json') != PRIOR_SHA: raise ValueError('Prior owned build identity differs')
    r = json.loads((PRIOR/'result.json').read_text(encoding='utf-8'))
    if r['result'] != 'PASS' or not r['sources_unchanged']: raise ValueError('Prior build not successful')
    sources = {}
    for name, digest in r['source_sha256'].items():
        path = ROOT/name
        if sha(path) != digest: raise ValueError('Prior native source drift '+name)
        sources[str(path)] = digest
    inputs = folder/'inputs'; inputs.mkdir()
    for name, digest in r['binary_sha256'].items():
        source = PRIOR/'inputs'/name
        if sha(source) != digest: raise ValueError('Prior owned artifact changed '+name)
        shutil.copyfile(source, inputs/name)
        if sha(inputs/name) != digest: raise ValueError('Copy differs '+name)
    profile = generate(inputs/'first.dll', folder/'counter-profile.h')
    pe = pefile.PE(str(inputs/'first.dll'))
    try: exports = {s.name.decode(): s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
    finally: pe.close()
    native.BUILD = dict(run=folder, inputs=inputs, sources={}, counters=profile['active_counters'],
                        exports=exports, binaries=r['binary_sha256'])
    return sources


def writer_blocked(path):
    k = files.kernel(); h = k.CreateFileW(str(path), 0x40000000, 7, None, 3, 0, None)
    if h not in (None, C.c_void_p(-1).value): k.CloseHandle(h); return False
    return C.get_last_error() == 32


class WarmPortDouble:
    def __init__(self, owned, request, target, source, fail=False):
        self.owned, self.request, self.target, self.source, self.fail = owned, request, target, source, fail
        self.events = []; self.abort_blocked = None
    def open_bank(self, index): self.events.append(['open', index]); return index
    def authorize_second(self, bank, profile): self.events.append(['handover', bank])
    def load(self, bank, profile, raw):
        self.events.append(['warm_load_double', bank])
        assert self.owned.publisher_calls[-1]['operation'] == 'restore'
        assert raw == self.target.read_bytes() == self.source.read_bytes()
        assert writer_blocked(self.target)
        self.owned.load(self.request)  # actual self-owned world pointer replacement
        if self.fail: raise RuntimeError('Injected warm load result failure after owned world switch')
        return dict(result='EXPLICIT_WARM_LOAD_DOUBLE', full_world_verified=False, ready=False)
    def abort(self):
        self.events.append(['abort']); self.abort_blocked = writer_blocked(self.target)
        assert self.abort_blocked


class Cases(unittest.TestCase):
    def fixture(self, label, fail=False):
        o = native.Owned(label); self.addCleanup(o.fail_cleanup)
        old = o.port(o.first); old.install()
        life = WorldLifecycle(old, guard_check=lambda: o.identity(None), on_hold=lambda reason: None)
        request = o.expected_next(old); config = Config.from_buffer_copy(old.world.config)
        source = o.run/'received.s14'; source.write_bytes(b'owned warm replacement'*73)
        target_dir = o.run/'target'; target_dir.mkdir(); target = target_dir/files.NAME
        target.write_bytes(b'owned previous slot bytes'*67)
        profile = Profile(); profile.file.name = files.NAME.encode(); profile.file.slot = 63
        profile.file.size = source.stat().st_size; profile.file.sha256[:] = bytes.fromhex(sha(source))
        profile.before = Date(config.year, config.month, config.day)
        profile.loaded = Date(request.year, request.month, request.day)
        # Owned rules fixture viewer is 12; source is the other human 2.
        profile.source = Identity(952, 2, 2); profile.target = Identity(666, 12, 11); profile.currentForce = config.viewer
        port = WarmPortDouble(o, request, target, source, fail)
        records = o.run/'records'; records.mkdir()
        bridge = WarmRulesBridge(life, port, target=target, records=records)
        return o, old, life, request, profile, source, target, records, port, bridge

    def test_restore_stage_load_observe_reinstall(self):
        o, old, life, req, profile, source, target, records, port, bridge = self.fixture('bridge-success')
        before = target.read_bytes()
        result = bridge.replace(req, profile, source, observe_loaded=o.observe_loaded, prepare_rules=o.prepare)
        self.assertFalse(result['ready']); self.assertFalse(result['full_world_verified'])
        self.assertEqual([x['operation'] for x in o.publisher_calls], ['install', 'restore', 'install'])
        self.assertEqual(o.transition_order, ['LOAD_COMPLETED_NO_NEW_CONFIG_YET',
            'NEW_WORLD_POINTERS_READ_FROM_NATIVE_MEMORY', 'FRESH_MODULE_PREPARED_AFTER_OBSERVATION'])
        self.assertEqual(target.read_bytes(), source.read_bytes())
        backups = list(records.rglob('*.verified-old.s14'))
        self.assertEqual(len(backups), 1); self.assertEqual(backups[0].read_bytes(), before)
        o.command('e', 'EXERCISED'); life.current.restore(); final = o.finish()
        self.assertEqual(final['worlds_loaded'], 1); self.assertEqual(final['resident_modules'], 2)
        EVIDENCE.append(dict(case='restore-stage-load-observe-install', final=final, native_rules=True,
            actual_staging=True, warm_load='EXPLICIT_DOUBLE_OWNED_WORLD_SWITCH', publisher=o.publisher_calls,
            transition=o.transition_order, ready=False))

    def test_active_old_native_call_prevents_staging(self):
        o, old, life, req, profile, source, target, records, port, bridge = self.fixture('bridge-active')
        before = target.read_bytes(); o.command('a', 'ACTIVE')
        with self.assertRaises(LifecycleError):
            bridge.replace(req, profile, source, observe_loaded=o.observe_loaded, prepare_rules=o.prepare)
        self.assertFalse(o.loaded); self.assertEqual(target.read_bytes(), before)
        self.assertFalse(list(records.rglob('*.verified-old.s14')))
        self.assertFalse(any(x['generation'] == 2 for x in o.publisher_calls))
        o.command('r', 'DRAINED'); old.restore(); final = o.finish()
        EVIDENCE.append(dict(case='native-active-rejects-before-stage', final=final, publisher=o.publisher_calls))

    def test_failed_warm_load_never_installs_new_rules(self):
        o, old, life, req, profile, source, target, records, port, bridge = self.fixture('bridge-load-failed', True)
        with self.assertRaises(RuntimeError):
            bridge.replace(req, profile, source, observe_loaded=o.observe_loaded, prepare_rules=o.prepare)
        self.assertTrue(o.loaded); self.assertIs(port.abort_blocked, True)
        self.assertEqual(life.phase, 'HELD'); self.assertEqual(len(o.ports), 1)
        self.assertEqual([x['operation'] for x in o.publisher_calls], ['install', 'restore'])
        self.assertFalse(writer_blocked(target)); self.assertEqual(target.read_bytes(), source.read_bytes())
        final = o.finish()
        EVIDENCE.append(dict(case='load-failed-no-reinstall', final=final,
            abort_actual_writer_blocked=True, publisher=o.publisher_calls, ready=False))


def python_pins():
    paths = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None)}
    paths.add(Path(__file__).resolve())
    return {str(p): sha(p) for p in paths if p.is_relative_to(ROOT) and p.suffix == '.py'}


if __name__ == '__main__':
    OUTPUT = PRIVATE/'b_warm_rules_bridge_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); OUTPUT.mkdir(parents=True)
    report = dict(family='san14.b-warm-rules-bridge.v1', result='FAIL', game_access=False, actual_game_load=False, ready=False)
    try:
        sources = prepare_build(OUTPUT); sources.update(python_pins()); stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
        (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
        stable = all(sha(n) == h for n, h in sources.items())
        report.update(result='PASS' if result.wasSuccessful() and result.testsRun == 3 and stable else 'FAIL',
            tests=result.testsRun, sources=sources, inputs_unchanged=stable, cases=EVIDENCE,
            failures=[(str(t), detail) for t, detail in result.failures+result.errors])
        print(stream.getvalue())
    except BaseException as exc: report['error'] = repr(exc)
    report['private_inputs'] = {str(PRIOR/'result.json'): PRIOR_SHA}
    report['artifacts'] = {str(p): sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT/'result.json')
    raise SystemExit(0 if report['result'] == 'PASS' else 1)
