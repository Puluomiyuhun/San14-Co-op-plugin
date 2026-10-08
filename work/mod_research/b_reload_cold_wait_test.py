"""Owned PE and actual archived ThreadEntry threads only; never discovers a game."""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,re,subprocess
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    private=Path(os.environ['SAN14_PRIVATE_FIXTURE_ROOT']).resolve()
    image_file=private/'game-runtime-image.bin'
    assert sha(image_file)=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
    names=['b_reload_cold_wait.h','b_reload_cold_wait.cpp','b_reload_cold_wait_test.py','b_reload_cold_wait_fixture.inc','b_reload_bootstrap_workers_fixture.inc','b_reload_bootstrap_workers_unwind.asm']
    pins={n:sha(P/n) for n in names};image=image_file.read_bytes()
    run=P/'b_reload_cold_wait_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    profiles={'b_reload_lifecycle_profile':{'InitBytes':(0x509580,0x509639),'InitCall':(0x1447B6,0x1447BB)},'b_reload_root_worker_profile':{'RunnerBytes':(0x834D10,0x834E75),'ThunkBytes':(0x50B730,0x50B79A),'YieldBytes':(0x50B690,0x50B6FF)},'checkpoint_task_native_activation_v2':{'ThreadEntryBytes':(0x83A930,0x83AA2D)}}
    for namespace,spans in profiles.items():
        filename='checkpoint_task_native_activation_v2_profile' if namespace=='checkpoint_task_native_activation_v2' else namespace
        body='#pragma once\nnamespace '+namespace+' {\n'
        for n,(a,b) in spans.items():body+='inline constexpr unsigned char '+n+'[]={'+','.join(hex(v) for v in image[a:b])+'};\n'
        (run/(filename+'.h')).write_text(body+'}\n')
    fixture=(P/'b_reload_bootstrap_workers_fixture.inc').read_text().split('static DWORD ownedRun()')[0]
    old='require(ResumeThread(w.thread)==1&&WaitForSingleObject(w.initial,3000)==WAIT_OBJECT_0,"constructor waits for actual initial native wait");'
    assert fixture.count(old)==1
    fixture=fixture.replace(old,'require(ResumeThread(w.thread)==1,"resume without constructor wait");')
    header='#include "b_reload_cold_wait.h"\n#include <cstdio>\n#include <initializer_list>\n#pragma bss_seg(".fixture")\nextern "C" __declspec(dllexport) unsigned char BReloadBootstrapWorkersSpace[0x2400000];\nunsigned char BReloadBootstrapWorkersSpace[0x2400000];\n#pragma bss_seg()\n'
    (run/'fixture.cpp').write_text(header+fixture+(P/'b_reload_cold_wait_fixture.inc').read_text())
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags=f'/nologo /W4 /WX /EHa /std:c++17 /O2 /MT /I"{run}" /I"{P}"'
    commands=[f'cl {flags} /c /Focold_wait.obj "{P/"b_reload_cold_wait.cpp"}"',f'ml64 /nologo /c /Founwind.obj "{P/"b_reload_bootstrap_workers_unwind.asm"}"',f'cl {flags} fixture.cpp cold_wait.obj unwind.obj /Fe:owned_cold_wait.exe']
    (run/'build.cmd').write_text('@echo off\nsetlocal\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    build=subprocess.run(['cmd','/c',str(run/'build.cmd')],cwd=run,capture_output=True,text=True,encoding='mbcs',errors='replace');(run/'build.log').write_text(build.stdout+build.stderr,encoding='utf-8')
    if build.returncode:raise SystemExit('Build failed '+str(run))
    rows=[]
    for case in ['delayed','deadline','source','warm','task-started','event-set','callback-refused','prior-suspended','binding','unknown-context','producer-busy','handle-changed']:
        p=subprocess.run([str(run/'owned_cold_wait.exe'),case],cwd=run,capture_output=True,text=True,errors='replace',timeout=20)
        (run/(case+'.stdout.txt')).write_text(p.stdout);(run/(case+'.stderr.txt')).write_text(p.stderr)
        records=[json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
        passed=p.returncode==0 and len(records)==1 and records[0].get('passed') is True
        rows.append(dict(case=case,passed=passed,exit=p.returncode,records=records));print(case,'PASS' if passed else 'FAIL',flush=True)
    unchanged=all(sha(P/n)==h for n,h in pins.items()) and sha(image_file)==hashlib.sha256(image).hexdigest()
    result=dict(schema='san14.b-reload-cold-wait-owned.v1',result='PASS' if unchanged and all(r['passed'] for r in rows) else 'FAIL',cases=rows,sources=pins,private_inputs={'game-runtime-image.bin':hashlib.sha256(image).hexdigest()},inputs_unchanged=unchanged,binaries={n:sha(run/n) for n in ['owned_cold_wait.exe','cold_wait.obj','unwind.obj']},generated={n:sha(run/n) for n in ['fixture.cpp','b_reload_lifecycle_profile.h','b_reload_root_worker_profile.h','checkpoint_task_native_activation_v2_profile.h','build.cmd']},production_component_fixture_macros=False,actual_archived_thread_entry=True,actual_os_suspend_context_unwind=True,registered_with_old_runtime=False,production_producer_exclusion_proved=False,game_access=False)
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run/'result.json');raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
