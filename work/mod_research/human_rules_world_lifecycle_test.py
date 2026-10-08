"""Compile and exercise six actual publisher sources in owned processes only.

No game discovery, live launcher import, Steam access or target module unload.
Private native archive is read only as input to the explicitly owned MEM_IMAGE.
"""
import argparse
import ctypes as C
from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import queue
import re
import shutil
import struct
import subprocess
import sys
import threading
import unittest

from human_rules_world_lifecycle import (Config, Descriptor, LifecycleError,
    ModuleIdentity, ResidentPort, WorldGeneration, NextWorldRequest, WorldLifecycle)

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
EVIDENCE = []
BUILD = None


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(private, run):
    sys.path.insert(0, str(private/'python_deps'))
    from human_rules_activation_publish_v2_counter_profile import generate
    import pefile
    source = run/'src'
    source.mkdir()
    snapshots = {}
    generated = {'human_rules_activation_publish_v2_fixture_hashes.h',
                 'human_rules_activation_publish_v2_fixture_counters.h'}

    def capture(path):
        path = path.resolve()
        if path in snapshots:
            return
        relative = path.relative_to(ROOT) if path.is_relative_to(ROOT) else Path('private')/path.name
        output = source/relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, output)
        snapshots[path] = (relative, sha(path))
        for name in re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.M):
            if name in generated:
                continue
            candidate = next((x for x in (path.parent/name, P/name, ROOT/'outputs/san14-link'/name,
                                           private/name) if x.is_file()), None)
            if candidate is None:
                raise FileNotFoundError(name)
            capture(candidate)

    names = ['human_rules_world_lifecycle_fixture.cpp', 'human_rules_activation_publish_v2.cpp',
             'human_rules_activation_v2.asm', 'human_rules_hook_transport.cpp',
             'human_ai_runtime_adapter.cpp', 'human_economy_runtime_adapter.cpp',
             'human_ai_runtime_subject.cpp', 'human_ai_group_resolver.cpp',
             'human_rules_activation_publish_v2_fixture_stage.cpp',
             'human_rules_activation_publish_v2_counter_profile.py',
             'human_rules_world_lifecycle.py', 'human_rules_world_lifecycle_test.py']
    for name in names:
        capture(P/name)
    sp = source/'work/mod_research'
    inputs = run/'inputs'
    inputs.mkdir()
    old = private/'human_rules_stage_debug_rollback_runs/20261007-214414-327573/inputs'
    for name in ('owned_rules_image.dll', 'game-runtime-image.bin'):
        shutil.copy2(old/name, inputs/name)
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags = f'/nologo /std:c++17 /EHa /W4 /WX /O2 /MT /I"{source/"outputs/san14-link"}" /I"{source/"private"}"'

    def commands(label, lines):
        script = run/f'build-{label}.cmd'
        script.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+
                          '\n'.join(line+'\nif errorlevel 1 exit /b 1' for line in lines))
        result = subprocess.run(['cmd', '/d', '/c', str(script)], cwd=run, capture_output=True)
        (run/f'build-{label}.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError(result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))

    deps = ['human_rules_hook_transport.cpp', 'human_ai_runtime_adapter.cpp',
            'human_economy_runtime_adapter.cpp', 'human_ai_runtime_subject.cpp', 'human_ai_group_resolver.cpp']
    commands('stage', [f'ml64 /nologo /c /Fo"{run/"income.obj"}" "{sp/"human_rules_activation_v2.asm"}"',
        f'cl {flags} /LD '+ ' '.join('"'+str(sp/n)+'"' for n in ['human_rules_activation_publish_v2_fixture_stage.cpp']+deps)+
        f' "{run/"income.obj"}" /link /EXPORT:HumanRulesActivationIncome /OUT:"{inputs/"first.dll"}"'])
    shutil.copy2(inputs/'first.dll', inputs/'second.dll')
    commands('target', [f'cl {flags} "{sp/"human_rules_world_lifecycle_fixture.cpp"}" /Fe:"{inputs/"target.exe"}"'])
    profile = generate(inputs/'first.dll', sp/'human_rules_activation_publish_v2_fixture_counters.h')
    (sp/'human_rules_activation_publish_v2_fixture_hashes.h').write_text(
        '#pragma once\nconstexpr unsigned ExpectedFixture=1;\n'+
        'constexpr const char* ApprovedExeSha="'+sha(inputs/'target.exe')+'";\n'+
        'constexpr const char* ApprovedStageSha="'+sha(inputs/'first.dll')+'";\n'+
        'constexpr const char* ApprovedImageSha="'+sha(inputs/'owned_rules_image.dll')+'";\n')
    commands('publisher', [f'cl {flags} /DHUMAN_RULES_ACTIVATION_PUBLISH_FIXTURE '+
        ' '.join('"'+str(sp/n)+'"' for n in ['human_rules_activation_publish_v2.cpp',
                    'human_ai_runtime_subject.cpp', 'human_ai_group_resolver.cpp'])+
        f' /Fe:"{inputs/"publisher.exe"}"'])
    pe = pefile.PE(str(inputs/'first.dll'))
    exports = {s.name.decode(): s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
    pe.close()
    binaries = {p.name: sha(p) for p in inputs.iterdir() if p.is_file()}
    return dict(run=run, inputs=inputs, sources=snapshots, counters=profile['active_counters'],
                exports=exports, binaries=binaries)


k32 = C.WinDLL('kernel32', use_last_error=True)
for name, args, result in [
    ('ReadProcessMemory', [C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)], C.c_int),
    ('GetProcessId', [C.c_void_p], C.c_uint32),
    ('GetProcessTimes', [C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p], C.c_int),
    ('CheckRemoteDebuggerPresent', [C.c_void_p,C.POINTER(C.c_int)], C.c_int),
]:
    f = getattr(k32, name); f.argtypes = args; f.restype = result


class Owned:
    def __init__(self, label):
        self.run = BUILD['run']/label
        self.run.mkdir()
        self.i = BUILD['inputs']
        self.child = subprocess.Popen([str(self.i/'target.exe'), str(self.i/'first.dll'),
            str(self.i/'second.dll'), str(self.i/'owned_rules_image.dll'),
            str(self.i/'game-runtime-image.bin')], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        self.lines = queue.Queue()
        self.output = []
        self.publisher_calls = []
        self.ports = []
        self.held_publishers = []
        self.closed = False
        self.loaded = False
        self.transition_order = []

        def consume():
            for line in self.child.stdout:
                self.output.append(line)
                self.lines.put(line)
        self.reader = threading.Thread(target=consume, daemon=True)
        self.reader.start()
        self.first = self.receive('PREPARED')
        self.birth = self.first['birth']
        self.identity(None)

    def receive(self, event):
        line = self.lines.get(timeout=15)
        value = json.loads(line)
        assert value['event'] == event, value
        return value

    def command(self, command, event):
        self.child.stdin.write(command.encode('ascii'))
        self.child.stdin.flush()
        return self.receive(event)

    def identity(self, module):
        assert self.child.poll() is None, 'Owned process exited'
        handle = int(self.child._handle)
        assert k32.GetProcessId(handle) == self.child.pid
        times = [C.c_uint64() for _ in range(4)]
        assert k32.GetProcessTimes(handle, *(C.byref(v) for v in times))
        assert times[0].value == self.birth
        assert sha(self.i/'target.exe') == BUILD['binaries']['target.exe']
        if module:
            assert module.pid == self.child.pid and module.birth == self.birth
            assert module.stage_sha256 == BUILD['binaries']['first.dll']
        debugged = C.c_int()
        assert k32.CheckRemoteDebuggerPresent(handle, C.byref(debugged)) and not debugged.value

    def read(self, address, length):
        buf = C.create_string_buffer(length)
        count = C.c_size_t()
        assert k32.ReadProcessMemory(int(self.child._handle), address, buf, length, C.byref(count))
        assert count.value == length
        return buf.raw

    def current_config(self, world):
        # A real RPM reader over own native data. Room/complete world are MODEL.
        c = Config.from_buffer_copy(world.config)
        get = lambda a, f: struct.unpack(f, self.read(a, struct.calcsize(f)))[0]
        c.root = get(c.image+0x1FCA1E0, '<Q')
        c.world = get(c.root+0x85130, '<Q')
        c.year, c.month, c.day = get(c.world+0x34,'<H'), get(c.world+0x36,'<B'), get(c.world+0x37,'<B')
        c.viewer = get(c.world+0x3A,'<B')
        c.income_key5 = get(c.image+0x18EB628,'<I')
        c.world_option8 = (get(c.world+0x16A8,'<I') >> 8) & 1
        assert get(c.image+0x1FD0C5C,'<i') not in (0,-1)
        assert get(c.image+0x1FCA1E0,'<Q') == c.root and get(c.root+0x85130,'<Q') == c.world
        return bytes(c)

    def port(self, ready):
        generation = ready['generation']
        world = WorldGeneration(generation, str(generation)*64, bytes.fromhex(ready['binding_hex']))
        m = ModuleIdentity(self.child.pid, self.birth, ready['module'], ready['descriptor'],
            bytes.fromhex(ready['nonce']), BUILD['binaries']['first.dll'],
            BUILD['exports']['HumanRulesActivationState'], BUILD['exports']['HumanRulesActivationBinding'],
            tuple((r['instruction_rva'], bytes.fromhex(r['bytes']), r['value_rva']) for r in BUILD['counters']),
            'OWNED_FIXTURE')
        binding_file = self.run/f'world-{generation}.binding.bin'
        binding_file.write_bytes(world.config)

        def publish(operation):
            self.identity(m)
            assert sha(self.i/'publisher.exe') == BUILD['binaries']['publisher.exe']
            stage_file = self.i/('first.dll' if generation == 1 else 'second.dll')
            assert sha(stage_file) == m.stage_sha256
            assert binding_file.read_bytes() == world.config
            args = [str(self.i/'publisher.exe'), operation, str(m.pid), str(m.birth),
                    str(Config.from_buffer_copy(world.config).image), str(m.descriptor),
                    str(stage_file), m.nonce.hex(), str(binding_file)]
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                out, err = proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                # May own an unresolved debug event. Do not kill it or the target.
                self.held_publishers.append(proc)
                raise LifecycleError('Publisher retained for inspection; no target cleanup permitted')
            key = f'{len(self.publisher_calls)}-{generation}-{operation}'
            (self.run/f'{key}.stdout.txt').write_bytes(out)
            (self.run/f'{key}.stderr.txt').write_bytes(err)
            report = json.loads(out.decode().splitlines()[-1])
            self.publisher_calls.append(dict(generation=generation, operation=operation,
                                            code=proc.returncode, report=report))
            return proc.returncode, report

        port = ResidentPort(world, m, read=self.read, identity_check=self.identity,
            publisher=publish, export_current=self.current_config,
            check_scope=lambda w: self.check_scope(w))
        self.ports.append(port)
        return port

    @staticmethod
    def check_scope(world):
        # Explicit own fixture room values, not a production Room attestation.
        c = Config.from_buffer_copy(world.config)
        assert bytes(c.room) == b'\1'+bytes(15) and bytes(c.rules_digest) == b'\7'+bytes(31)
        assert bytes(c.epoch) == bytes([76+world.generation])+bytes(15)

    def expected_next(self, old):
        c = Config.from_buffer_copy(old.world.config)
        return NextWorldRequest(2, '2'*64, bytes([78])+bytes(15), c.year, c.month, 21)

    def load(self, request):
        assert type(request) is NextWorldRequest and not hasattr(request, 'config')
        assert not self.loaded
        self.command('n', 'LOADED')
        self.loaded = True
        self.transition_order.append('LOAD_COMPLETED_NO_NEW_CONFIG_YET')

    def observe_loaded(self, request):
        assert self.loaded, 'Cannot read an unknown new world before load'
        c = Config.from_buffer_copy(bytes.fromhex(self.first['binding_hex']))
        c.epoch[:] = request.epoch
        # Template contains only the known old pointers. current_config reads the
        # actual new root/world from native memory; no predicted target address.
        raw = self.current_config(WorldGeneration(request.generation, request.checkpoint, bytes(c)))
        observed = WorldGeneration(request.generation, request.checkpoint, raw)
        self.transition_order.append('NEW_WORLD_POINTERS_READ_FROM_NATIVE_MEMORY')
        return observed

    def prepare(self, observed):
        assert self.loaded and self.transition_order[-1] == 'NEW_WORLD_POINTERS_READ_FROM_NATIVE_MEMORY'
        new = self.port(self.command('p', 'PREPARED'))
        assert new.world == observed
        self.transition_order.append('FRESH_MODULE_PREPARED_AFTER_OBSERVATION')
        return new

    def finish(self):
        assert not self.held_publishers, 'Publisher retained; inspect without killing'
        final = self.command('q', 'FINAL')
        assert self.child.wait(timeout=10) == 0 and final['result'] == 'PASS'
        self.closed = True
        self.reader.join(timeout=2)
        (self.run/'target.stdout.txt').write_bytes(b''.join(self.output))
        (self.run/'target.stderr.txt').write_bytes(self.child.stderr.read())
        self.child.stdin.close(); self.child.stdout.close(); self.child.stderr.close()
        return final

    def fail_cleanup(self):
        if not self.closed and not self.held_publishers:
            # Only the explicitly created owned target; EOF exits its fixture loop.
            self.child.stdin.close()
            try:
                self.child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                return  # preserve process; no forced kill
            self.reader.join(timeout=2)
            (self.run/'target.stdout.txt').write_bytes(b''.join(self.output))
            (self.run/'target.stderr.txt').write_bytes(self.child.stderr.read())
            self.child.stdout.close(); self.child.stderr.close()


class NativeTests(unittest.TestCase):
    def fixture(self, label):
        owned = Owned(label)
        self.addCleanup(owned.fail_cleanup)
        old = owned.port(owned.first)
        old.install()
        holds = []
        # Blocking stdin loop is this fixture's execution fence. It excludes
        # business execution except our explicit e/a/n test commands.
        guard = lambda: owned.identity(None)
        life = WorldLifecycle(old, guard_check=guard, on_hold=holds.append)
        return owned, old, life, holds

    def test_actual_two_modules_restore_load_rebind_and_both_humans(self):
        o, old, life, holds = self.fixture('two-worlds')
        first = o.command('e', 'EXERCISED')
        o.command('d', 'DATE_ADVANCED')  # normal restore must allow date advancement
        request = o.expected_next(old)
        self.assertFalse(hasattr(request, 'config'))
        self.assertFalse(o.loaded)
        self.assertEqual(o.transition_order, [])
        result = life.replace(request, load=o.load, observe_loaded=o.observe_loaded, prepare=o.prepare)
        self.assertEqual(result['phase'], 'RULES_REBOUND')
        self.assertFalse(result['ready'])
        self.assertEqual(holds, [])
        second = o.command('e', 'EXERCISED')
        life.current.restore()
        final = o.finish()
        self.assertEqual(final['worlds_loaded'], 1)
        self.assertEqual(final['resident_modules'], 2)
        EVIDENCE.append(dict(case='TWO_REAL_NATIVE_RULE_GENERATIONS', history=life.history,
            publisher_calls=o.publisher_calls, generations=[first, second], final=final,
            world_load='OWNED_MEMORY_REPLACEMENT', room_scope='MODEL', full_world_verified=False,
            transition_order=o.transition_order, new_addresses_supplied_before_load=False))

    def test_active_native_call_prevents_restore_and_load(self):
        o, old, life, holds = self.fixture('active-denial')
        o.command('a', 'ACTIVE')
        loaded = []
        with self.assertRaisesRegex(LifecycleError, 'still active'):
            life.replace(o.expected_next(old), load=loaded.append, observe_loaded=o.observe_loaded, prepare=lambda _: old)
        self.assertEqual(loaded, [])
        self.assertEqual(life.phase, 'HELD')
        self.assertEqual(len(holds), 1)
        o.command('r', 'DRAINED')
        old.restore()
        final = o.finish()
        self.assertEqual(final['worlds_loaded'], 0)
        EVIDENCE.append(dict(case='REAL_ACTIVE_CALL_BLOCKS_LOAD', final=final, status=life.status()))

    def test_false_restore_report_does_not_replace_six_source_readback(self):
        o, old, life, holds = self.fixture('false-restore')
        real = old._publisher
        report = dict(o.publisher_calls[-1]['report'], status='RESTORED')
        old._publisher = lambda _: (0, report)
        loaded = []
        with self.assertRaisesRegex(LifecycleError, 'source bytes'):
            life.replace(o.expected_next(old), load=loaded.append, observe_loaded=o.observe_loaded, prepare=lambda _: old)
        self.assertEqual(loaded, [])
        self.assertEqual(len(holds), 1)
        old._publisher = real
        old.restore()
        final = o.finish()
        EVIDENCE.append(dict(case='FABRICATED_SUCCESS_CANNOT_AUTHORIZE_LOAD', final=final))

    def test_new_world_reader_mismatch_blocks_install(self):
        o, old, life, holds = self.fixture('stale-world-reader')
        def prepare(observed):
            new = o.prepare(observed)
            new._export = lambda w: old.world.config
            return new
        with self.assertRaisesRegex(LifecycleError, 'reader disagrees'):
            life.replace(o.expected_next(old), load=o.load, observe_loaded=o.observe_loaded, prepare=prepare)
        self.assertEqual(len(holds), 1)
        self.assertFalse(any(c['generation'] == 2 for c in o.publisher_calls))
        final = o.finish()  # new sources remain original, no install attempted
        EVIDENCE.append(dict(case='STALE_NEW_WORLD_READER_BLOCKS_PUBLICATION', final=final))

    def test_old_loaded_observation_cannot_prepare_a_new_module(self):
        o, old, life, holds = self.fixture('old-loaded-observation')
        request = o.expected_next(old)
        with self.assertRaisesRegex(LifecycleError, 'epoch/date'):
            life.replace(request, load=o.load,
                observe_loaded=lambda q: WorldGeneration(q.generation, q.checkpoint, old.world.config),
                prepare=lambda _: self.fail('Stale observation reached native Prepare'))
        self.assertTrue(o.loaded)
        self.assertEqual(len(holds), 1)
        self.assertEqual(len(o.ports), 1)
        final = o.finish()
        self.assertEqual(final['resident_modules'], 1)
        EVIDENCE.append(dict(case='OLD_POST_LOAD_OBSERVATION_BLOCKS_PREPARE', final=final,
                             transition_order=o.transition_order))

    def test_same_resident_module_is_not_reset_for_next_world(self):
        o, old, life, holds = self.fixture('same-instance')
        def prepare(expected):
            new = o.prepare(expected)
            new.module = old.module  # local contract adversarial fixture, not network input
            return new
        with self.assertRaisesRegex(LifecycleError, 'Fresh resident'):
            life.replace(o.expected_next(old), load=o.load, observe_loaded=o.observe_loaded, prepare=prepare)
        self.assertEqual(len(holds), 1)
        self.assertFalse(any(c['generation'] == 2 for c in o.publisher_calls))
        EVIDENCE.append(dict(case='REUSE_RESIDENT_INSTANCE_REJECTED', final=o.finish()))

    def test_fault_after_real_new_install_stays_held_with_fence_unreleased(self):
        o, old, life, holds = self.fixture('post-install-fault')
        newer = []
        def prepare(observed):
            new = o.prepare(observed)
            newer.append(new)
            real = new._publisher
            def fail_after(operation):
                result = real(operation)
                if operation == 'install':
                    raise LifecycleError('post-install transport uncertainty')
                return result
            new._publisher = fail_after
            return new
        with self.assertRaisesRegex(LifecycleError, 'post-install'):
            life.replace(o.expected_next(old), load=o.load, observe_loaded=o.observe_loaded, prepare=prepare)
        self.assertEqual(life.phase, 'HELD')
        self.assertEqual(len(holds), 1)
        self.assertFalse(life.status()['fence_released'])
        newer[-1].observe(True)
        newer[-1].restore()  # explicit test closeout under own fixture fence
        EVIDENCE.append(dict(case='POST_INSTALL_UNCERTAINTY_RETAINS_HOLD', final=o.finish(), status=life.status()))

    def test_stale_generation_is_terminal_without_any_restore_or_load(self):
        o, old, life, holds = self.fixture('stale-generation')
        loaded = []
        c = Config.from_buffer_copy(old.world.config)
        stale = NextWorldRequest(old.world.generation, old.world.checkpoint, bytes(c.epoch), c.year, c.month, c.day)
        with self.assertRaisesRegex(LifecycleError, 'Stale/repeated'):
            life.replace(stale, load=loaded.append, observe_loaded=o.observe_loaded, prepare=lambda _: old)
        self.assertEqual(loaded, [])
        self.assertEqual(len(o.publisher_calls), 1)
        with self.assertRaisesRegex(LifecycleError, 'held'):
            life.replace(o.expected_next(old), load=loaded.append, observe_loaded=o.observe_loaded, prepare=lambda _: old)
        old.restore()
        EVIDENCE.append(dict(case='STALE_GENERATION_REJECTED_NO_RETRY', final=o.finish()))

    def test_lost_fence_after_restore_blocks_load_and_reports_hold_failure(self):
        o, old, life, holds = self.fixture('fence-lost')
        checks = []
        def guard():
            checks.append(1)
            if len(checks) == 2:
                raise LifecycleError('fence lost')
        def bad_hold(reason):
            holds.append(reason)
            raise LifecycleError('retain port unavailable')
        life._guard, life._on_hold = guard, bad_hold
        loaded = []
        with self.assertRaisesRegex(LifecycleError, 'fence lost'):
            life.replace(o.expected_next(old), load=loaded.append, observe_loaded=o.observe_loaded, prepare=lambda _: old)
        self.assertEqual(loaded, [])
        self.assertIn('retain port unavailable', life.status()['hold_error'])
        old.observe(False)
        EVIDENCE.append(dict(case='FENCE_LOSS_BLOCKS_LOAD_HOLD_FAILURE_EXPOSED', final=o.finish(), status=life.status()))

    def test_modeled_third_generation_cannot_reuse_first_resident_address(self):
        o, first, life, holds = self.fixture('history-reuse')
        life.replace(o.expected_next(first),
            load=o.load, observe_loaded=o.observe_loaded, prepare=o.prepare)
        second = life.current
        config = Config.from_buffer_copy(second.world.config)
        config.epoch[0] = 79
        third_world = WorldGeneration(3, '3'*64, bytes(config))
        third_request = NextWorldRequest(3, '3'*64, bytes(config.epoch), config.year, config.month, config.day)
        # Deliberate MODEL third generation: no third world or DLL is loaded.
        # Fresh nonce with the first resident address must fail before install.
        fake_module = replace(first.module, nonce=bytes([123])*32)
        candidate = ResidentPort(third_world, fake_module, read=o.read, identity_check=o.identity,
            publisher=lambda _: self.fail('Historical module was republished'),
            export_current=o.current_config, check_scope=o.check_scope)
        with self.assertRaisesRegex(LifecycleError, 'Fresh resident'):
            life.replace(third_request, load=lambda _: None, observe_loaded=lambda _: third_world, prepare=lambda _: candidate)
        self.assertEqual(life.phase, 'HELD')
        self.assertEqual(len(life.retained), 3)
        self.assertEqual(len(holds), 1)
        EVIDENCE.append(dict(case='MODEL_THIRD_GENERATION_REJECTS_FIRST_MODULE_REUSE',
            third_generation='MODEL_ONLY_NO_NATIVE_LOAD', final=o.finish(), status=life.status()))

    def test_boolean_check_callbacks_cannot_silently_admit_transition(self):
        o, old, _, _ = self.fixture('bool-contract')
        original_identity, original_scope = old._identity, old._scope
        for which in ('identity', 'scope', 'guard'):
            with self.subTest(port=which):
                holds, loads = [], []
                life = WorldLifecycle(old, guard_check=lambda: o.identity(None), on_hold=holds.append)
                if which == 'identity': old._identity = lambda _: False
                if which == 'scope': old._scope = lambda _: True
                if which == 'guard': life._guard = lambda: False
                with self.assertRaisesRegex(LifecycleError, 'return None'):
                    life.replace(o.expected_next(old), load=loads.append, observe_loaded=o.observe_loaded, prepare=lambda _: old)
                self.assertEqual(loads, [])
                self.assertEqual(len(holds), 1)
                self.assertEqual(life.phase, 'HELD')
                old._identity, old._scope = original_identity, original_scope
        self.assertEqual(len(o.publisher_calls), 1)
        old.restore()
        EVIDENCE.append(dict(case='BOOL_IDENTITY_SCOPE_GUARD_REJECTED', final=o.finish()))

    def test_false_load_result_blocks_prepare_and_records_false_hold_callback(self):
        o, old, life, _ = self.fixture('false-load-result')
        life._on_hold = lambda _: False
        with self.assertRaisesRegex(LifecycleError, 'return None'):
            life.replace(o.expected_next(old), load=lambda _: False, observe_loaded=o.observe_loaded,
                         prepare=lambda _: self.fail('Prepare after failed load'))
        self.assertEqual(life.phase, 'HELD')
        self.assertIn('return None', life.hold_error)
        self.assertEqual(len(o.publisher_calls), 2)  # install then restore only
        EVIDENCE.append(dict(case='FALSE_LOAD_AND_FALSE_HOLD_NOT_SUCCESS', final=o.finish(), status=life.status()))


def main():
    global BUILD
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture-root', required=True)
    args = parser.parse_args()
    private = Path(args.fixture_root).resolve()
    if any(c in str(private)+str(P) for c in ('"','\n','\r','%','&','|','<','>')):
        raise SystemExit('Unsupported build path')
    run = P/'human_rules_world_lifecycle_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    result = dict(schema='san14.human-rules-world-lifecycle.v1', result='FAIL', game_access=False,
                  actual_game_load=False, full_world_verified=False, production_fence_verified=False,
                  ready=False, fixture_room_scope=True)
    try:
        BUILD = build(private, run)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeTests)
        result['test_methods'] = [t.id() for t in suite]
        tests = unittest.TextTestRunner(verbosity=2).run(suite)
        unchanged = all(sha(path) == evidence[1] for path, evidence in BUILD['sources'].items())
        result.update(result='PASS' if tests.wasSuccessful() and unchanged else 'FAIL',
            tests_run=tests.testsRun, errors=len(tests.errors), failures=len(tests.failures),
            skipped=len(tests.skipped), sources_unchanged=unchanged, cases=EVIDENCE,
            source_sha256={str(v[0]):v[1] for v in BUILD['sources'].values()},
            binary_sha256=BUILD['binaries'])
    except BaseException as exc:
        result['error'] = type(exc).__name__+': '+str(exc)
        print(result['error'], file=sys.stderr)
    (run/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'result':result['result'], 'path':str(run/'result.json')}))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
