"""Build the local handover wrapper and exercise its ABI in an owned process."""
import ctypes as C
from datetime import datetime
import hashlib,json,os,re,subprocess
from pathlib import Path
import b_warm_coordinator_contract as wire
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    run=PRIVATE/'b_warm_coordinator_build_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    pins={}
    def pin(p):
        p=p.resolve()
        if str(p) in pins:return
        pins[str(p)]=sha(p)
        if p.suffix in ('.h','.cpp'):
            for name in re.findall(r'#include "([^"]+)"',p.read_text(encoding='utf-8')):
                if (P/name).exists():pin(P/name)
    for n in ('b_warm_coordinator_native.cpp','b_warm_coordinator_native.h','b_warm_two_bank_owner.cpp','b_warm_coordinator_contract.py','b_warm_coordinator_build.py'):pin(P/n)
    result=dict(family='san14.b-warm-coordinator.v1',result='FAIL',sources=pins,game_process_access=False,cases=[])
    try:
        lines=['#include "b_warm_coordinator_native.h"','#include <cstdio>','#include <cstddef>','int main(){puts("{");']
        for i,(name,kind) in enumerate(wire.TYPES.items()):
            cpp='b_warm_coordinator::'+name
            lines.append('printf('+json.dumps((',' if i else '')+'"'+name+'":{"size":%zu,"fields":{')+',sizeof('+cpp+'));')
            for j,(field,_) in enumerate(kind._fields_):
                label=(',' if j else '')+'"'+field+'":{"offset":%zu,"size":%zu}'
                lines.append('printf('+json.dumps(label)+',offsetof('+cpp+','+field+'),sizeof((('+cpp+'*)0)->'+field+'));')
            lines.append('printf("}}");')
        lines.append('puts("}");}')
        (run/'schema.cpp').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        command=['@echo off','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul','if errorlevel 1 exit /b 1',f'cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /I"{P}" /Fe:schema.exe schema.cpp','if errorlevel 1 exit /b 1',f'cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /LD /I"{P}" "{P / "b_warm_coordinator_native.cpp"}" "{P / "b_warm_two_bank_owner.cpp"}" /link /OUT:coordinator.dll','if errorlevel 1 exit /b 1']
        (run/'build.cmd').write_text('\n'.join(command)+'\n',encoding='utf-8')
        out=subprocess.run(['cmd','/d','/c',str(run/'build.cmd')],cwd=run,capture_output=True,timeout=120)
        (run/'build.log').write_bytes(out.stdout+out.stderr)
        assert out.returncode==0,'Native build failed'
        raw=subprocess.check_output([str(run/'schema.exe')],cwd=run,timeout=10);(run/'schema.json').write_bytes(raw);schema=json.loads(raw)
        for name,kind in wire.TYPES.items():
            assert schema[name]['size']==C.sizeof(kind),name
            for f,t in kind._fields_:assert schema[name]['fields'][f]==dict(offset=getattr(kind,f).offset,size=C.sizeof(t)),(name,f)
        result['cases'].append('all_native_structure_sizes_and_offsets')
        dll=C.WinDLL(str(run/'coordinator.dll'))
        def call(name,value):
            fn=getattr(dll,name);fn.argtypes=[C.c_void_p];fn.restype=C.c_uint32
            return fn(C.byref(value))
        d=wire.Description();assert call('DescribeBWarmCoordinator',d)==0;wire.decode(wire.Description,bytes(d));result['cases'].append('actual_description')
        nonce=bytes([23])*32
        for kind,name in ((wire.Observe,'ObserveBWarmCoordinator'),(wire.Authorize,'AuthorizeBWarmCoordinator')):
            v=wire.envelope(kind,nonce);assert call(name,v)!=0 and wire.decode(kind,bytes(v),nonce).header.result;result['cases'].append('reject_unprepared_'+kind.__name__)
        v=wire.envelope(wire.Prepare,nonce);v.pid=os.getpid();v.birth=1;v.first=1
        assert call('PrepareBWarmCoordinator',v)==3;result['cases'].append('reject_wrong_process_birth')
        v=wire.envelope(wire.Prepare,nonce);assert call('PrepareBWarmCoordinator',v)==2;result['cases'].append('failed_prepare_once_is_terminal')
        assert all(sha(n)==h for n,h in pins.items());result.update(result='PASS',inputs_unchanged=True,production_dll=dict(path=str(run/'coordinator.dll'),sha256=sha(run/'coordinator.dll')))
    except Exception as exc:result['error']=repr(exc)
    result['generated']={str(p):sha(p) for p in run.iterdir() if p.suffix in ('.cmd','.cpp') or p.name=='schema.json'}
    result['binaries']={str(p):sha(p) for p in run.iterdir() if p.suffix in ('.obj','.dll','.exe','.lib','.exp')}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(result=result['result'],path=str(run/'result.json'))));return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
