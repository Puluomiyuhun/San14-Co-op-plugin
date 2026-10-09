"""Compile the real refresh owner TU and compare its ABI; no game access."""
import ctypes as C
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import b_warm_refresh_contract as abi

HERE=Path(__file__).resolve().parent
PRIVATE=HERE.parents[2]/'mod_research'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    folder=PRIVATE/'b_warm_refresh_abi_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    sources={}
    def pin(p):
        p=Path(p).resolve()
        if str(p) in sources:return
        sources[str(p)]=sha(p)
        if p.suffix in ('.h','.cpp'):
            for name in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):pin(p.parent/name)
    for name in ('b_warm_refresh_owner.cpp','b_warm_refresh_abi.cpp','b_warm_refresh_abi_test.py','b_warm_refresh_contract.py','b_warm_profile_contract.py','checkpoint_complete_live_owner_contract.py'):pin(HERE/name)
    cmd=folder/'build.cmd'
    cmd.write_text('@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\nif errorlevel 1 exit /b 1\npushd "%~dp0"\n'
        +f'cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:owner.obj "{HERE / "b_warm_refresh_owner.cpp"}"\nif errorlevel 1 exit /b 1\n'
        +f'cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /Fo:abi.obj /Fe:abi.exe "{HERE / "b_warm_refresh_abi.cpp"}"\nexit /b %errorlevel%\n')
    result=dict(result='FAIL',game_access=False,native_io_executed=False,sources=sources)
    try:
        build=subprocess.run(['cmd','/c',str(cmd)],capture_output=True,text=True,errors='replace',timeout=90)
        (folder/'build.log').write_text(build.stdout+build.stderr)
        if build.returncode:raise RuntimeError('Production compile failed; see build.log')
        run=subprocess.run([str(folder/'abi.exe')],capture_output=True,text=True,errors='replace',timeout=10)
        (folder/'abi.log').write_text(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError('ABI program failed')
        actual=json.loads(run.stdout)
        for name in ('Config','Report','Description','Identity'):assert actual[name]==C.sizeof(getattr(abi,name)),name
        for name,value in actual['offsets'].items():assert value==getattr(abi.Config,name).offset,name
        for name,value in actual['report_offsets'].items():assert value==getattr(abi.Report,name).offset,name
        result['abi']=actual
        result['sources_unchanged']=all(sha(p)==h for p,h in sources.items())
        assert result['sources_unchanged']
        result['result']='PASS'
    except BaseException as exc:result['error']=repr(exc)
    result['generated']={str(cmd):sha(cmd)}
    result['artifacts']={str(p):sha(p) for p in folder.iterdir() if p.suffix in ('.obj','.exe','.log')}
    path=folder/'result.json';path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(result=result['result'],path=str(path),sha256=sha(path))))
    return 0 if result['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
