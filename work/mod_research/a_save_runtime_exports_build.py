"""Build the real exported Runtime DLL and its owned ABI/schema executable."""
from pathlib import Path
from datetime import datetime
import json,hashlib,os,re,subprocess,sys,difflib
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def schema_cpp():
    h=re.sub(r'//[^\n]*','',(P/'a_save_runtime_exports.h').read_text())
    lines=['#include "a_save_runtime_exports.h"','#include <cstdio>','#include <cstddef>','using namespace a_save_runtime_wire;','int main(){puts("{\\\"structures\\\":{");']
    structs=re.findall(r'struct\s+(\w+)\s*\{(.*?)\};',h,re.S)
    for si,(name,body) in enumerate(structs):
        lines.append('printf("'+('' if not si else ',')+'\\\"'+name+'\\\":{\\\"size\\\":%zu,\\\"fields\\\":{",sizeof('+name+'));')
        fi=0
        for decl in body.split(';'):
            decl=decl.strip()
            if not decl:continue
            match=re.fullmatch(r'(unsigned char|std::\w+|wchar_t|\w+)\s+(.+)',decl,re.S)
            if not match:raise ValueError(decl)
            typ,tail=match.groups()
            for field in tail.split(','):
                m=re.fullmatch(r'(\w+)(?:\[(\w+)\])?',field.strip());field,count=m.groups();count=int(count or '1',0)
                lines.append('printf("'+('' if not fi else ',')+'\\\"'+field+'\\\":{\\\"offset\\\":%zu,\\\"size\\\":%zu,\\\"count\\\":'+str(count)+',\\\"type\\\":\\\"'+typ+'\\\"}",offsetof('+name+','+field+'),sizeof((('+name+'*)0)->'+field+'));');fi+=1
        lines.append('printf("}}");')
    lines+=['puts("}}");return 0;}']
    return '\n'.join(lines).replace('\\\"','\\"')+'\n'
def main():
    run=PRIVATE/'a_save_runtime_exports_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    own_before={p.name:sha(p) for p in P.glob('a_save_runtime_exports*') if p.suffix in ('.cpp','.h','.py')}
    old=(P/'a_save_local_runtime_build.py').read_text();s=old.replace('P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/\'mod_research\'', 'P=Path('+repr(str(P))+');PRIVATE=Path('+repr(str(PRIVATE))+')')
    s=s.replace("run=PRIVATE/'a_save_local_runtime_build_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)", 'run=Path('+repr(str(run/'production'))+');run.mkdir(parents=True)')
    s=s.replace("runtime='a_save_local_runtime.cpp',", "runtime='a_save_local_runtime.cpp', exports='a_save_runtime_exports.cpp',")
    s=s.replace("parent='a_save_parent_adapter.cpp'","parent='a_save_runtime_publish_parent.cpp'").replace("parent_bridge='b_reload_parent_bridge.cpp'","parent_bridge='a_save_runtime_publish_parent_bridge.cpp'")
    s=s.replace(" start=s.index('    asm = dict(')"," s=s.replace(\"input_bridge='a_save_action_gate_bridge.cpp'\",\"input_bridge='a_save_runtime_publish_gate.cpp'\").replace(\"bridge='a_reward_save_owner_bridge.cpp'\",\"bridge='a_save_runtime_publish_user.cpp'\")\n start=s.index('    asm = dict(')")
    s=s.replace('runtime.obj sampler.obj','runtime.obj exports.obj sampler.obj')
    s=s.replace("'a_save_local_runtime_build.py'", "'a_save_runtime_exports_build.py'")
    # The production Runtime remains unchanged; only the composition gains ABI.
    script=run/'production_build.py';script.write_text(s);(run/'builder.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))))
    result={'result':'FAIL','game_access':False,'runtime_game_execution':False}
    try:
        p=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,errors='replace',timeout=240)
        (run/'production-driver.log').write_text(p.stdout+p.stderr)
        info=json.loads((run/'production'/'result.json').read_text());assert p.returncode==0 and info['result']=='PASS',info
        build=run/'production'/'build';result['production']=info
        cpp=run/'schema.cpp';cpp.write_text(schema_cpp());vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
        cmd=run/'abi_build.cmd';cmd.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /EHsc /MT /I"'+str(P)+'" "'+str(cpp)+'" /Fe:schema.exe\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /EHsc /MT /I"'+str(P)+'" "'+str(P/'a_save_runtime_exports_test.cpp')+'" /Fe:abi.exe\nif errorlevel 1 exit /b 1\ndumpbin /imports "'+str(build/'a_save_local_runtime.dll')+'" > imports.txt\nif errorlevel 1 exit /b 1\ndumpbin /exports "'+str(build/'a_save_local_runtime.dll')+'" > exports.txt\n')
        p=subprocess.run(['cmd','/c',str(cmd)],cwd=run,capture_output=True,text=True,errors='replace',timeout=90);(run/'abi-build.log').write_text(p.stdout+p.stderr);assert p.returncode==0,'ABI compile'
        p=subprocess.run([str(run/'schema.exe')],capture_output=True,text=True,timeout=10);assert p.returncode==0
        schema=json.loads(p.stdout);(run/'schema.json').write_text(json.dumps(schema,indent=2)+'\n')
        p=subprocess.run([str(run/'abi.exe'),str(build/'a_save_local_runtime.dll')],cwd=build,capture_output=True,text=True,timeout=30);(run/'abi.log').write_text(p.stdout+p.stderr);assert p.returncode==0,'ABI checks'
        result['result']='PASS';result['abi_executed']=True;result['schema']=str(run/'schema.json');result['dll']=str(build/'a_save_local_runtime.dll')
        assert all(sha(P/n)==h for n,h in info['sources'].items())
        assert all(sha(P/n)==h for n,h in own_before.items()),'ABI/build source changed during run'
    except Exception as e:
        result['result']='FAIL';result['error']=repr(e);(run/'failure.log').write_text(repr(e)+'\n'+str(getattr(e,'stdout',''))+'\n'+str(getattr(e,'stderr','')))
    result['own_sources']=own_before
    result['generated']={p.name:sha(p) for p in run.iterdir() if p.is_file() and p.suffix in ('.cpp','.cmd','.exe','.obj','.py','.json')}
    out=run/'result.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(out)}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
