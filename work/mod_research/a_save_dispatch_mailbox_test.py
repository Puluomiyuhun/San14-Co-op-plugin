"""Build/run only the owned mailbox fixture; no archive, game or discovery."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,subprocess
P=Path(__file__).resolve().parent
CASES=('two-generations','concurrent','queued-timeout','claimed-timeout','stop','unknown','artifact-mismatch')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    sources=set();todo=['a_save_dispatch_mailbox.cpp','a_save_dispatch_mailbox_fixture.cpp','a_save_dispatch_mailbox_test.py']
    while todo:
        name=todo.pop()
        if name in sources:continue
        p=P/name
        if not p.is_file():raise SystemExit('Missing '+name)
        sources.add(name)
        if p.suffix in ('.h','.cpp'):todo.extend(re.findall(r'^\s*#include "([^"]+)"',p.read_text(encoding='utf-8-sig'),re.M))
    before={n:sha(P/n) for n in sorted(sources)}
    run=P/'a_save_dispatch_mailbox_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    build=run/'build.cmd'
    build.write_text('@echo off\nsetlocal\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /W4 /WX /O2 /EHsc /std:c++17 /I"'+str(P)+'" "'+str(P/'a_save_dispatch_mailbox.cpp')+'" "'+str(P/'a_save_dispatch_mailbox_fixture.cpp')+'" /Fe:mailbox.exe\n')
    def text(value):return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value or ''
    build_error=None
    try:
        p=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,text=True,encoding='mbcs',errors='replace',timeout=120)
        build_exit=p.returncode;build_output=p.stdout+p.stderr
    except (subprocess.TimeoutExpired,OSError) as e:
        build_exit=-1;build_error=type(e).__name__;build_output=text(getattr(e,'stdout',None))+text(getattr(e,'stderr',None))+repr(e)
    (run/'build.log').write_text(build_output,encoding='utf-8')
    rows=[]
    if not build_exit:
        for case in CASES:
            try:
                r=subprocess.run([str(run/'mailbox.exe'),case],cwd=run,capture_output=True,text=True,timeout=15)
                output=r.stdout+r.stderr
                rows.append(dict(case=case,passed=r.returncode==0 and '"passed":true' in r.stdout,exit=r.returncode))
            except (subprocess.TimeoutExpired,OSError) as e:
                output=text(getattr(e,'stdout',None))+text(getattr(e,'stderr',None))+repr(e)
                rows.append(dict(case=case,passed=False,exit=-1,error=type(e).__name__))
            (run/(case+'.log')).write_text(output,encoding='utf-8')
    same=all(sha(P/n)==v for n,v in before.items())
    passed=not build_exit and same and len(rows)==len(CASES) and all(r['passed'] for r in rows)
    result=dict(result='PASS' if passed else 'FAIL',build_exit=build_exit,build_error=build_error,cases=rows,sources=before,sources_unchanged=same,binary_sha256=sha(run/'mailbox.exe') if (run/'mailbox.exe').is_file() else None,native_save=False,root_boundary_proven=False,permit=False,serializer=False,existing_ipc_server_unmodified=True,held_ipc_config_ports_executed=passed,pipe_server_executed=False,game_access=False)
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'result':result['result'],'cases':len(rows),'path':str(run/'result.json')}))
    raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
