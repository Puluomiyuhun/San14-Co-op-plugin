"""Exercise a retained Title vtable publication in owned child processes.

The frozen completion fixture is transformed only in the ignored build folder.
Its existing native game services, parent ports and Title starts remain doubles.
No game process or Steam folder is opened. Private archived inputs are read only.
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
INTEGRATION = ('success', 'reuse-full-addresses', 'late-old-root', 'completion-wait',
           'completion-native-exception', 'completion-stop')
NEGATIVE = ('source-stop-before-publish', 'source-slot-drift', 'source-code-drift',
            'source-writable-slot', 'source-adapter-stop', 'source-after-publish-conflict')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f'Frozen fixture anchor changed: {old[:80]}')
    return text.replace(old, new)


PUBLICATION = r'''
    // New production owner publishes the fixed native vtable source. The
    // child fixture uses private pages for its synthetic executable image.
    if(!generationIndex) {
        b_reload_title_source::Owner uninitialized;
        check(!uninitialized.Initialize({base,nullptr}),"missing completion adapter refused without consuming owner");
        check(titleSource.Initialize({base,completionAdapter}),"one retained Title source owner configures original-call bridge");
        const auto slot=base+0x12DAAF0+0x28;
        if(providerCase==L"source-stop-before-publish")titleSource.Stop();
        if(providerCase==L"source-adapter-stop")completionAdapter->Stop();
        if(providerCase==L"source-slot-drift"||providerCase==L"source-writable-slot") {
            DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(slot),8,PAGE_READWRITE,&old),"owned slot page writable for negative case");
            if(providerCase==L"source-slot-drift") {
                put<uintptr_t>(slot,base+0x4AA7B1);
                check(VirtualProtect(reinterpret_cast<void*>(slot),8,PAGE_READONLY,&old),"restore negative slot protection");
            }
        }
        if(providerCase==L"source-code-drift") {
            DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+0x4AA7B0),8,PAGE_READWRITE,&old),"owned code writable for negative case");
            *reinterpret_cast<BYTE*>(base+0x4AA7B0)^=1;
            check(VirtualProtect(reinterpret_cast<void*>(base+0x4AA7B0),8,PAGE_EXECUTE_READ,&old),"negative code restored RX");
        }
        const bool rejection=providerCase.rfind(L"source-",0)==0&&providerCase!=L"source-after-publish-conflict";
        const bool published=titleSource.Publish();
        check(published!=rejection,"source publication reflects exact source/configuration");
        if(rejection) {
            b_reload_title_source::Report rejected{};check(titleSource.Snapshot(rejected),"rejected publication report");
            check(!rejected.published&&!rejected.hooks.entries[0].dirty&&!rejected.hooks.entries[0].published,"refusal leaves source unmodified");
            const auto expected=providerCase==L"source-slot-drift"?base+0x4AA7B1:base+0x4AA7B0;
            check(at<uintptr_t>(slot)==expected,"negative branch cannot overwrite original or competing pointer");
            const auto expectedError=providerCase==L"source-stop-before-publish"?b_reload_title_source::Error::Stopped:
                providerCase==L"source-adapter-stop"?b_reload_title_source::Error::Completion:b_reload_title_source::Error::Source;
            check(rejected.error==expectedError,"refusal class is precise");
            printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"publication_refused\":true,\"error\":%u,\"game_access\":false}\n",providerCase.c_str(),failures?"false":"true",failures,unsigned(rejected.error));
            fflush(stdout);ExitProcess(failures?1:0);
        }
        if(providerCase==L"source-after-publish-conflict") {
            DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(slot),8,PAGE_READWRITE,&old),"owned published slot conflict");
            put<uintptr_t>(slot,base+0x4AA7B1);check(VirtualProtect(reinterpret_cast<void*>(slot),8,PAGE_READONLY,&old),"conflicting slot is RO again");
            check(!titleSource.Verify()&&at<uintptr_t>(slot)==base+0x4AA7B1,"verification detects conflict without overwriting competing owner");
            b_reload_title_source::Report rejected{};check(titleSource.Snapshot(rejected)&&rejected.error==b_reload_title_source::Error::Verification&&!rejected.verified,"conflict is terminal");
            printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"post_publication_conflict_detected\":true,\"game_access\":false}\n",providerCase.c_str(),failures?"false":"true",failures);
            fflush(stdout);ExitProcess(failures?1:0);
        }
        b_reload_title_source::Owner duplicate;
        check(!duplicate.Initialize({base,completionAdapter}),"second physical Title owner refused");
        check(!titleSource.Publish(),"publication cannot be repeated or reset");
    }
    check(titleSource.Verify(),"same Title source remains published across immutable generations");
'''


def fixture_source():
    text = (P / 'checkpoint_task_completion_fixture.cpp').read_text(encoding='utf-8-sig')
    text = '#include "b_reload_title_source.h"\nstatic b_reload_title_source::Owner titleSource;\n' + text
    # The historical fixture reconstructs its entire synthetic image between
    # generations. Exclude the retained Title source page from that operation;
    # never reinstate a lost pointer by fixture write or a second publisher.
    old = 'if(generationIndex){DWORD prior=0;check(VirtualProtect(reinterpret_cast<void*>(sharedImage),0x2200000,PAGE_READWRITE,&prior),"owned shared image writable for next synthetic world");memcpy(reinterpret_cast<void*>(sharedImage),reinterpret_cast<void*>(layout.config.base),0x2200000);'
    new = r'''if(generationIndex){DWORD prior=0;
        check(VirtualProtect(reinterpret_cast<void*>(sharedImage),0x12DA000,PAGE_READWRITE,&prior)&&VirtualProtect(reinterpret_cast<void*>(sharedImage+0x12DB000),0x2200000-0x12DB000,PAGE_READWRITE,&prior),"owned synthetic world reset excludes retained Title source page");
        memcpy(reinterpret_cast<void*>(sharedImage),reinterpret_cast<void*>(layout.config.base),0x12DA000);
        memcpy(reinterpret_cast<void*>(sharedImage+0x12DB000),reinterpret_cast<void*>(layout.config.base+0x12DB000),0x2200000-0x12DB000);'''
    text = replace_once(text, old, new)
    old = '    prepareNativeMachine();'
    text = replace_once(text, old, old + r'''
    if(!generationIndex)put<uintptr_t>(base+0x12DAAF0+0x28,base+0x4AA7B0);
    {DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+0x12DA000),4096,PAGE_READONLY,&old),"Title vtable page read-only before source publication");}
''')
    text = replace_once(text, '    if(!generationIndex)check(completion::Adapter::ConfigureTitle(base),"one retained transparent Title Update entry");', PUBLICATION)
    old = '    rt::Report report{};report=physicalReport().route;'
    text = replace_once(text, old, r'''
    check(titleSource.Verify(),"retained Title source verified after both generations");
    titleSource.Stop();
    check(titleSource.Verify(),"Stop leaves published bridge resident; no unsafe unhook");
    b_reload_title_source::Report sourceReport{};check(titleSource.Snapshot(sourceReport),"source final report");
    check(sourceReport.initialized&&sourceReport.bridgeConfigured&&sourceReport.publishAttempted&&sourceReport.published&&sourceReport.stopped&&sourceReport.verified&&sourceReport.modulePinned,"one source stays resident after both generations");
    check(sourceReport.hooks.count==1&&sourceReport.hooks.entries[0].published&&!sourceReport.hooks.entries[0].dirty&&sourceReport.hooks.entries[0].lastProtection==PAGE_READONLY,"single pointer CAS and original RO protection");
    check(!sourceReport.parentSourcesInstalled&&!sourceReport.titleStartsInstalled&&!sourceReport.fullInputHold&&!sourceReport.roomReady&&!sourceReport.gameValidated,"no whole-game guarantees fabricated");
    const unsigned expectedTitleCalls=providerCase==L"completion-wait"?5:
        providerCase==L"completion-native-exception"||providerCase==L"completion-stop"?3:4;
    CheckpointLoadWorkerBridgeStats titleStats{};check(CheckpointLoadWorkerBridgeSnapshot(1,&titleStats)&&titleStats.started==expectedTitleCalls&&titleStats.started==titleStats.finally_calls&&!titleStats.active&&!titleStats.cleanup_faults,"all indirect vtable Title calls flow through original/finally bridge");
    printf("{\"title_source\":true,\"published\":%u,\"stopped\":%u,\"verified\":%u,\"verify_calls\":%u,\"title_calls\":%llu,\"title_finally\":%llu,\"error\":%u}\n",sourceReport.published,sourceReport.stopped,sourceReport.verified,sourceReport.verifyCalls,titleStats.started,titleStats.finally_calls,unsigned(sourceReport.error));
''' + old)
    asm = (P / 'checkpoint_task_completion_fixture.asm').read_text(encoding='utf-8-sig')
    asm = replace_once(asm, '    call CheckpointLoadWorkerBridge1', '    mov rax,qword ptr [rcx]\n    call qword ptr [rax+28h]')
    return text, asm


def main():
    private_string = os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    if not private_string or any(c in private_string for c in ('"', '\n', '%', '&', '|', '<', '>')):
        raise SystemExit('Set SAN14_PRIVATE_FIXTURE_ROOT to the private research inputs; no tests ran.')
    private = Path(private_string).resolve()
    archive = private / 'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
    expected = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    image = private / 'game-runtime-image.bin'
    required = (archive, image, private / 'checkpoint_task_completion_profile.h')
    if not all(p.is_file() for p in required):
        raise SystemExit('Missing private archive/runtime/profile input; no tests ran.')
    if sha(archive) != expected or sha(image) != '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268':
        raise SystemExit('Private archive/runtime identity mismatch; no tests ran.')
    # Reuse only frozen build constants, never its main() or historical paths.
    spec = importlib.util.spec_from_file_location('frozen_completion_build', P / 'checkpoint_task_completion_test.py')
    frozen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen)
    sources = set()
    todo = [f'{u}.cpp' for u in frozen.UNITS if u != 'checkpoint_task_completion_fixture']
    todo += ['b_reload_title_source.cpp', 'b_reload_title_source.h', 'b_reload_title_source_test.py',
             'checkpoint_task_completion_fixture.cpp', 'checkpoint_task_completion_fixture.asm',
             'checkpoint_task_completion_test.py']
    asm_units = ['checkpoint_persistent_bridge', 'checkpoint_guest_native_session_fixture',
                 'checkpoint_persistent_authorized_bridge', 'checkpoint_native_input_hwbp_fixture',
                 'checkpoint_load_worker_bridge']
    todo += [f'{n}.asm' for n in asm_units]
    private_inputs = {str(p.relative_to(private)): sha(p) for p in required}
    while todo:
        name = todo.pop()
        if name in sources:
            continue
        path = P / name
        if not path.is_file():
            path = private / name
            if not path.is_file():
                raise SystemExit(f'Missing dependency {name}; no tests ran.')
            private_inputs[name] = sha(path)
            continue
        sources.add(name)
        if path.suffix in ('.cpp', '.h', '.inc'):
            todo.extend(re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.M))
    before = {name: sha(P / name) for name in sorted(sources)}
    run = P / 'b_reload_title_source_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    cpp, asm = fixture_source()
    (run / 'fixture.cpp').write_text(cpp, encoding='utf-8')
    (run / 'fixture.asm').write_text(asm, encoding='utf-8')
    flags = frozen.FLAGS + f' /I"{P}" /I"{private}"'
    commands = [f'cl {flags} /c /Foproduction_owner.obj "{P / "b_reload_title_source.cpp"}"',
                f'cl {flags} /c /Foproduction_completion.obj "{P / "checkpoint_task_completion_ports.cpp"}"']
    objs = []
    for name in (*[n for n in frozen.UNITS if n != 'checkpoint_task_completion_fixture'], 'b_reload_title_source'):
        remap = frozen.REMAP if name == 'checkpoint_dynamic_cc_load_observer' else ''
        obj = f'{name}.obj'
        objs.append(obj)
        commands.append(f'cl {flags} {frozen.DEFS} /DB_RELOAD_TITLE_SOURCE_FIXTURE {remap} /c /Fo"{obj}" "{P / (name + ".cpp")}"')
    commands.append(f'cl {flags} {frozen.DEFS} /DB_RELOAD_TITLE_SOURCE_FIXTURE /c /Fofixture.obj fixture.cpp')
    objs.append('fixture.obj')
    for name in asm_units:
        obj = f'{name}_asm.obj'
        objs.append(obj)
        commands.append(f'ml64 /nologo /c /Fo "{obj}" "{P / (name + ".asm")}"')
    commands.append('ml64 /nologo /c /Fo fixture_asm.obj fixture.asm')
    objs.append('fixture_asm.obj')
    commands.append('link /nologo /incremental:no /OUT:fixture.exe ' + ' '.join(objs))
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    build = run / 'build.cmd'
    build.write_text('@echo off\nsetlocal\ncall "' + vc + '" >nul\nif errorlevel 1 exit /b 1\n' + '\n'.join(c + '\nif errorlevel 1 exit /b 1' for c in commands) + '\n')
    process = subprocess.run(['cmd', '/c', str(build)], cwd=run, capture_output=True, text=True, errors='replace')
    (run / 'build.log').write_text(process.stdout + process.stderr, encoding='utf-8')
    if process.returncode:
        print(process.stdout + process.stderr)
        raise SystemExit(process.returncode)
    rows = []
    for case in (*INTEGRATION, *NEGATIVE):
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
        process = subprocess.run([str(run / 'fixture.exe'), case, str(first), str(folder)], cwd=run,
                                 capture_output=True, text=True, errors='replace', timeout=45)
        (folder / 'stdout.txt').write_text(process.stdout, encoding='utf-8')
        (folder / 'stderr.txt').write_text(process.stderr, encoding='utf-8')
        records = [json.loads(line) for line in process.stdout.splitlines() if line.startswith('{')]
        final = records[-1] if records else {'passed': False}
        row = {'case': case, 'passed': bool(final['passed'] and process.returncode == 0 and sha(first) == expected and sha(second) == second_sha),
               'exit': process.returncode, 'two_generation_attempts': case in INTEGRATION,
               'records': records}
        rows.append(row)
        print(case, 'PASS' if row['passed'] else 'FAIL', flush=True)
    unchanged = before == {n: sha(P / n) for n in before} and private_inputs == {n: sha(private / n) for n in private_inputs}
    result = {
        'schema': 'san14.b-reload-title-source-owned.v1',
        'result': 'PASS' if unchanged and all(r['passed'] for r in rows) else 'FAIL',
        'cases': rows, 'sources': before, 'private_inputs': private_inputs, 'inputs_unchanged': unchanged,
        'production_object_sha256': sha(run / 'production_owner.obj'),
        'production_completion_object_sha256': sha(run / 'production_completion.obj'),
        'fixture_sha256': sha(run / 'fixture.exe'),
        'generated_fixture_sha256': {'cpp': sha(run / 'fixture.cpp'), 'asm': sha(run / 'fixture.asm')},
        'game_access': False, 'steam_access': False, 'real_game_reload': False,
        'actual_title_slot_cas_and_page_protection': True,
        'actual_indirect_title_virtual_dispatch': True,
        'actual_title_join_context_capture': True,
        'parent_sources_installed': False, 'title_starts_installed': False,
        'title_worker_explicit_fixture_begin': True,
        'full_input_hold': False, 'room_ready': False,
        'scope': 'One retained Title vtable publisher plus frozen two-generation completion/session fixture. Indirect original native Title Update bytes and FINALLY execute on CPU. Native game service bodies, parent source captures and Title worker creation/start remain owned-process doubles. No external process opened.',
    }
    path = run / 'result.json'
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': result['result'], 'cases': len(rows), 'path': str(path)}))
    raise SystemExit(0 if result['result'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
