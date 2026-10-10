"""Compile the production header and compare every used Python wire field."""
import ctypes as C
from datetime import datetime
import hashlib,json,subprocess
from pathlib import Path
import player_input_lease_port as p
HERE=Path(__file__).resolve().parent;PRIVATE=HERE.parents[2]/'mod_research'
def main():
    out=PRIVATE/'player_input_lease_abi_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    sources={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (Path(__file__),Path(p.__file__),HERE/'player_input_lease_exports.h')}
    lines=['#include "player_input_lease_exports.h"','#include <cstdio>','#include <cstddef>','int main(){'];expected={}
    for kind in (p.Header,p.Binding,p.Request,p.Lease,p.Snapshot):
        name=kind.__name__;cpp='player_input_lease_wire::'+name;expected[name]=[C.sizeof(kind)]
        lines.append(f'printf("{name} %zu\\n",sizeof({cpp}));')
        for field,typ in kind._fields_:
            lines.append(f'printf("{name}.{field} %zu %zu\\n",offsetof({cpp},{field}),sizeof((({cpp}*)0)->{field}));')
            expected[name+'.'+field]=[getattr(kind,field).offset,C.sizeof(typ)]
    lines.append('}');(out/'schema.cpp').write_text('\n'.join(lines))
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    (out/'build.cmd').write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /EHsc /MT /I"'+str(HERE)+'" schema.cpp /Fe:schema.exe\n')
    result=dict(result='FAIL',game_access=False,sources=sources)
    try:
        r=subprocess.run(['cmd','/c',str(out/'build.cmd')],cwd=out,capture_output=True,text=True);(out/'build.log').write_text(r.stdout+r.stderr);assert r.returncode==0
        r=subprocess.run([str(out/'schema.exe')],capture_output=True,text=True);assert r.returncode==0;(out/'schema.txt').write_text(r.stdout)
        actual={v.split()[0]:list(map(int,v.split()[1:])) for v in r.stdout.splitlines()};assert actual==expected
        assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in sources.items())
        result.update(result='PASS',verified_entries=len(expected))
    except BaseException as exc:result['error']=repr(exc)
    result['artifacts']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file()}
    (out/'result.json').write_text(json.dumps(result,indent=2));print(out/'result.json');return result['result']!='PASS'
if __name__=='__main__':raise SystemExit(main())
