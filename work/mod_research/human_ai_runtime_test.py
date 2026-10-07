"""Build callable DLL and independent fixture. No game/process/network access."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import subprocess
import re
import sys
P=Path(__file__).resolve().parent
ROOT=P.parent.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 run=P/'human_ai_runtime_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 sys.path.insert(0,str(P/'python_deps'));import capstone
 image=(P/'game-runtime-image.bin').read_bytes()
 profile=(P/'human_ai_runtime_profile.h').read_text(encoding='utf-8')
 arrays={name:bytes(map(int,data.split(','))) for name,data in re.findall(r'Bytes(\w+)\[\]=\{([\d,]+)\}',profile)}
 anchors=re.findall(r'\{(0x[0-9a-f]+),Bytes(\w+),sizeof Bytes\w+\}',profile)
 for rva,name in anchors:
  a=int(rva,16);assert image[a:a+len(arrays[name])]==arrays[name]
 assert len(anchors)==12
 md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
 prefixes=[]
 for rva,size in [(0xc6660,16),(0xc65f0,15),(0xc6580,15),(0xc66a0,15)]:
  ins=list(md.disasm(image[rva:rva+size],rva));assert sum(i.size for i in ins)==size
  assert all(not i.mnemonic.startswith(('call','j','ret')) for i in ins)
  assert all(not (op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP) for i in ins for op in i.operands)
  prefixes.append({'rva':hex(rva),'instruction_boundary_bytes':size,'instructions':[f'{i.mnemonic} {i.op_str}' for i in ins],'relocated':False,'unwind_registered':False,'published':False})
 sources=['human_ai_runtime_subject.cpp','human_ai_runtime_adapter.cpp','human_ai_group_resolver.cpp']
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 flags=f'/nologo /W4 /WX /EHa /std:c++17 /O2 /MT /I"{ROOT/"outputs/san14-link"}"'
 common=' '.join(f'"{P/s}"' for s in sources)
 build=run/'build.cmd'
 build.write_text(f'@echo off\ncall "{vc}" >nul\nif errorlevel 1 exit /b 1\ncl {flags} /LD {common} /Fe:"{run/"human_ai_runtime.dll"}"\nif errorlevel 1 exit /b 1\ncl {flags} {common} "{P/"human_ai_runtime_fixture.cpp"}" /Fe:"{run/"human_ai_runtime_fixture.exe"}"\n',encoding='utf-8')
 p=subprocess.run(['cmd','/d','/c',str(build)],cwd=run,capture_output=True)
 (run/'build.stdout.txt').write_bytes(p.stdout);(run/'build.stderr.txt').write_bytes(p.stderr)
 if p.returncode:raise RuntimeError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 rows=[]
 for case in ['routes','nested','native-exception','binding-repair','army-repair','hold-exception','blocking-hold','main-order-change','bad-binding','bad-original','profile']:
  p=subprocess.run([str(run/'human_ai_runtime_fixture.exe'),case,str(run/'human_ai_runtime.dll')],cwd=run,capture_output=True,timeout=15)
  (run/f'{case}.stdout.txt').write_bytes(p.stdout);(run/f'{case}.stderr.txt').write_bytes(p.stderr)
  if p.returncode:raise RuntimeError(case+': '+p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
  rows.append(json.loads(p.stdout))
 files=sources+['human_ai_runtime_subject.h','human_ai_runtime_adapter.h','human_ai_runtime_profile.h','human_ai_runtime_fixture_memory.h','human_ai_runtime_fixture.cpp','human_ai_runtime_test.py','human_ai_group_resolver.h','human_ai_group_resolver_profile.h']
 result={'result':'PASS','cases':rows,'profile_anchors_checked':12,'entry_prefix_review':prefixes,'source_sha256':{f:sha(P/f) for f in files},'image_sha256':sha(P/'game-runtime-image.bin'),'dll_sha256':sha(run/'human_ai_runtime.dll'),'production_installer_provided':False,'safe_game_hold_proven':False,'game_access':False,'subject_stubs':False}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':'PASS','result_path':str(run/'result.json')}))

if __name__=='__main__':main()
