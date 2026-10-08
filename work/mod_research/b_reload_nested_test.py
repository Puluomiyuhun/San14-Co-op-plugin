"""Archived Root and nested Load observers composed in both queue generations.

No game/Steam discovery. OS contexts supply generic Root and nested captures;
activation and business remain fixtures, not two legal game loads.
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


previous = module('nested_root_previous', 'b_reload_root_worker_test.py')
once = previous.once
NEW_UNITS = ('b_reload_nested_root_ports','b_reload_nested_start','b_reload_nested_completion','b_reload_nested_input')
REUSED_UNITS = tuple(u for u in previous.REUSED_UNITS if u != 'b_reload_title590_ports') + ('checkpoint_native_task_provider_worker',)
CASES = previous.CASES + ('root-lease-refusals',)


def fixture_sources():
    cpp, asm, machine, ports = previous.fixture_sources()
    cpp='#include "b_reload_nested_debug.h"\n'+cpp
    cpp=once(cpp,'static void check(bool x,const char*s)', '''static bool nestedDrEqual(const std::uint64_t*a,const std::uint64_t*b){return a[0]==b[0]&&a[1]==b[1]&&a[2]==b[2]&&a[3]==b[3]&&((a[4]^b[4])&0xE00Full)==0&&((a[5]^b[5])&~0x400ull)==0;}
static void check(bool x,const char*s)''')
    cpp=cpp.replace('!memcmp(r.prefetch.original_dr,r.prefetch.restored_dr,sizeof r.prefetch.original_dr)', 'nestedDrEqual(r.prefetch.original_dr,r.prefetch.restored_dr)')
    cpp=cpp.replace('!memcmp(q.originalDr,q.restoredDr,sizeof q.originalDr)', 'nestedDrEqual(q.originalDr,q.restoredDr)')
    cpp=cpp.replace('all six debug registers exactly restored','all six debug registers restored except OS-normalized reserved bits')
    cpp=cpp.replace('automatic normal/finally six DR restore','automatic normal/finally six DR semantic restore')
    machine=machine.replace('!memcmp(startReport.originalDr,startReport.restoredDr,sizeof startReport.originalDr)', 'nestedDrEqual(startReport.originalDr,startReport.restoredDr)')
    cpp=once(cpp,'static LONG WINAPI parentUnhandled(EXCEPTION_POINTERS*e){',r'''static LONG WINAPI parentUnhandled(EXCEPTION_POINTERS*e){
    {auto&c=*e->ContextRecord;printf("DEBUG dr=%llx,%llx,%llx,%llx,%llx,%llx\n",c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7);
     if(rootExercise){rootports::Report r{};rootports::Snapshot(rootExercise->ports,r);printf("ROOT captured=%u error=%u finished=%u restored=%u uncertain=%u\n",r.captured,unsigned(r.error),r.finished,r.restored,r.uncertain);}
     if(admissionBundle){hw::HardwareReceipt r{};hw::Snapshot(admissionBundle->hardware,r);printf("INPUT entered=%u captured=%u finished=%u error=%u restored=%u uncertain=%u beforeDR=%llx,%llx,%llx,%llx,%llx,%llx afterDR=%llx,%llx,%llx,%llx,%llx,%llx\n",r.entered,r.captured,r.finished,unsigned(r.error),r.restored,r.restore_uncertain,r.original_dr[0],r.original_dr[1],r.original_dr[2],r.original_dr[3],r.original_dr[4],r.original_dr[5],r.restored_dr[0],r.restored_dr[1],r.restored_dr[2],r.restored_dr[3],r.restored_dr[4],r.restored_dr[5]);}}
''')
    begin=ports.index('static std::uint64_t runState(Invoke fn,')
    end=ports.index('static std::uint64_t routedUser(',begin)
    ports=ports[:begin]+'static std::uint64_t runState(Invoke,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);\n'+ports[end:]
    root=(P/'b_reload_root_worker_fixture.inc').read_text(encoding='utf-8')
    root='static void nestedLeaseProbe();\n'+root
    root=once(root,' ++rootExercise->bodies;++rootTotalBodies;',
              ' if(providerCase==L"root-lease-refusals")nestedLeaseProbe();\n ++rootExercise->bodies;++rootTotalBodies;')
    root=once(root,'const bool normal=providerCase==L"root-normal"||providerCase==L"root-two-tasks";',
              'const bool normal=providerCase==L"root-normal"||providerCase==L"root-two-tasks"||providerCase==L"root-lease-refusals";')
    root=once(root,'struct RootExercise {','struct RootExercise {Invoke fn=nullptr;std::uint64_t args[3]{},value=0;')
    root=once(root,'rootExercise->task->state&&a==11&&b==22&&c==33',
              'rootExercise->task->state&&(rootExercise->fn?(a==rootExercise->args[0]&&b==rootExercise->args[1]&&c==rootExercise->args[2]):(a==11&&b==22&&c==33))')
    root=once(root,' ++rootExercise->bodies;++rootTotalBodies;',
              ' ++rootExercise->bodies;++rootTotalBodies;if(rootExercise->fn){rootExercise->value=rootExercise->fn(self,a,b,c);return rootExercise->value;}')
    ports=once(ports,'#include "b_reload_root_worker_fixture.inc"',root)
    ports+='\n#include "b_reload_nested_fixture.inc"\n'
    anchor='    check(queueRuns==2&&queuePopCallbacks==2'
    pos=cpp.index(anchor)
    cpp=cpp[:pos]+r'''
    check(nestedTasks==16&&nestedCaptures==48&&nestedLoadTasks==8,"both generations use actual Root sources for all 16 generic tasks");
    printf("{\"nested_root_tasks\":%u,\"nested_root_captures\":%u,\"nested_load_tasks\":%u,\"manual_root_capture\":false}\n",nestedTasks,nestedCaptures,nestedLoadTasks);
'''+cpp[pos:]
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
    units = [u for u in frozen.UNITS if u not in ('checkpoint_task_completion_fixture', 'checkpoint_task_completion_ports', 'checkpoint_native_task_provider', 'checkpoint_task_native_start','checkpoint_persistent_input_hwbp')] + list(REUSED_UNITS) + list(NEW_UNITS)
    asm_units = ('checkpoint_persistent_bridge', 'checkpoint_guest_native_session_fixture', 'checkpoint_persistent_authorized_bridge', 'checkpoint_native_input_hwbp_fixture', 'checkpoint_load_worker_bridge', 'b_reload_title_bridge', 'b_reload_title520_bridge', 'b_reload_parent_bridge')
    generated = {'b_reload_root_worker_profile.h', 'b_reload_parent_profile.h', 'b_reload_title520_profile.h', 'b_reload_title590_profile.h'}
    sources = set()
    todo = [u+'.cpp' for u in units] + [u+'.asm' for u in asm_units]
    todo += ['b_reload_nested_test.py','b_reload_nested_fixture.inc','b_reload_root_worker_test.py', 'b_reload_root_worker_fixture.inc', 'b_reload_bound_test.py', 'b_reload_bound_fixture.inc', 'b_reload_queue_test.py', 'b_reload_queue_fixture.inc', 'b_reload_queue_parent_fixture.inc', 'b_reload_parent_test.py', 'b_reload_title520_test.py', 'b_reload_title590_test.py', 'b_reload_title_source_test.py', 'checkpoint_task_completion_test.py', 'checkpoint_task_completion_fixture.cpp', 'checkpoint_task_completion_fixture.asm']
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
    run = P / 'b_reload_nested_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    image = image_file.read_bytes()
    profiles = {'b_reload_root_worker_profile': {'RunnerBytes': (0x834D10,0x834E75), 'ThunkBytes': (0x50B730,0x50B79A), 'YieldBytes': (0x50B690,0x50B6FF)}, 'b_reload_parent_profile': {'SchedulerBytes': (0x509FE0,0x50B690), 'OuterCall': (0x13DC09,0x13DC0E), 'PhaseCall': (0x50B41B,0x50B420), 'WaitBytes': (0x834EF0,0x834EFE)}, 'b_reload_title590_profile': {'StartBytes': (0x4BEEE0,0x4BEF50)}, 'b_reload_title520_profile': {'FinalizeBytes': (0x497110,0x49713F), 'ThunkBytes': (0x4FAC30,0x4FAC3C), 'CallbackBytes': (0x4CC690,0x4CC7C5), 'StartBytes': (0x4BEE50,0x4BEED7)}}
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
        commands.append(f'cl {flags} {frozen.DEFS} /DB_RELOAD_TITLE_SOURCE_FIXTURE /DB_RELOAD_PARENT_FIXTURE /DB_RELOAD_ROOT_WORKER_FIXTURE {remap} /c /Fo"{obj}" "{P / (name+".cpp")}"')
    commands.append(f'cl {flags} {frozen.DEFS} /DB_RELOAD_TITLE_SOURCE_FIXTURE /DB_RELOAD_PARENT_FIXTURE /DB_RELOAD_ROOT_WORKER_FIXTURE /c /Fofixture.obj fixture.cpp');objects.append('fixture.obj')
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
    result=dict(schema='san14.b-reload-nested-owned.v1', worker_expected_generation_atomic=True, actual_root_observer_activation_is_fixture=True, nested_root_load_ports_composed=True, actual_root_yield_executed=False, parent_expected_generation_atomic=True, all_native_sources_bound=False, direct_capture_cases_are_fixtures=True,result='PASS' if unchanged and all(x['passed'] for x in rows) else 'FAIL',cases=rows,sources=before,private_inputs=private_inputs,inputs_unchanged=unchanged,production_objects={u:sha(run/f'production_{u}.obj') for u in NEW_UNITS},fixture_sha256=sha(run/'fixture.exe'),game_access=False,actual_queue_finalize=True,synthetic_finalize_call=False,queue_root_worker_sources_are_doubles=False,independent_root_sources_are_os_contexts=True,constructor_and_engine_business_are_doubles=True,production_installer=False,real_game_reload=False,full_world=False,room_ready=False)
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':result['result'],'cases':len(rows),'path':str(path)}));raise SystemExit(0 if result['result']=='PASS' else 1)


if __name__ == '__main__':
    main()
