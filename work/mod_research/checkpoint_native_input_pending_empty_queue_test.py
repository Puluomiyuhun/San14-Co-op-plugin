"""Reproduce the real A binding rejection, then test the same-ABI successor. No game access."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'checkpoint_native_input_pending_empty_queue_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    names=('checkpoint_native_input_pending_empty_queue.cpp','checkpoint_native_input_pending_empty_queue_fixture.cpp','checkpoint_native_input_pending_empty_queue_test.py','checkpoint_native_input_pending_adapter.cpp','checkpoint_native_input_pending_adapter.h','checkpoint_native_input_core.h','checkpoint_load_dispatch_bridge.h','checkpoint_push_bridge.h')
    pins={n:sha(P/n) for n in names}
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    commands=[]
    for name,unit in (('baseline','checkpoint_native_input_pending_adapter.cpp'),('successor','checkpoint_native_input_pending_empty_queue.cpp')):
        commands.append(f'cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT /I"{P}" "{P/unit}" "{P/names[1]}" /Fe:{name}.exe /link /INCREMENTAL:NO')
    build=run/'build.cmd';build.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    result={'result':'FAIL','sources':pins,'game_access':False};rows=[]
    try:
        r=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,text=True,errors='replace',timeout=90)
        (run/'build.log').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,'compile failed'
        for name in ('baseline','successor'):
            r=subprocess.run([str(run/(name+'.exe'))]+(['baseline'] if name=='baseline' else []),cwd=run,capture_output=True,text=True,errors='replace',timeout=10)
            (run/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,(name,r.stdout,r.stderr)
            rows.append({'case':name,'result':json.loads(r.stdout),'sha256':sha(run/(name+'.exe'))})
        assert all(sha(P/n)==h for n,h in pins.items()),'source drift'
        result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    result['cases']=rows;(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'result':result['result'],'path':str(run/'result.json')}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
