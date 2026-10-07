from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=P/'human_rules_hook_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 flags=f'/nologo /W4 /WX /EHa /std:c++17 /O2 /MT /I"{ROOT/"outputs/san14-link"}"'
 lines=['@echo off',f'call "{vc}" >nul','if errorlevel 1 exit /b 1']
 def build(name,files,extra=''):
  args=' '.join(f'"{P/f}"' for f in files);lines.extend([f'cl {flags} {extra} {args} /Fe:"{run/name}"','if errorlevel 1 exit /b 1'])
 build('human_ai_runtime.dll',['human_ai_runtime_adapter.cpp','human_ai_runtime_subject.cpp','human_ai_group_resolver.cpp'],'/LD')
 build('human_economy_runtime.dll',['human_economy_runtime_adapter.cpp','human_ai_runtime_subject.cpp','human_ai_group_resolver.cpp'],'/LD')
 build('human_rules_hook_production.dll',['human_rules_hook_transport.cpp'],'/LD')
 build('human_rules_hook_fixture.dll',['human_rules_hook_transport.cpp'],'/LD /DHUMAN_RULES_OWN_PROCESS_FIXTURE')
 build('human_rules_hook_fixture.exe',['human_rules_hook_fixture.cpp'],'/DHUMAN_RULES_OWN_PROCESS_FIXTURE')
 cmd=run/'build.cmd';cmd.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 process=subprocess.run(['cmd','/d','/c',str(cmd)],cwd=run,capture_output=True)
 (run/'build.stdout.txt').write_bytes(process.stdout);(run/'build.stderr.txt').write_bytes(process.stderr)
 if process.returncode:raise RuntimeError(process.stdout.decode(errors='replace')+process.stderr.decode(errors='replace'))
 cases=[]
 for case in ['routes','native-seh','trampoline-seh','drain','preimage-drift','protection-drift']+[f'rollback-{i}' for i in range(6)]+['uncertain']:
  process=subprocess.run([str(run/'human_rules_hook_fixture.exe'),case,str(run/'human_ai_runtime.dll'),str(run/'human_economy_runtime.dll'),str(run/('human_rules_hook_fixture.dll' if case.startswith('rollback-') or case=='uncertain' else 'human_rules_hook_production.dll')),str(P/'game-runtime-image.bin')],cwd=run,capture_output=True,timeout=20)
  (run/f'{case}.stdout.txt').write_bytes(process.stdout);(run/f'{case}.stderr.txt').write_bytes(process.stderr)
  if process.returncode:raise RuntimeError(f'{case}: exit {process.returncode} '+process.stdout.decode(errors='replace')+process.stderr.decode(errors='replace'))
  cases.append(json.loads(process.stdout.decode().splitlines()[-1]))
 files=['human_rules_hook_transport.h','human_rules_hook_transport.cpp','human_rules_hook_unwind.h','human_rules_hook_fixture.cpp','human_rules_hook_test.py','human_ai_runtime_adapter.cpp','human_ai_runtime_adapter.h','human_ai_runtime_subject.cpp','human_ai_runtime_subject.h','human_ai_runtime_profile.h','human_ai_group_resolver.cpp','human_ai_group_resolver.h','human_ai_group_resolver_profile.h','human_economy_runtime_adapter.cpp','human_economy_runtime_adapter.h','human_economy_runtime_profile.h','human_economy_runtime_fixture_memory.h','human_economy_runtime_fixture_unwind.h','human_ai_runtime_fixture_memory.h']
 result={'result':'PASS','cases':cases,'source_sha256':{f:sha(P/f) for f in files},'archived_image_sha256':sha(P/'game-runtime-image.bin'),'archived_pdata_sha256':sha(P/'runtime-pdata.bin'),'game_access':False,'game_publication_available':False,'own_process_cooperative_gate':True,'production_dll_sha256':sha(run/'human_rules_hook_production.dll'),'fixture_dll_sha256':sha(run/'human_rules_hook_fixture.dll')}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':'PASS','path':str(run/'result.json')}))
if __name__=='__main__':main()
