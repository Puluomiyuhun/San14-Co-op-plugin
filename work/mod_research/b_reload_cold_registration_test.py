"""Owned same-PE lifecycle to original cold registration; no game discovery."""
from pathlib import Path
from datetime import datetime
import hashlib,importlib.util,json,os,re,subprocess
P=Path(__file__).resolve().parent

def module(name,file):
    s=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    value=os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT','')
    if not value or any(x in value for x in ('"','\n','%','&','|','<','>')):raise SystemExit('Explicit private fixture root required')
    private=Path(value).resolve();image_file=private/'game-runtime-image.bin'
    if not image_file.is_file() or sha(image_file)!='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268':raise SystemExit('Private runtime archive unavailable/changed')
    base=module('bootstrap_build_base','checkpoint_task_completion_test.py');life=module('bootstrap_life','b_reload_lifecycle_test.py')
    units=[u for u in base.UNITS if u not in ('checkpoint_task_completion_fixture','checkpoint_task_completion_ports','checkpoint_native_task_provider','checkpoint_task_native_start','checkpoint_persistent_input_hwbp')]+list(life.REUSED_UNITS)+list(life.NEW_UNITS)+['b_reload_cold_registration','b_reload_cold_registration_wait']
    units=['b_reload_cold_registration_lifecycle' if u=='b_reload_lifecycle' else u for u in units]
    asm=('checkpoint_persistent_bridge','checkpoint_persistent_authorized_bridge','checkpoint_load_worker_bridge','b_reload_title_bridge','b_reload_title520_bridge','b_reload_parent_bridge','b_reload_root_activation_bridge','b_reload_lifecycle_bridge')
    profiles={
      'b_reload_lifecycle_profile':{'InitBytes':(0x509580,0x509639),'InitCall':(0x1447B6,0x1447BB)},
      'b_reload_root_worker_profile':{'RunnerBytes':(0x834D10,0x834E75),'ThunkBytes':(0x50B730,0x50B79A),'YieldBytes':(0x50B690,0x50B6FF)},
      'b_reload_parent_profile':{'SchedulerBytes':(0x509FE0,0x50B690),'OuterCall':(0x13DC09,0x13DC0E),'PhaseCall':(0x50B41B,0x50B420),'WaitBytes':(0x834EF0,0x834EFE)},
      'b_reload_title590_profile':{'StartBytes':(0x4BEEE0,0x4BEF50)},
      'b_reload_title520_profile':{'FinalizeBytes':(0x497110,0x49713F),'ThunkBytes':(0x4FAC30,0x4FAC3C),'CallbackBytes':(0x4CC690,0x4CC7C5),'StartBytes':(0x4BEE50,0x4BEED7)}}
    sources=set();private_inputs={'game-runtime-image.bin':sha(image_file)}
    todo=[u+'.cpp' for u in units]+[u+'.asm' for u in asm]+['b_reload_cold_registration_fixture.inc','b_reload_cold_registration_test.py','b_reload_bootstrap_workers_fixture.inc','b_reload_bootstrap_workers_unwind.asm','b_reload_cold_wait.h','b_reload_cold_wait.cpp','checkpoint_task_completion_test.py','b_reload_lifecycle_test.py','b_reload_activated_queue_test.py','b_reload_root_activation_test.py','b_reload_yield_test.py','b_reload_nested_test.py','b_reload_root_worker_test.py','b_reload_bound_test.py','b_reload_queue_test.py','b_reload_parent_test.py','b_reload_title520_test.py','b_reload_title590_test.py','b_reload_title_source_test.py']
    while todo:
        n=todo.pop()
        if n in sources or n in {x+'.h' for x in profiles}:continue
        f=P/n
        if not f.is_file():
            f=private/n
            if not f.is_file():raise SystemExit('Missing '+n)
            private_inputs[n]=sha(f);continue
        sources.add(n)
        if f.suffix in ('.h','.cpp','.inc'):todo.extend(re.findall(r'^\s*#include\s+"([^"]+)"',f.read_text(encoding='utf-8-sig'),re.M))
    before={n:sha(P/n) for n in sorted(sources)}
    run=P/'b_reload_cold_registration_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True);image=image_file.read_bytes()
    for namespace,spans in profiles.items():
        body='#pragma once\nnamespace '+namespace+' {\n'
        for name,(a,b) in spans.items():body+='inline constexpr unsigned char '+name+'[]={'+','.join(hex(v) for v in image[a:b])+'};\n'
        (run/(namespace+'.h')).write_text(body+'}\n')
    flags=base.FLAGS+f' /I"{run}" /I"{P}" /I"{private}"'
    commands=[];objects=[]
    for u in units:
        obj=u+'.obj';objects.append(obj);remap='' # No fixture-only observer aliases in this EXE's objects.
        commands.append(f'cl {flags} {remap} /c /Fo"{obj}" "{P/(u+".cpp")}"')
    for u in asm:
        obj=u+'_asm.obj';objects.append(obj);commands.append(f'ml64 /nologo /c /Fo"{obj}" "{P/(u+".asm")}"')
    commands.append(f'ml64 /nologo /c /Fohost_unwind.obj "{P/"b_reload_bootstrap_workers_unwind.asm"}"')
    fixture=(P/'b_reload_bootstrap_workers_fixture.inc').read_text().split('static DWORD ownedRun()')[0]
    old='require(ResumeThread(w.thread)==1&&WaitForSingleObject(w.initial,3000)==WAIT_OBJECT_0,"constructor waits for actual initial native wait");'
    assert fixture.count(old)==1
    fixture=fixture.replace(old,'require(ResumeThread(w.thread)==1,"resume without waiting for initial wait");if(i==3)Sleep(30);')
    header='#include "b_reload_cold_registration.h"\n#include "b_reload_root_activation_bridge.h"\n#include <cstdio>\n#include <initializer_list>\n#pragma bss_seg(".fixture")\nextern "C" __declspec(dllexport) unsigned char BReloadBootstrapWorkersSpace[0x2400000];\nunsigned char BReloadBootstrapWorkersSpace[0x2400000];\n#pragma bss_seg()\n'
    (run/'fixture.cpp').write_text(header+fixture+(P/'b_reload_cold_registration_fixture.inc').read_text())
    commands += [f'cl {flags} fixture.cpp host_unwind.obj '+' '.join(objects)+' /Fe:owned_registration.exe']
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    build=run/'build.cmd';build.write_text('@echo off\nsetlocal\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    proc=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,text=True,encoding='mbcs',errors='replace');(run/'build.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
    if proc.returncode:raise SystemExit('Build failed '+str(run/'build.log'))
    rows=[]
    for case in ['delayed','deadline','source-drift','iat-drift','task-started','stop-before','stop-during','outside-owner']:
        proc=subprocess.run([str(run/'owned_registration.exe'),case],cwd=run,capture_output=True,text=True,errors='replace',timeout=20)
        (run/(case+'.stdout.txt')).write_text(proc.stdout,encoding='utf-8');(run/(case+'.stderr.txt')).write_text(proc.stderr,encoding='utf-8')
        records=[json.loads(l) for l in proc.stdout.splitlines() if l.startswith('{')]
        passed=proc.returncode==0 and len(records)==1 and records[0].get('passed') is True
        rows.append(dict(case=case,passed=passed,exit=proc.returncode,records=records));print(case,'PASS' if passed else 'FAIL',flush=True)
    unchanged=all(sha(P/n)==h for n,h in before.items()) and all(sha(private/n)==h for n,h in private_inputs.items())
    result=dict(schema='san14.b-reload-cold-registration-owned.v1',result='PASS' if unchanged and all(x['passed'] for x in rows) else 'FAIL',cases=rows,sources=before,private_inputs=private_inputs,inputs_unchanged=unchanged,binaries={n:sha(run/n) for n in ('owned_registration.exe','b_reload_cold_registration.obj','b_reload_cold_registration_wait.obj','b_reload_cold_registration_lifecycle.obj','b_reload_lifecycle_activation.obj')},generated={f.name:sha(f) for f in run.glob('*.h')},fixture_source=sha(run/'fixture.cpp'),build_script=sha(run/'build.cmd'),actual_original_register_cold_pool=True,lifecycle_callee_redirect_successor=True,activation_fixture_macros=False,bootstrap_loader_composed=False,actual_complete_queue=False,production_producer_exclusion_proved=False,game_access=False)
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(path);raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
