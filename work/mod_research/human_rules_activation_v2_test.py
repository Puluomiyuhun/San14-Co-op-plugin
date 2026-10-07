from pathlib import Path
from datetime import datetime
import subprocess,json,hashlib,shutil,re
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=P/'human_rules_activation_v2_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 src=run/'src';src.mkdir();captured={}
 def copy(path):
  path=path.resolve();relative=path.relative_to(ROOT)
  if str(relative) in captured:return
  out=src/relative;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,out);captured[str(relative)]=sha(out)
  for name in re.findall(r'^\s*#include\s+"([^"]+)"',path.read_text(encoding='utf-8-sig'),re.M):
   options=[path.parent/name,P/name,ROOT/'outputs/san14-link'/name];found=next((x for x in options if x.is_file()),None)
   if found is None:raise FileNotFoundError(name)
   copy(found)
 files=['human_rules_activation_v2.cpp','human_rules_activation_v2.h','human_rules_activation_v2.asm','human_rules_activation_v2_fixture.cpp','human_rules_activation_v2_test.py','human_rules_hook_transport.cpp','human_ai_runtime_adapter.cpp','human_economy_runtime_adapter.cpp','human_ai_runtime_subject.cpp','human_ai_group_resolver.cpp']
 for f in files:copy(P/f)
 sp=src/'work/mod_research'
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 flags='/nologo /W4 /WX /EHa /std:c++17 /O2 /MT /I"'+str(src/'outputs/san14-link')+'"'
 commands=['@echo off',f'call "{vc}" >nul','if errorlevel 1 exit /b 1',f'ml64 /nologo /c /Fo"{run/"policy.obj"}" "{sp/"human_rules_activation_v2.asm"}"','if errorlevel 1 exit /b 1']
 code=['human_rules_activation_v2.cpp','human_rules_hook_transport.cpp','human_ai_runtime_adapter.cpp','human_economy_runtime_adapter.cpp','human_ai_runtime_subject.cpp','human_ai_group_resolver.cpp']
 for fixture in [False,True]:
  output='fixture.dll'if fixture else'production.dll'
  commands.extend(['cl '+flags+' /LD '+('/DHUMAN_RULES_ACTIVATION_FIXTURE 'if fixture else'')+' '.join('"'+str(sp/f)+'"'for f in code)+' "'+str(run/'policy.obj')+'" /link /EXPORT:HumanRulesActivationIncome /OUT:"'+str(run/output)+'"','if errorlevel 1 exit /b 1'])
 commands.extend(['cl '+flags+' "'+str(sp/'human_rules_activation_v2_fixture.cpp')+'" /Fe:"'+str(run/'fixture.exe')+'"','if errorlevel 1 exit /b 1'])
 cmd=run/'build.cmd';cmd.write_text('\n'.join(commands)+'\n',encoding='utf-8');r=subprocess.run(['cmd','/d','/c',str(cmd)],cwd=run,capture_output=True);(run/'build.txt').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stdout.decode(errors='replace'))
 cases=[]
 for case in ['routes','zhanglu-idle2','liubei-idle1','native-seh','world-fatal','settings-fatal','revoked-fatal','wrong-settings','wrong-main','wrong-epoch','changed-planning','prepublished','late-toolbar','late-panel','late-selection','transient-dispatch','seal-fault-race','production-image-reject']:
  r=subprocess.run([str(run/'fixture.exe'),case,str(run/('production.dll'if case=='production-image-reject'else'fixture.dll')),str(P/'game-runtime-image.bin')],cwd=run,capture_output=True,timeout=20)
  (run/f'{case}.stdout.txt').write_bytes(r.stdout);(run/f'{case}.stderr.txt').write_bytes(r.stderr)
  if r.returncode:raise RuntimeError(f'{case} exit{r.returncode}: '+r.stdout.decode(errors='replace')+r.stderr.decode(errors='replace'))
  cases.append(json.loads(r.stdout.decode().splitlines()[-1]))
 report=dict(result='PASS',cases=cases,source_sha256=captured,binary_sha256={name:sha(run/name)for name in ['production.dll','fixture.dll','fixture.exe']},game_access=False,production_seal_export_available=True,global_safe_pause=False,room_native_loader_connected=False,actual_native_profile_publication_in_owned_memory=True)
 (run/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(result='PASS',path=str(run/'result.json'))))
if __name__=='__main__':main()
