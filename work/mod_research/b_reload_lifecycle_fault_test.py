"""Compose cold-pool lifecycle with the complete two-generation queue.

Only owned child fixtures and explicit private archives. No process discovery,
installed-game access, loader invocation or real game-file business execution.
Frozen production sources are linked unchanged; only fixture services compose.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import uuid

P = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, P / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


previous = module('lifecycle_queue_previous', 'b_reload_lifecycle_test.py')
once = previous.once
CASES = ('success', 'lf-first-observer', 'lf-second-observer')


def fixture_sources():
    queue = module('fault_queue_base', 'b_reload_lifecycle_queue_test.py')
    cpp, asm, machine, ports = queue.fixture_sources()
    cpp = once(cpp, 'static AdmissionBundle* admissionBundle=nullptr;', 'static AdmissionBundle* admissionBundle=nullptr;\n#include "b_reload_lifecycle_fault_admission.inc"')
    cpp = once(cpp, 'ac.prefetch_provider=hw::MakeProvider(b->hardware);', 'ac.prefetch_provider=lifecycleFaultProvider(b->hardware);')
    cpp = once(cpp, 'check(provider.Register(pcfg)&&provider.OpenWindow(generationIndex+2),"retained native-source bank and observation window");', 'lifecycleFaultConfig=pcfg;check(generationIndex?lifecycleAdvance->RegisterAndOpen(pcfg):(provider.Register(pcfg)&&provider.OpenWindow(generationIndex+2)),"actual prior completion gate before second generation registration");')
    cpp = once(cpp, '    routedUser(layout.config.states[4],1,2,3);ns::Report r{};', '    if(lifecycleFaultTarget()){routedUser(layout.config.states[4],1,2,3);ns::Report rejected{};session.Snapshot(rejected);lifecycleFaultVerify();return finishReport(rejected,true); }\n    routedUser(layout.config.states[4],1,2,3);ns::Report r{};')
    cpp = once(cpp, '        wchar_t* args[]=', '        if(first.rfind(L"lf-",0)==0)caseName=L"success";\n        wchar_t* args[]=')
    cpp = once(cpp, '    }\n\n    lifecycleQueueFinish();', '        lifecycleFaultAfterGeneration();\n    }\n\n    lifecycleQueueFinish();')
    cpp = once(cpp, 'int wmain(int argc,wchar_t**argv)', '#include "b_reload_lifecycle_fault_fixture.inc"\nint wmain(int argc,wchar_t**argv)')
    return cpp, asm, machine, ports


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    value = os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    if not value or any(c in value for c in ('"', '\n', '%', '&', '|', '<', '>')):
        raise SystemExit('Set SAN14_PRIVATE_FIXTURE_ROOT; no tests ran.')
    private = Path(value).resolve()
    archive = private / 'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
    image_file = private / 'game-runtime-image.bin'
    expected = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    if not archive.is_file() or not image_file.is_file() or sha(archive) != expected or sha(image_file) != '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268':
        raise SystemExit('Missing/changed private archive inputs; no tests ran.')
    frozen = module('lifecycle_queue_build', 'checkpoint_task_completion_test.py')
    units = [u for u in frozen.UNITS if u not in ('checkpoint_task_completion_fixture', 'checkpoint_task_completion_ports', 'checkpoint_native_task_provider', 'checkpoint_task_native_start', 'checkpoint_persistent_input_hwbp')]
    units += list(previous.REUSED_UNITS) + list(previous.NEW_UNITS) + ['b_reload_lifecycle_fault_guard']
    asm_units = ('checkpoint_persistent_bridge', 'checkpoint_guest_native_session_fixture', 'checkpoint_persistent_authorized_bridge', 'checkpoint_native_input_hwbp_fixture', 'checkpoint_load_worker_bridge', 'b_reload_title_bridge', 'b_reload_title520_bridge', 'b_reload_parent_bridge', 'b_reload_root_activation_bridge', 'b_reload_lifecycle_bridge')
    profiles = {
        'b_reload_lifecycle_profile': {'InitBytes': (0x509580, 0x509639), 'InitCall': (0x1447B6, 0x1447BB)},
        'b_reload_yield_profile': {'ResetBytes': (0x509EF0, 0x509F4F), 'SetBytes': (0x834820, 0x83483C), 'EventResetBytes': (0x834640, 0x83465C)},
        'b_reload_root_worker_profile': {'RunnerBytes': (0x834D10, 0x834E75), 'ThunkBytes': (0x50B730, 0x50B79A), 'YieldBytes': (0x50B690, 0x50B6FF)},
        'b_reload_parent_profile': {'SchedulerBytes': (0x509FE0, 0x50B690), 'OuterCall': (0x13DC09, 0x13DC0E), 'PhaseCall': (0x50B41B, 0x50B420), 'WaitBytes': (0x834EF0, 0x834EFE)},
        'b_reload_title590_profile': {'StartBytes': (0x4BEEE0, 0x4BEF50)},
        'b_reload_title520_profile': {'FinalizeBytes': (0x497110, 0x49713F), 'ThunkBytes': (0x4FAC30, 0x4FAC3C), 'CallbackBytes': (0x4CC690, 0x4CC7C5), 'StartBytes': (0x4BEE50, 0x4BEED7)},
    }
    sources = set()
    todo = [u + '.cpp' for u in units] + [u + '.asm' for u in asm_units]
    todo += ['b_reload_lifecycle_fault_test.py','b_reload_lifecycle_fault_admission.inc','b_reload_lifecycle_fault_fixture.inc','b_reload_lifecycle_queue_test.py', 'b_reload_lifecycle_queue_fixture.inc', 'b_reload_lifecycle_test.py', 'b_reload_lifecycle_fixture.inc', 'b_reload_activated_queue_test.py', 'b_reload_activated_queue_fixture.inc', 'b_reload_yield_test.py', 'b_reload_yield_fixture.inc', 'b_reload_nested_test.py', 'b_reload_nested_fixture.inc', 'b_reload_root_worker_test.py', 'b_reload_root_worker_fixture.inc', 'b_reload_bound_test.py', 'b_reload_bound_fixture.inc', 'b_reload_queue_test.py', 'b_reload_queue_fixture.inc', 'b_reload_queue_parent_fixture.inc', 'b_reload_parent_test.py', 'b_reload_title520_test.py', 'b_reload_title590_test.py', 'b_reload_title_source_test.py', 'checkpoint_task_completion_test.py', 'checkpoint_task_completion_fixture.cpp', 'checkpoint_task_completion_fixture.asm']
    private_inputs = {str(archive.relative_to(private)): sha(archive), 'game-runtime-image.bin': sha(image_file)}
    while todo:
        name = todo.pop()
        if name in sources or name in {n + '.h' for n in profiles}:
            continue
        path = P / name
        if not path.is_file():
            path = private / name
            if not path.is_file():
                raise SystemExit('Missing input ' + name)
            private_inputs[name] = sha(path)
            continue
        sources.add(name)
        if path.suffix in ('.cpp', '.h', '.inc'):
            todo.extend(re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.M))
    before = {n: sha(P / n) for n in sorted(sources)}
    run = P / 'b_reload_lifecycle_fault_runs' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + uuid.uuid4().hex[:6])
    run.mkdir(parents=True)
    image = image_file.read_bytes()
    for namespace, spans in profiles.items():
        body = '#pragma once\nnamespace ' + namespace + ' {\n'
        for name, (start, end) in spans.items():
            body += 'inline constexpr unsigned char ' + name + '[]={' + ','.join(hex(v) for v in image[start:end]) + '};\n'
        (run / (namespace + '.h')).write_text(body + '}\n')
    cpp, asm, machine, ports = fixture_sources()
    for name, content in (('fixture.cpp', cpp), ('fixture.asm', asm), ('b_reload_title520_machine.inc', machine), ('b_reload_title520_fixture_ports.inc', ports)):
        (run / name).write_text(content, encoding='utf-8')
    flags = frozen.FLAGS + f' /I"{run}" /I"{P}" /I"{private}"'
    defs = frozen.DEFS + ' /DB_RELOAD_TITLE_SOURCE_FIXTURE /DB_RELOAD_PARENT_FIXTURE /DB_RELOAD_ROOT_WORKER_FIXTURE /DB_RELOAD_ROOT_ACTIVATION_FIXTURE /DB_RELOAD_LIFECYCLE_FIXTURE'
    commands = [f'cl {flags} /c /Fo"production_{u}.obj" "{P / (u + ".cpp")}"' for u in (*previous.NEW_UNITS, 'b_reload_lifecycle_fault_guard')]
    objects = []
    for name in units:
        obj = name + '.obj'
        objects.append(obj)
        remap = frozen.REMAP if name == 'checkpoint_dynamic_cc_load_observer' else ''
        commands.append(f'cl {flags} {defs} {remap} /c /Fo"{obj}" "{P / (name + ".cpp")}"')
    commands.append(f'cl {flags} {defs} /c /Fofixture.obj fixture.cpp')
    objects.append('fixture.obj')
    for name in asm_units:
        obj = name + '_asm.obj'
        objects.append(obj)
        commands.append(f'ml64 /nologo /c /Fo"{obj}" "{P / (name + ".asm")}"')
    commands += ['ml64 /nologo /c /Fo fixture_asm.obj fixture.asm', 'link /nologo /incremental:no /OUT:fixture.exe ' + ' '.join(objects) + ' fixture_asm.obj']
    build = run / 'build.cmd'
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    build.write_text('@echo off\nsetlocal\ncall "' + vc + '" >nul\nif errorlevel 1 exit /b 1\n' + '\n'.join(c + '\nif errorlevel 1 exit /b 1' for c in commands) + '\n')
    proc = subprocess.run(['cmd', '/c', str(build)], cwd=run, capture_output=True, text=True, encoding='mbcs', errors='replace')
    (run / 'build.log').write_text(proc.stdout + proc.stderr, encoding='utf-8')
    if proc.returncode:
        raise SystemExit('Build failed; see ' + str(run / 'build.log'))
    rows = []
    for case in CASES:
        folder = run / case
        first = folder / '0/svdexccSC03.s14'
        first.parent.mkdir(parents=True)
        shutil.copyfile(archive, first)
        second = folder / '1/svdexccSC03.s14'
        second.parent.mkdir()
        payload = bytearray(archive.read_bytes())
        payload[77] ^= 0x5a
        payload.extend(bytes(range(128)))
        second.write_bytes(payload)
        second_sha = sha(second)
        proc = subprocess.run([str(run / 'fixture.exe'), case, str(first), str(folder)], cwd=run, capture_output=True, text=True, errors='replace', timeout=60)
        (folder / 'stdout.txt').write_text(proc.stdout, encoding='utf-8')
        (folder / 'stderr.txt').write_text(proc.stderr, encoding='utf-8')
        records = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith('{')]
        composition = [r for r in records if r.get('startup_and_full_queue_composed') or r.get('startup_and_fault_composed')]
        passed = bool(records and records[-1].get('passed') and len(composition) == 1 and proc.returncode == 0 and sha(first) == expected and sha(second) == second_sha)
        rows.append(dict(case=case, passed=passed, exit=proc.returncode, records=records))
        print(case, 'PASS' if passed else 'FAIL', flush=True)
    unchanged = all(sha(P / n) == h for n, h in before.items()) and all(sha(private / n) == h for n, h in private_inputs.items())
    result = dict(schema='san14.b-reload-lifecycle-fault-owned.v1', result='PASS' if unchanged and all(r['passed'] for r in rows) else 'FAIL', cases=rows, sources=before, private_inputs=private_inputs, inputs_unchanged=unchanged,
                  fixture_sha256=sha(run / 'fixture.exe'), production_objects={u: sha(run / f'production_{u}.obj') for u in (*previous.NEW_UNITS, 'b_reload_lifecycle_fault_guard')},
                  actual_pool_initializer=True, full_queue_activation_composed=True, nested_root_load_ports_composed=True,
                  actual_root_yield_executed=False, actual_parent_resume_executed=False, actual_input_lease_yield_executed=False,
                  actual_queue_finalize=True, worker_expected_generation_atomic=True, trusted_host_advance_gate=True, global_scheduler_fence=False, fault_generations_finish_full_queue=False, unowned_warmup_each_generation=True,
                  initial_wait_only=True, constructor_wait_is_double=True, constructor_and_engine_business_are_doubles=True,
                  second_file_is_diagnostic_variant=True, game_access=False, production_installer=False,
                  real_game_reload=False, full_world=False, room_ready=False, native_simulation_permit=False)
    path = run / 'result.json'
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': result['result'], 'cases': len(rows), 'path': str(path)}))
    raise SystemExit(0 if result['result'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
