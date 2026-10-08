"""Owned native scheduler queue Finalize, immutable windows, both Title roles.

No game/Steam discovery. Allocator, status, root worker and engine business
remain explicit fixture services; actual scheduler and Finalize paths execute.
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

P = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, P / file)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


previous = module('queue_parent_previous', 'b_reload_parent_test.py')
once = previous.once
NEW_UNITS = ('b_reload_queue_parent_source', 'b_reload_queue_finalize_ports', 'b_reload_queue_finalize_source')
REUSED_UNITS = ('b_reload_title_bridge', 'b_reload_title590_router', 'b_reload_title590_publish', 'b_reload_title590_ports', 'b_reload_title_source_v2', 'b_reload_title520_bridge', 'b_reload_title520_router', 'b_reload_title520_publish', 'b_reload_parent_bridge')
CASES = ('success', 'reuse-full-addresses', 'completion-wait')


def fixture_sources():
    cpp, asm, machine, ports = previous.fixture_sources()
    for old, new in (('b_reload_parent_source', 'b_reload_queue_parent_source'), ('b_reload_finalize_source', 'b_reload_queue_finalize_source'), ('b_reload_finalize_ports', 'b_reload_queue_finalize_ports')):
        cpp = cpp.replace(old, new)
    ports = once(ports, '#include "b_reload_parent_fixture.inc"', '#include "b_reload_queue_parent_fixture.inc"\n#include "b_reload_queue_fixture.inc"')
    cpp = once(cpp, '    prepareParentMachine();', '    prepareParentMachine();prepareQueueMachine();queueIdlePasses(500);')
    start = cpp.index('static DWORD WINAPI titleStartOnOtherParent(')
    end = cpp.index('static bool completionExceptionCaught=', start)
    cpp = cpp[:start] + 'static DWORD WINAPI titleStartOnOtherParent(void*p){return queueFinalizeOnParent(p);}\n' + cpp[end:]
    anchor = 'check(provider.Register(pcfg)&&provider.OpenWindow(generationIndex+2),"retained native-source bank and observation window");'
    cpp = once(cpp, anchor, anchor + r'''
    {tp::Report p{};check(provider.Snapshot(generationIndex+2,p),"immutable parent binding from registered Provider");queueBinding={p.generation,p.attempt,p.epoch};auto wrong=queueBinding;++wrong.epoch;
     check(!parentSource.RegisterWindow(wrong),"wrong Provider epoch cannot register parent authority");
     check(parentSource.RegisterWindow(queueBinding),"two immutable parent windows register once");check(!parentSource.BeginWindow(wrong),"wrong window identity cannot begin");
     check(parentSource.BeginWindow(queueBinding),"trusted load owner starts exact parent window");check(!parentSource.EndWindow(queueBinding),"unfinished Provider window cannot retire early");}
''')
    anchor = '    check(provider.CloseCompletedWindow(generationIndex+2)==!incomplete,"all THREE joins and drained tasks required with actual Session/planning receipts");'
    cpp = once(cpp, anchor, anchor + '\n    check(parentSource.EndWindow(queueBinding),"completed generation retires its exact parent window");check(!parentSource.BeginWindow(queueBinding),"retired generation can never be reopened");queueIdlePasses(500);')
    anchor = '    const auto&fq=finalReport.scopes[0];'
    cpp = once(cpp, anchor, r'''
    check(finalReport.caller==base+0x50B1B8&&!finalReport.currentAtEntry&&finalReport.parentCall&&finalReport.binding.generation==queueBinding.generation&&finalReport.binding.attempt==queueBinding.attempt&&finalReport.binding.epoch==queueBinding.epoch&&finalReport.load==load&&finalReport.closure==closure&&finalReport.title==title,"Finalize comes from actual pop caller/current zero and exact parent generation/closure");
''' + anchor)
    cpp = once(cpp, 'parentReport.scopes==parentReport.phaseStarted&&parentQueueChecks==parentReport.scopes&&parentReport.accepted[0]==parentReport.scopes&&parentReport.accepted[1]==parentReport.scopes&&parentReport.accepted[3]==parentReport.scopes', 'parentReport.scopes==parentReport.phaseStarted&&parentQueueChecks+queueRuns==parentReport.scopes&&parentReport.accepted[0]+queueRuns==parentReport.scopes&&parentReport.accepted[1]+queueRuns==parentReport.scopes&&parentReport.accepted[3]+queueRuns==parentReport.scopes')
    cpp = once(cpp, 'parentStats.started==parentReport.scopes&&parentStats.finally_calls==parentReport.scopes', 'parentStats.started==parentReport.scopes+parentReport.idleForwarded&&parentStats.finally_calls==parentStats.started')
    anchor = '    rt::Report report{};report=physicalReport().route;'
    cpp = once(cpp, anchor, r'''
    check(queueRuns==2&&queuePopCallbacks==2&&queueStatusCalls==8&&queueZeroCurrentChecks==8&&parentReport.registeredWindows==2&&parentReport.retiredWindows==2&&parentReport.idleForwarded==2000&&!parentReport.window.generation,"two true queue pops and 2000 unowned scheduler frames consume no load scope");
    printf("{\"queue_runs\":%u,\"actual_pop_calls\":%u,\"zero_current_checks\":%u,\"parent_scopes\":%u,\"idle_forwarded\":%u,\"retired_windows\":%u,\"synthetic_finalize_call\":false}\n",queueRuns,queuePopCallbacks,queueZeroCurrentChecks,parentReport.scopes,parentReport.idleForwarded,parentReport.retiredWindows);
''' + anchor)
    if 'using Finalize=' in cpp or 'Existing Finalize fixture boundary' in cpp:
        raise RuntimeError('Synthetic Finalize invocation remains')
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
    frozen = module('queue_build_previous', 'checkpoint_task_completion_test.py')
    units = [u for u in frozen.UNITS if u not in ('checkpoint_task_completion_fixture', 'checkpoint_task_completion_ports')] + list(REUSED_UNITS) + list(NEW_UNITS)
    asm_units = ('checkpoint_persistent_bridge', 'checkpoint_guest_native_session_fixture', 'checkpoint_persistent_authorized_bridge', 'checkpoint_native_input_hwbp_fixture', 'checkpoint_load_worker_bridge', 'b_reload_title_bridge', 'b_reload_title520_bridge', 'b_reload_parent_bridge')
    generated = {'b_reload_parent_profile.h', 'b_reload_title520_profile.h', 'b_reload_title590_profile.h'}
    sources = set()
    todo = [u+'.cpp' for u in units] + [u+'.asm' for u in asm_units]
    todo += ['b_reload_queue_test.py', 'b_reload_queue_fixture.inc', 'b_reload_queue_parent_fixture.inc', 'b_reload_parent_test.py', 'b_reload_title520_test.py', 'b_reload_title590_test.py', 'b_reload_title_source_test.py', 'checkpoint_task_completion_test.py', 'checkpoint_task_completion_fixture.cpp', 'checkpoint_task_completion_fixture.asm']
    private_inputs = {str(archive.relative_to(private)): sha(archive), 'game-runtime-image.bin': sha(image_file)}
    while todo:
        name = todo.pop()
        if name in sources or name in generated:
            continue
        path = P / name
        if not path.is_file():
            path = private / name
            if not path.is_file():raise SystemExit('Missing input '+name)
            private_inputs[name] = sha(path)
            continue
        sources.add(name)
        if path.suffix in ('.cpp', '.h', '.inc'):
            todo.extend(re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.M))
    before = {n: sha(P / n) for n in sources}
    run = P / 'b_reload_queue_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    image = image_file.read_bytes()
    profiles = {'b_reload_parent_profile': {'SchedulerBytes': (0x509FE0,0x50B690), 'OuterCall': (0x13DC09,0x13DC0E), 'PhaseCall': (0x50B41B,0x50B420), 'WaitBytes': (0x834EF0,0x834EFE)}, 'b_reload_title590_profile': {'StartBytes': (0x4BEEE0,0x4BEF50)}, 'b_reload_title520_profile': {'FinalizeBytes': (0x497110,0x49713F), 'ThunkBytes': (0x4FAC30,0x4FAC3C), 'CallbackBytes': (0x4CC690,0x4CC7C5), 'StartBytes': (0x4BEE50,0x4BEED7)}}
    for namespace, spans in profiles.items():
        body = '#pragma once\nnamespace '+namespace+' {\n'
        for name,(start,end) in spans.items():
            body += 'inline constexpr unsigned char '+name+'[]={'+','.join(hex(v) for v in image[start:end])+'};\n'
        (run / (namespace+'.h')).write_text(body+'}\n')
    cpp, asm, machine, ports = fixture_sources()
    for name, content in (('fixture.cpp',cpp), ('fixture.asm',asm), ('b_reload_title520_machine.inc',machine), ('b_reload_title520_fixture_ports.inc',ports)):
        (run / name).write_text(content, encoding='utf-8')
    flags = frozen.FLAGS + f' /I"{run}" /I"{P}" /I"{private}"'
    commands = [f'cl {flags} /c /Fo"production_{u}.obj" "{P / (u+".cpp")}"' for u in NEW_UNITS]
    objects = []
    for name in units:
        obj = name+'.obj';objects.append(obj)
        remap = frozen.REMAP if name == 'checkpoint_dynamic_cc_load_observer' else ''
        commands.append(f'cl {flags} {frozen.DEFS} /DB_RELOAD_TITLE_SOURCE_FIXTURE /DB_RELOAD_PARENT_FIXTURE {remap} /c /Fo"{obj}" "{P / (name+".cpp")}"')
    commands.append(f'cl {flags} {frozen.DEFS} /DB_RELOAD_TITLE_SOURCE_FIXTURE /DB_RELOAD_PARENT_FIXTURE /c /Fofixture.obj fixture.cpp');objects.append('fixture.obj')
    for name in asm_units:
        obj=name+'_asm.obj';objects.append(obj);commands.append(f'ml64 /nologo /c /Fo"{obj}" "{P / (name+".asm")}"')
    commands += ['ml64 /nologo /c /Fo fixture_asm.obj fixture.asm', 'link /nologo /incremental:no /OUT:fixture.exe '+' '.join(objects)+' fixture_asm.obj']
    build = run / 'build.cmd'
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    build.write_text('@echo off\nsetlocal\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    proc = subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,text=True,encoding='mbcs',errors='replace')
    (run/'build.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
    if proc.returncode:print('Build failed; see',run/'build.log');raise SystemExit(proc.returncode)
    rows=[]
    for case in CASES:
        folder=run/case;first=folder/'0/svdexccSC03.s14';first.parent.mkdir(parents=True);shutil.copyfile(archive,first)
        second=folder/'1/svdexccSC03.s14';second.parent.mkdir();payload=bytearray(archive.read_bytes());payload[77]^=0x5a;payload.extend(bytes(range(128)));second.write_bytes(payload);second_sha=sha(second)
        proc=subprocess.run([str(run/'fixture.exe'),case,str(first),str(folder)],cwd=run,capture_output=True,text=True,errors='replace',timeout=60)
        (folder/'stdout.txt').write_text(proc.stdout,encoding='utf-8');(folder/'stderr.txt').write_text(proc.stderr,encoding='utf-8')
        records=[json.loads(l) for l in proc.stdout.splitlines() if l.startswith('{')]
        passed=bool(records and records[-1].get('passed') and proc.returncode==0 and sha(first)==expected and sha(second)==second_sha)
        rows.append(dict(case=case,passed=passed,exit=proc.returncode,records=records));print(case,'PASS' if passed else 'FAIL',flush=True)
    unchanged=all(sha(P/n)==h for n,h in before.items()) and all(sha(private/n)==h for n,h in private_inputs.items())
    result=dict(schema='san14.b-reload-queue-owned.v1',result='PASS' if unchanged and all(x['passed'] for x in rows) else 'FAIL',cases=rows,sources=before,private_inputs=private_inputs,inputs_unchanged=unchanged,production_objects={u:sha(run/f'production_{u}.obj') for u in NEW_UNITS},fixture_sha256=sha(run/'fixture.exe'),game_access=False,actual_queue_finalize=True,synthetic_finalize_call=False,root_worker_sources_are_doubles=True,constructor_and_engine_business_are_doubles=True,production_installer=False,real_game_reload=False,full_world=False,room_ready=False)
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':result['result'],'cases':len(rows),'path':str(path)}));raise SystemExit(0 if result['result']=='PASS' else 1)


if __name__ == '__main__':
    main()
