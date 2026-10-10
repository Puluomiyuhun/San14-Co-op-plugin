"""Build exact three-bank helper and test real exports against owned report DLLs."""
import ctypes as C
from datetime import datetime
import hashlib,json,re,subprocess
from pathlib import Path
import b_warm_chain_coordinator_contract as wire
from b_warm_chain_coordinator_test import exercise
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    run=PRIVATE/'b_warm_chain_coordinator_build_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    pins={}
    def pin(path):
        path=path.resolve()
        if str(path) in pins:return
        pins[str(path)]=sha(path)
        if path.suffix in ('.cpp','.h'):
            for n in re.findall(r'#include\s+"([^"]+)"',path.read_text()):
                if (P/n).is_file():pin(P/n)
    for n in ('b_warm_chain_coordinator_native.cpp','b_warm_chain_coordinator_native.h','b_warm_chain_coordinator_contract.py','b_warm_chain_coordinator_test.py','b_warm_chain_coordinator_build.py','b_warm_chain_handover.cpp','b_warm_two_bank_owner.cpp','b_warm_chain_fixture_bank.cpp'):pin(P/n)
    result=dict(family='san14.b-warm-chain-coordinator.v1',result='FAIL',sources=pins,cases=[],game_process_access=False,steam_save_access=False,native_load_executed=False,owned_report_double=True,room_ready=False)
    try:
        lines=['#include "b_warm_chain_coordinator_native.h"','#include <cstdio>','#include <cstddef>','int main(){puts("{");']
        for i,(name,kind) in enumerate(wire.TYPES.items()):
            cpp='b_warm_chain_coordinator::'+name
            lines.append('printf('+json.dumps((',' if i else '')+'"'+name+'":{"size":%zu,"fields":{')+',sizeof('+cpp+'));')
            for j,(field,_) in enumerate(kind._fields_):
                label=(',' if j else '')+'"'+field+'":{"offset":%zu,"size":%zu}'
                lines.append('printf('+json.dumps(label)+',offsetof('+cpp+','+field+'),sizeof((('+cpp+'*)0)->'+field+'));')
            lines.append('printf("}}");')
        lines.append('puts("}");}');(run/'schema.cpp').write_text('\n'.join(lines)+'\n')
        flags=f'/nologo /std:c++17 /EHa /W4 /WX /O2 /MT /I"{P}"'
        commands=['@echo off','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul','if errorlevel 1 exit /b 1',f'cl {flags} /Fe:schema.exe schema.cpp','if errorlevel 1 exit /b 1',f'cl {flags} /LD /Fe:coordinator.dll "{P/"b_warm_chain_coordinator_native.cpp"}" "{P/"b_warm_chain_handover.cpp"}" "{P/"b_warm_two_bank_owner.cpp"}" /link /INCREMENTAL:NO','if errorlevel 1 exit /b 1',f'cl {flags} /LD /Fe:bank.dll "{P/"b_warm_chain_fixture_bank.cpp"}" /link /OPT:NOICF /INCREMENTAL:NO','if errorlevel 1 exit /b 1']
        (run/'build.cmd').write_text('\n'.join(commands)+'\n')
        out=subprocess.run(['cmd','/d','/c',str(run/'build.cmd')],cwd=run,capture_output=True,timeout=120);(run/'build.log').write_bytes(out.stdout+out.stderr);assert out.returncode==0,'build failed'
        raw=subprocess.check_output([str(run/'schema.exe')],cwd=run,timeout=10);(run/'schema.json').write_bytes(raw);schema=json.loads(raw)
        for name,kind in wire.TYPES.items():
            assert schema[name]['size']==C.sizeof(kind),name
            for f,t in kind._fields_:assert schema[name]['fields'][f]==dict(offset=getattr(kind,f).offset,size=C.sizeof(t)),(name,f)
        result['cases']=['all_native_structure_sizes_and_offsets']+exercise(run)
        assert all(sha(n)==h for n,h in pins.items())
        result.update(result='PASS',inputs_unchanged=True,chain_exports_passed=True,production_dll=dict(path=str(run/'coordinator.dll'),sha256=sha(run/'coordinator.dll')))
    except Exception as exc:result['error']=repr(exc)
    result['generated']={str(p):sha(p) for p in run.iterdir() if p.suffix in ('.cmd','.cpp') or p.name=='schema.json'}
    result['binaries']={str(p):sha(p) for p in run.iterdir() if p.suffix in ('.obj','.dll','.exe','.lib','.exp')}
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],path=str(path),sha256=sha(path),error=result.get('error'))));return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
