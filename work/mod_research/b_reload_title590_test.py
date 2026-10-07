"""Actual Title +590 start, worker publication and automatic role ports.

Only self-owned fixture processes. The archived native initializer/runner and
Windows CONTEXT sources execute on CPU; engine/Steam business remain doubles.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess

P = Path(__file__).resolve().parent
CASES = ('success', 'reuse-full-addresses', 'late-old-root', 'completion-wait',
         'title590-exception', 'title590-wrong-wait',
         'source-stop-before-publish', 'source-slot-drift', 'source-code-drift',
         'source-writable-slot', 'source-adapter-stop', 'source-after-publish-conflict')
NEW_UNITS = ('b_reload_title_bridge', 'b_reload_title590_router',
             'b_reload_title590_publish', 'b_reload_title590_ports', 'b_reload_title_source_v2')


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, P / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('Frozen fixture anchor changed: ' + old[:100])
    return text.replace(old, new)


def fixture_sources():
    previous = load_module('title_source_predecessor', 'b_reload_title_source_test.py')
    cpp, asm = previous.fixture_source()
    cpp = cpp.replace('b_reload_title_source.h', 'b_reload_title_source_v2.h')
    cpp = cpp.replace('b_reload_title_source::', 'b_reload_title_source_v2::')
    cpp = cpp.replace('checkpoint_task_completion_ports.h', 'b_reload_title590_ports.h')
    cpp = cpp.replace('namespace completion=checkpoint_task_completion;',
        'namespace completion=b_reload_title590_ports;\nstatic b_reload_title590_router::Router title590Router;\nstatic b_reload_title590_publish::Publisher* title590Publisher=nullptr;')
    cpp = '#include "b_reload_title590_profile.h"\n' + cpp
    cpp = once(cpp, 'check(activationRouter.Initialize(base),"production automatic runner wrapper configured once");',
        'check(activationRouter.Initialize(base),"production automatic runner wrapper configured once");\ncheck(title590Router.Initialize(base),"one retained automatic Title590 runner bridge");')
    anchor = 'check(activationRouter.Register(provider,generationIndex+2),"register immutable native generation before task creation");'
    cpp = once(cpp, anchor, anchor + r'''
    check(title590Router.Register(provider,generationIndex+2),"immutable Title590 router generation");
    title590Publisher=new b_reload_title590_publish::Publisher;
    check(title590Publisher->Initialize({base,generationIndex+2,&provider,&title590Router,true}),"Title590 start publisher bound before worker creation");
''')
    cpp = once(cpp, 'cc.provider=&provider;', 'cc.provider=&provider;cc.title590=title590Publisher;')
    cpp = once(cpp, 'if(self==auxCallable){++auxBodies;return;}',
        'if(self==auxCallable){++auxBodies;if(scenario==L"title590-exception")RaiseException(0xE014CC92,0,0,nullptr);return;}')
    anchor = '    bool titleException=titleInvokeWithException();session.Snapshot(r);'
    cpp = once(cpp, anchor, anchor + r'''
    b_reload_title590_publish::Report titleStart{};
    b_reload_title590_router::Report titleWorker{};
    check(title590Publisher->Snapshot(titleStart)&&title590Router.Snapshot(generationIndex+2,titleWorker),"Title590 actual source/worker reports");
    check(titleStart.captured==1&&titleStart.samples[0].rip==base+0x834B60&&titleStart.samples[0].rcx==title+0x590,"Title590 start CONTEXT from native initializer");
    if(scenario==L"title590-wrong-wait") {
        check(titleStart.error==checkpoint_task_native_start::Error::WaitStack&&!titleStart.published&&!titleWorker.selected&&titleStart.workerResumed,"wrong native wait refuses publication and resumes original worker");
    } else {
        check(titleStart.published&&titleStart.waitStackVerified&&titleStart.eventUnsignaled&&titleStart.workerResumed,"Title590 runner published only at suspended native unsignaled wait");
        check(titleWorker.selected&&titleWorker.beforeNative&&titleWorker.armed&&titleWorker.finally&&titleWorker.ports.role==2,"Title590 worker automatically begins and finishes its own role ports");
        check(titleWorker.ports.finished&&titleWorker.ports.restored&&!titleWorker.ports.uncertain&&!memcmp(titleWorker.ports.originalDr,titleWorker.ports.restoredDr,sizeof titleWorker.ports.originalDr),"Title590 hardware context restored");
        check(titleWorker.ports.captured==(scenario==L"title590-exception"?2u:4u),"actual Title590 worker source count");
    }
    printf("{\"title590_generation\":%u,\"starts\":%u,\"published\":%u,\"wait_verified\":%u,\"automatic_worker\":%u,\"worker_captured\":%u,\"worker_finally\":%u,\"worker_abnormal\":%u,\"error\":%u}\n",generationIndex+2,titleStart.captured,titleStart.published,titleStart.waitStackVerified,titleWorker.selected,titleWorker.ports.captured,titleWorker.finally,titleWorker.abnormal,unsigned(titleStart.error));
    if(scenario==L"title590-exception"||scenario==L"title590-wrong-wait") {
        completion::Report failed{};check(completionAdapter->Snapshot(failed)&&!failed.active&&failed.starts590==1,"failed generation retains actual start without making completion receipt");
        for(unsigned i=0;i<failed.scopeCount;++i)check(failed.scopes[i].finally&&failed.scopes[i].restored&&!failed.scopes[i].uncertain,"negative Title source scope restores all debug registers");
        if(scenario==L"title590-exception")check(titleWorker.abnormal&&!titleWorker.after&&titleWorker.ports.providerScopeAbandoned==1,"Title590 native exception preserves FINALLY and abandons incomplete task");
        check(!provider.CloseCompletedWindow(generationIndex+2),"failed Title590 cannot close generation");
        return finishReport(r,true);
    }
''')
    cpp = cpp.replace('CheckpointLoadWorkerBridgeSnapshot(1,&titleStats)', 'BReloadTitleBridgeSnapshot(1,&titleStats)')
    # Source v2 now owns the Title bridge. The frozen six-entry/Load bridge
    # retains its independent bank and remains unchanged.
    cpp = cpp.replace('CheckpointLoadWorkerBridgeSnapshot(1,&stats)', 'BReloadTitleBridgeSnapshot(1,&stats)')
    machine = (P / 'checkpoint_task_completion_fixture_machine.inc').read_text(encoding='utf-8-sig')
    machine = machine.replace('completion::', 'checkpoint_task_completion::')
    old = 'static void completionStart590(uintptr_t owner){check(owner==title,"actual Title update supplies own owner");startEmbedded(2);put<DWORD>(title+0x470,16);}\n'
    machine = once(machine, old, '')
    machine = once(machine, '{0x4BEEE0,uintptr_t(&completionStart590)},', '{0x394470,uintptr_t(&nativeNullDouble)},')
    anchor = '    memcpy(reinterpret_cast<void*>(base+0x4F7050),checkpoint_task_completion::LoadJoinBytes,sizeof checkpoint_task_completion::LoadJoinBytes);'
    machine = once(machine, anchor, '    memcpy(reinterpret_cast<void*>(base+0x4BEEE0),b_reload_title590_profile::StartBytes,sizeof b_reload_title590_profile::StartBytes);\n' + anchor)
    old = 'auto*joins=new RUNTIME_FUNCTION[2]{{0x4AA7B0,0x4AB074,0x8C0},{0x4F7050,0x4F70A4,0x8A0}};check(RtlAddFunctionTable(joins,2,base),'
    new = 'const unsigned char start590Uw[]={1,10,4,0,10,0x72,6,0x70,5,0x34,10,0};memcpy(reinterpret_cast<void*>(base+0x920),start590Uw,sizeof start590Uw);auto*joins=new RUNTIME_FUNCTION[3]{{0x4AA7B0,0x4AB074,0x8C0},{0x4BEEE0,0x4BEF50,0x920},{0x4F7050,0x4F70A4,0x8A0}};check(RtlAddFunctionTable(joins,3,base),'
    machine = once(machine, old, new)
    machine = once(machine, '0x4BE000u,0x40B000u', '0x4BE000u,0x394000u,0x40B000u')
    machine = once(machine, 'if(t.role)return syntheticEmbeddedEntry(p);', 'if(t.role==1)return syntheticEmbeddedEntry(p);')
    machine = once(machine, '    nativeFixtureTask=&t;\n    if(scenario', '    nativeFixtureTask=&t;nativeUnboundExecuting=t.role==2; // Native runner supplies its real two-argument ABI.\n    if(scenario')
    machine = once(machine, 'if(scenario==L"start-wrong-wait"){SetEvent(t.ready);', 'if(scenario==L"start-wrong-wait"||(scenario==L"title590-wrong-wait"&&t.role==2)){SetEvent(t.ready);')
    anchor = '    check(activationRouter.Snapshot(generationIndex+2,activationReport),"retained activation report");'
    machine = once(machine, anchor, '    if(t.role==2)return t.abnormal?1:0;\n' + anchor)
    old = 'check(control==load+0x478&&payload==base+0x508B40,"actual archived native initializer passes Load constructor args");'
    new = 'const unsigned role=control==title+0x590?2:0;check(control==(role?title+0x590:load+0x478)&&payload==base+(role?0x466600:0x508B40),"archived initializer supplies exact Load or Title590 constructor args");'
    machine = once(machine, old, new)
    machine = once(machine, 'auto*t=new EmbeddedPort;embeddedPorts[0]=t;t->image=base;t->owner=load;t->control=control;t->callable=loadCallable;t->object=alloc(4096);',
        'auto*t=new EmbeddedPort;embeddedPorts[role]=t;t->role=role;t->image=base;t->owner=role?title:load;t->control=control;t->callable=role?auxCallable:loadCallable;t->object=alloc(4096);')
    cpp = once(cpp, '#include "checkpoint_task_completion_fixture_ports.inc"', '#include "b_reload_title590_fixture_ports.inc"')
    ports = (P / 'checkpoint_task_completion_fixture_ports.inc').read_text(encoding='utf-8-sig')
    ports = once(ports, '#include "checkpoint_task_completion_fixture_machine.inc"', '#include "b_reload_title590_machine.inc"')
    return cpp, asm, machine, ports


def main():
    private_string = os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    if not private_string or any(c in private_string for c in ('"', '\n', '%', '&', '|', '<', '>')):
        raise SystemExit('Set SAN14_PRIVATE_FIXTURE_ROOT; no tests ran.')
    private = Path(private_string).resolve()
    archive = private / 'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
    image_file = private / 'game-runtime-image.bin'
    expected = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    if not archive.is_file() or not image_file.is_file() or sha(archive) != expected or sha(image_file) != '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268':
        raise SystemExit('Missing or changed private inputs; no tests ran.')
    frozen = load_module('completion_build', 'checkpoint_task_completion_test.py')
    units = [n for n in frozen.UNITS if n not in ('checkpoint_task_completion_fixture', 'checkpoint_task_completion_ports')]
    units += NEW_UNITS
    asm_units = ['checkpoint_persistent_bridge', 'checkpoint_guest_native_session_fixture',
                 'checkpoint_persistent_authorized_bridge', 'checkpoint_native_input_hwbp_fixture',
                 'checkpoint_load_worker_bridge', 'b_reload_title_bridge']
    sources = set()
    todo = [f'{u}.cpp' for u in units] + [f'{u}.asm' for u in asm_units]
    todo += ['b_reload_title590_test.py', 'b_reload_title_source_test.py', 'checkpoint_task_completion_test.py',
             'checkpoint_task_completion_fixture.cpp', 'checkpoint_task_completion_fixture.asm']
    private_inputs = {str(archive.relative_to(private)): sha(archive), 'game-runtime-image.bin': sha(image_file)}
    while todo:
        name = todo.pop()
        if name in sources or name == 'b_reload_title590_profile.h':
            continue
        path = P / name
        if not path.is_file():
            path = private / name
            if not path.is_file():raise SystemExit('Missing input ' + name)
            private_inputs[name] = sha(path)
            continue
        sources.add(name)
        if path.suffix in ('.h', '.cpp', '.inc'):
            todo.extend(re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.M))
    before = {n: sha(P / n) for n in sources}
    run = P / 'b_reload_title590_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    raw = image_file.read_bytes()[0x4BEEE0:0x4BEF50]
    (run / 'b_reload_title590_profile.h').write_text('#pragma once\nnamespace b_reload_title590_profile {inline constexpr unsigned char StartBytes[]={' + ','.join(hex(b) for b in raw) + '};}\n')
    cpp, asm, machine, ports = fixture_sources()
    (run / 'fixture.cpp').write_text(cpp, encoding='utf-8')
    (run / 'fixture.asm').write_text(asm, encoding='utf-8')
    (run / 'b_reload_title590_machine.inc').write_text(machine, encoding='utf-8')
    (run / 'b_reload_title590_fixture_ports.inc').write_text(ports, encoding='utf-8')
    flags = frozen.FLAGS + f' /I"{run}" /I"{P}" /I"{private}"'
    commands = [f'cl {flags} /c /Fo"production_{n}.obj" "{P / (n + ".cpp")}"' for n in NEW_UNITS]
    objects = []
    for name in units:
        obj = name + '.obj';objects.append(obj)
        remap = frozen.REMAP if name == 'checkpoint_dynamic_cc_load_observer' else ''
        commands.append(f'cl {flags} {frozen.DEFS} /DB_RELOAD_TITLE_SOURCE_FIXTURE {remap} /c /Fo"{obj}" "{P / (name + ".cpp")}"')
    commands.append(f'cl {flags} {frozen.DEFS} /DB_RELOAD_TITLE_SOURCE_FIXTURE /c /Fofixture.obj fixture.cpp')
    objects.append('fixture.obj')
    for name in asm_units:
        obj = name + '_asm.obj';objects.append(obj)
        commands.append(f'ml64 /nologo /c /Fo"{obj}" "{P / (name + ".asm")}"')
    commands += ['ml64 /nologo /c /Fo fixture_asm.obj fixture.asm', 'link /nologo /incremental:no /OUT:fixture.exe ' + ' '.join(objects) + ' fixture_asm.obj']
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    build = run / 'build.cmd'
    build.write_text('@echo off\nsetlocal\ncall "' + vc + '" >nul\nif errorlevel 1 exit /b 1\n' + '\n'.join(c + '\nif errorlevel 1 exit /b 1' for c in commands) + '\n')
    process = subprocess.run(['cmd', '/c', str(build)], cwd=run, capture_output=True, text=True, encoding='mbcs', errors='replace')
    (run / 'build.log').write_text(process.stdout + process.stderr, encoding='utf-8')
    if process.returncode:
        print('Build failed; see', run / 'build.log');raise SystemExit(process.returncode)
    rows = []
    for case in CASES:
        folder = run / case;first = folder / '0/svdexccSC03.s14';first.parent.mkdir(parents=True);shutil.copyfile(archive, first)
        second = folder / '1/svdexccSC03.s14';second.parent.mkdir();payload = bytearray(archive.read_bytes());payload[77] ^= 0x5a;payload.extend(bytes(range(128)));second.write_bytes(payload);second_sha = sha(second)
        process = subprocess.run([str(run / 'fixture.exe'), case, str(first), str(folder)], cwd=run, capture_output=True, text=True, errors='replace', timeout=45)
        (folder / 'stdout.txt').write_text(process.stdout, encoding='utf-8');(folder / 'stderr.txt').write_text(process.stderr, encoding='utf-8')
        records = [json.loads(line) for line in process.stdout.splitlines() if line.startswith('{')]
        passed = bool(records and records[-1].get('passed') and process.returncode == 0 and sha(first) == expected and sha(second) == second_sha)
        rows.append(dict(case=case, passed=passed, exit=process.returncode, records=records))
        print(case, 'PASS' if passed else 'FAIL', flush=True)
    unchanged = all(sha(P / n) == h for n, h in before.items()) and all(sha(private / n) == h for n, h in private_inputs.items())
    result = dict(schema='san14.b-reload-title590-owned.v1', result='PASS' if unchanged and all(r['passed'] for r in rows) else 'FAIL',
        cases=rows, sources=before, private_inputs=private_inputs, inputs_unchanged=unchanged,
        production_objects={n: sha(run / f'production_{n}.obj') for n in NEW_UNITS}, fixture_sha256=sha(run / 'fixture.exe'),
        game_access=False, actual_title590_start_context=True, actual_title590_wait_before_publication=True,
        title590_automatic_worker_begin=True, title590_fixture_manual_begin=False,
        title520_fixture_manual_begin=True, parent_sources_installed=False, load_finalize_source_installed=False,
        real_game_reload=False, full_world=False, room_ready=False,
        scope='Archived Title.Update/4BEEE0/834B60/83A930/834D10 execute on CPU with actual native CONTEXT delivery; Title590 runner is automatically published and observes its role. Thread construction, engine/Steam payloads, parent and Title520 sources remain explicit owned doubles.')
    path = run / 'result.json';path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': result['result'], 'cases': len(rows), 'path': str(path)}))
    raise SystemExit(0 if result['result'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
