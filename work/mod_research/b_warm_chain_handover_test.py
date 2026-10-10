"""Actual native chain + predecessor checks; owned DLL reports, no game access."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,shutil
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
VC=Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'b_warm_chain_handover_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(result='FAIL',game_process_access=False,steam_save_access=False,native_load_executed=False,
        owned_report_double=True,python_loader_rewired=False,sources={})
    try:
        # Resolve local quoted headers transitively; no archived game bytes used.
        todo=[P/n for n in ('b_warm_chain_handover.h','b_warm_chain_handover.cpp','b_warm_chain_fixture.cpp',
            'b_warm_chain_fixture_bank.cpp','b_warm_two_bank_owner.cpp','b_warm_chain_handover_test.py')]
        import re
        while todo:
            f=todo.pop()
            if str(f) in result['sources']:continue
            result['sources'][str(f)]=sha(f)
            todo += [P/n for n in re.findall(r'#include\s+"([^"]+)"',f.read_text()) if (P/n).is_file()]
        flags=f'/nologo /std:c++17 /EHsc /W4 /WX /O2 /MT /I"{P}"'
        commands=['@echo off',f'call "{VC}" >nul','if errorlevel 1 exit /b 1',f'cd /d "{run}"',
            f'cl {flags} /LD /Fe:bank.dll "{P/"b_warm_chain_fixture_bank.cpp"}" /link /OPT:NOICF /INCREMENTAL:NO','if errorlevel 1 exit /b 1',
            f'cl {flags} /Fe:fixture.exe "{P/"b_warm_chain_fixture.cpp"}" "{P/"b_warm_chain_handover.cpp"}" "{P/"b_warm_two_bank_owner.cpp"}" /link /INCREMENTAL:NO','if errorlevel 1 exit /b 1']
        (run/'build.cmd').write_text('\n'.join(commands)+'\n')
        p=subprocess.run(['cmd','/d','/c',str(run/'build.cmd')],cwd=run,capture_output=True,timeout=90)
        (run/'build.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,('build',p.returncode)
        for i in range(3):shutil.copyfile(run/'bank.dll',run/f'bank{i}.dll')
        p=subprocess.run([str(run/'fixture.exe'),*[str(run/f'bank{i}.dll') for i in range(3)]],cwd=run,capture_output=True,timeout=15)
        (run/'execution.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,('fixture',p.returncode)
        result['native_result']=json.loads(p.stdout.decode());assert result['native_result']['passed']
        assert all(sha(Path(n))==h for n,h in result['sources'].items());result['result']='PASS'
    except Exception as exc:result['error']=repr(exc)
    result['artifacts']={str(p.relative_to(run)):sha(p) for p in run.rglob('*') if p.is_file()}
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],path=str(path))))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
