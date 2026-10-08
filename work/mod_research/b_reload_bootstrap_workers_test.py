"""Only freshly built own EXE/DLL; no discovery, existing process or game use."""
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
    units=[u for u in base.UNITS if u not in ('checkpoint_task_completion_fixture','checkpoint_task_completion_ports','checkpoint_native_task_provider','checkpoint_task_native_start','checkpoint_persistent_input_hwbp')]+list(life.REUSED_UNITS)+list(life.NEW_UNITS)+['b_reload_bootstrap','b_reload_bootstrap_workers']
    asm=('checkpoint_persistent_bridge','checkpoint_persistent_authorized_bridge','checkpoint_load_worker_bridge','b_reload_title_bridge','b_reload_title520_bridge','b_reload_parent_bridge','b_reload_root_activation_bridge','b_reload_lifecycle_bridge')
    profiles={
      'b_reload_lifecycle_profile':{'InitBytes':(0x509580,0x509639),'InitCall':(0x1447B6,0x1447BB)},
      'b_reload_root_worker_profile':{'RunnerBytes':(0x834D10,0x834E75),'ThunkBytes':(0x50B730,0x50B79A),'YieldBytes':(0x50B690,0x50B6FF)},
      'b_reload_parent_profile':{'SchedulerBytes':(0x509FE0,0x50B690),'OuterCall':(0x13DC09,0x13DC0E),'PhaseCall':(0x50B41B,0x50B420),'WaitBytes':(0x834EF0,0x834EFE)},
      'b_reload_title590_profile':{'StartBytes':(0x4BEEE0,0x4BEF50)},
      'b_reload_title520_profile':{'FinalizeBytes':(0x497110,0x49713F),'ThunkBytes':(0x4FAC30,0x4FAC3C),'CallbackBytes':(0x4CC690,0x4CC7C5),'StartBytes':(0x4BEE50,0x4BEED7)}}
    sources=set();private_inputs={'game-runtime-image.bin':sha(image_file)}
    todo=[u+'.cpp' for u in units]+[u+'.asm' for u in asm]+['b_reload_bootstrap_workers_export.cpp','b_reload_bootstrap_workers_fixture.cpp','b_reload_bootstrap_workers_test.py','b_reload_bootstrap_workers_unwind.asm','b_reload_lifecycle_loader.cpp','b_reload_lifecycle_test.py','b_reload_activated_queue_test.py','b_reload_root_activation_test.py','b_reload_yield_test.py','b_reload_nested_test.py','b_reload_root_worker_test.py','b_reload_bound_test.py','b_reload_queue_test.py','b_reload_parent_test.py','b_reload_title520_test.py','b_reload_title590_test.py','b_reload_title_source_test.py','checkpoint_task_completion_test.py']
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
    run=P/'b_reload_bootstrap_workers_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True);image=image_file.read_bytes()
    for namespace,spans in profiles.items():
        body='#pragma once\nnamespace '+namespace+' {\n'
        for name,(a,b) in spans.items():body+='inline constexpr unsigned char '+name+'[]={'+','.join(hex(v) for v in image[a:b])+'};\n'
        (run/(namespace+'.h')).write_text(body+'}\n')
    flags=base.FLAGS+f' /I"{run}" /I"{P}" /I"{private}"'
    commands=[];objects=[]
    for u in units:
        obj=u+'.obj';objects.append(obj);remap='' # No fixture-only observer aliases in the actual DLL.
        commands.append(f'cl {flags} {remap} /c /Fo"{obj}" "{P/(u+".cpp")}"')
    for u in asm:
        obj=u+'_asm.obj';objects.append(obj);commands.append(f'ml64 /nologo /c /Fo"{obj}" "{P/(u+".asm")}"')
    commands.append(f'ml64 /nologo /c /Fohost_unwind.obj "{P/"b_reload_bootstrap_workers_unwind.asm"}"')
    commands += [f'cl {flags} /c /Foproduction_export.obj "{P/"b_reload_bootstrap_workers_export.cpp"}"',f'link /nologo /DLL /OUT:production_bootstrap.dll '+ ' '.join(objects)+' production_export.obj',f'cl {flags} /DB_RELOAD_BOOTSTRAP_WORKERS_OWNED /c /Foowned_export.obj "{P/"b_reload_bootstrap_workers_export.cpp"}"',f'link /nologo /DLL /OUT:"owned workers.dll" '+' '.join(objects)+' owned_export.obj',f'cl {flags} "{P/"b_reload_bootstrap_workers_fixture.cpp"}" host_unwind.obj /Fe:"owned host.exe"',f'cl {flags} "{P/"b_reload_lifecycle_loader.cpp"}" /Fe:loader.exe']
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    build=run/'build.cmd';build.write_text('@echo off\nsetlocal\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    proc=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,text=True,encoding='mbcs',errors='replace');(run/'build.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
    if proc.returncode:raise SystemExit('Build failed '+str(run/'build.log'))
    rows=[]
    for case,production in [('bootstrap-four-workers-ordinary',False),('production-source-unready',True)]:
        proc=subprocess.run([str(run/'loader.exe'),str(run/'owned host.exe'),str(run/('production_bootstrap.dll' if production else 'owned workers.dll')),'--wait-exit'],cwd=run,capture_output=True,text=True,errors='replace',timeout=40)
        (run/(case+'.stdout.txt')).write_text(proc.stdout);(run/(case+'.stderr.txt')).write_text(proc.stderr)
        records=[json.loads(l) for l in proc.stdout.splitlines() if l.startswith('{')];last=records[-1] if records else {}
        bs=[r for r in records if r.get('actual_bootstrap')];ws=[r for r in records if r.get('workers_composed')]
        if production:
            passed=proc.returncode==1 and last.get('stage')=='bootstrap' and len(bs)==1 and not bs[0].get('ok') and not any(r.get('owned_main_started') for r in records)
        else:
            passed=proc.returncode==0 and last.get('passed') is True and len(bs)==len(ws)==1 and bs[0].get('ok') is True and bs[0].get('workers')==0 and bs[0].get('attempts')==1 and ws[0].get('passed') is True and ws[0].get('cold_workers')==4 and ws[0].get('outer_finally')==4 and ws[0].get('unowned_tasks')==1 and ws[0].get('ordinary_bodies')==1
        rows.append(dict(case=case,passed=bool(passed),exit=proc.returncode,records=records));print(case,'PASS' if passed else 'FAIL',flush=True)
    unchanged=all(sha(P/n)==h for n,h in before.items()) and all(sha(private/n)==h for n,h in private_inputs.items())
    result=dict(schema='san14.b-reload-bootstrap-workers-owned.v1',result='PASS' if unchanged and all(x['passed'] for x in rows) else 'FAIL',cases=rows,sources=before,private_inputs=private_inputs,inputs_unchanged=unchanged,binaries={n:sha(run/n) for n in ('loader.exe','owned host.exe','production_bootstrap.dll','owned workers.dll','b_reload_bootstrap.obj','b_reload_bootstrap_workers.obj')},lifecycle_source_prepared_and_armed=True,actual_production_modules_no_fixture_macros=True,artificial_owned_MEM_IMAGE=True,actual_four_workers_started=True,actual_complete_queue=False,game_access=False,steam_access=False,game_launch_verified=False,production_source_readiness_proved=False,full_world=False,room_ready=False,native_simulation_permit=False)
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(path);raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
