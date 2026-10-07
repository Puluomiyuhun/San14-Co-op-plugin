from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,re
P=Path(__file__).resolve().parent
ROOT=P.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=P/'human_economy_runtime_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 profile=(P/'human_economy_runtime_profile.h').read_text(encoding='utf-8');image=(P/'game-runtime-image.bin').read_bytes()
 arrays={name:bytes(map(int,data.split(','))) for name,data in re.findall(r'Bytes(\w+)\[\]=\{([\d,]+)\}',profile)}
 for rva,name in re.findall(r'\{(0x[0-9a-f]+),Bytes(\w+),sizeof Bytes\w+\}',profile):
  a=int(rva,16);assert image[a:a+len(arrays[name])]==arrays[name]
 for a in [0x28de71,0x28daa5]:
  assert image[a]==0xe8 and a+5+int.from_bytes(image[a+1:a+5],'little',signed=True)==0x2110b0
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 sources=['human_economy_runtime_adapter.cpp','human_ai_runtime_subject.cpp','human_ai_group_resolver.cpp']
 flags=f'/nologo /W4 /WX /EHa /std:c++17 /O2 /MT /I"{ROOT/"outputs/san14-link"}"'
 common=' '.join(f'"{P/s}"' for s in sources)
 build=run/'build.cmd'
 build.write_text(f'@echo off\ncall "{vc}" >nul\nif errorlevel 1 exit /b 1\ncl {flags} /LD {common} /Fe:"{run/"human_economy_runtime.dll"}"\nif errorlevel 1 exit /b 1\ncl {flags} {common} "{P/"human_economy_runtime_fixture.cpp"}" /Fe:"{run/"human_economy_runtime_fixture.exe"}"\n',encoding='utf-8')
 proc=subprocess.run(['cmd','/d','/c',str(build)],cwd=run,capture_output=True)
 (run/'build.stdout.txt').write_bytes(proc.stdout);(run/'build.stderr.txt').write_bytes(proc.stderr)
 if proc.returncode:raise RuntimeError(proc.stdout.decode(errors='replace')+proc.stderr.decode(errors='replace'))
 rows=[]
 for case in ['routing','hold-repair','hold-exception','native-exception','unknown-unhealthy-binding','plan-bounds','bad-settings','bad-site']:
  proc=subprocess.run([str(run/'human_economy_runtime_fixture.exe'),case,str(run/'human_economy_runtime.dll')],cwd=run,capture_output=True,timeout=15)
  (run/f'{case}.stdout.txt').write_bytes(proc.stdout);(run/f'{case}.stderr.txt').write_bytes(proc.stderr)
  if proc.returncode:raise RuntimeError(f'{case} exit={proc.returncode}: '+proc.stdout.decode(errors='replace')+proc.stderr.decode(errors='replace'))
  rows.append(json.loads(proc.stdout.decode().splitlines()[-1]))
 files=sources+['human_economy_runtime_adapter.h','human_economy_runtime_profile.h','human_economy_runtime_fixture.cpp','human_economy_runtime_fixture_memory.h','human_economy_runtime_fixture_unwind.h','human_economy_runtime_test.py','human_ai_runtime_subject.h','human_ai_runtime_profile.h','human_ai_group_resolver.h','human_ai_group_resolver_profile.h','human_ai_runtime_fixture_memory.h']
 result={'result':'PASS','cases':rows,'source_sha256':{f:sha(P/f) for f in files},'image_sha256':sha(P/'game-runtime-image.bin'),'pdata_sha256':sha(P/'runtime-pdata.bin'),'dll_sha256':sha(run/'human_economy_runtime.dll'),'production_installer_provided':False,'safe_game_hold_proven':False,'game_access':False,'actual_return_addresses':True,'force_subject_stubs':False,'copied_native_predicate_executed_in_own_process':True}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':'PASS','result_path':str(run/'result.json')}))
if __name__=='__main__':main()
