"""Owned live-layout sampler/inspector composition. Never finds or opens the game."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,subprocess
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'a_save_local_binding_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    pending=['a_save_local_binding.cpp','a_save_local_binding_fixture.cpp','a_save_local_binding_test.py','checkpoint_native_input_pending_empty_queue.cpp'];sources={}
    while pending:
        n=pending.pop()
        if n in sources:continue
        sources[n]=sha(P/n);pending.extend(re.findall(r'^\s*#include\s+"([^"]+)"',(P/n).read_text(),re.M))
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    command=f'cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT /I"{P}" "{P/"a_save_local_binding.cpp"}" "{P/"a_save_local_binding_fixture.cpp"}" "{P/"checkpoint_native_input_pending_empty_queue.cpp"}" /Fe:sampler.exe /link /INCREMENTAL:NO'
    build=run/'build.cmd';build.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+command+'\nif errorlevel 1 exit /b 1\n')
    result=dict(result='FAIL',sources=sources,game_access=False)
    try:
        r=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,text=True,errors='replace',timeout=90);(run/'build.log').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,'build failed'
        r=subprocess.run([str(run/'sampler.exe')],cwd=run,capture_output=True,text=True,errors='replace',timeout=10);(run/'run.log').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,(r.stdout,r.stderr)
        result['checks']=json.loads(r.stdout);assert all(sha(P/n)==h for n,h in sources.items()),'source drift'
        result.update(result='PASS',sources_unchanged=True,binaries={p.name:sha(p) for p in run.glob('*') if p.suffix in ('.exe','.obj')})
    except Exception as e:result['error']=repr(e)
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],path=str(run/'result.json'))));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
