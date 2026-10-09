"""Compile the owned layout helper and test bounded offline decoding only."""
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import a_save_parent_failure_read as r


def main():
    out=r.PRIVATE/'a_save_parent_failure_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    result=dict(result='FAIL',game_access=False,native_calls=0,cases=[])
    try:
        sources={}
        def pin(p):
            if p.name in sources:return
            sources[p.name]=r.digest(p)
            for name in re.findall(r'^\s*#\s*include\s*"([^"\n]+)"',p.read_text(encoding='utf-8'),re.M):
                q=r.P/name
                if q.is_file():pin(q)
        for name in ('a_save_parent_failure_layout.cpp','a_save_parent_failure_read.py','a_save_parent_failure_test.py'):
            pin(r.P/name)
        result['sources']=sources
        script='@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\nif errorlevel 1 exit /b 1\n'
        script+='cl /nologo /std:c++17 /W4 /WX /EHsc /MT /I"'+str(r.P)+'" "'+str(r.P/'a_save_parent_failure_layout.cpp')+'" /Fe:layout.exe\n'
        (out/'build.cmd').write_text(script,encoding='utf-8')
        child=subprocess.run(['cmd','/d','/c',str(out/'build.cmd')],cwd=out,capture_output=True,timeout=60)
        (out/'build.log').write_bytes(child.stdout+child.stderr)
        if child.returncode:raise RuntimeError('Owned layout build failed')
        child=subprocess.run([str(out/'layout.exe')],cwd=out,capture_output=True,timeout=5)
        (out/'layout.json').write_bytes(child.stdout)
        assert child.returncode==0 and r.digest(out/'layout.json')==r.LAYOUT_SHA
        result['cases'].append(dict(case='same_msvc_native_layout',passed=True))
        schema=r.layout();base=schema['Runtime']['controller_']['offset']+schema['Controller']['r_']['offset']
        for code,initialized,label in ((1,0,'CONTROLLER_INITIALIZE_READ_OR_CLEAN_OR_CLAIM_REJECTED'),
            (3,0,'CONTROLLER_INITIALIZE_DATE_READ_EXCEPTION_AFTER_CLAIM'),
            (0,1,'CONTROLLER_REQUEST_OR_LATER_INITIALIZATION_REJECTED')):
            raw=bytearray(schema['Runtime']['_size']);raw[base]=code;raw[base+32]=initialized
            assert r.decode_runtime(raw,schema)['localization']==label
            result['cases'].append(dict(case=label,passed=True))
        try:r.decode_runtime(bytes(18231),schema)
        except RuntimeError:result['cases'].append(dict(case='truncated_runtime_rejected',passed=True))
        else:raise AssertionError('Truncated Runtime accepted')
        result['artifacts']={p.name:r.digest(p) for p in out.iterdir() if p.is_file()}
        result['sources_unchanged']=all(r.digest(r.P/n)==h for n,h in sources.items())
        assert result['sources_unchanged'] and len(result['cases'])==5
        result['result']='PASS'
    except Exception as error:result['error']=repr(error)
    path=out/'result.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=result['result'],path=str(path),sha256=r.digest(path))))
    return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
