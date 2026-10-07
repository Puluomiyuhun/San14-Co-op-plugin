from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=P/'human_rules_debug_publish_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 flags='/nologo /W4 /WX /EHa /std:c++17 /O2 /MT'
 commands=['@echo off',f'call "{vc}" >nul','if errorlevel 1 exit /b 1',f'ml64 /nologo /c /Fo"{run/"target.obj"}" "{P/"human_rules_debug_publish_target.asm"}"','if errorlevel 1 exit /b 1',f'cl {flags} "{P/"human_rules_debug_publish_target.cpp"}" "{run/"target.obj"}" /Fe:"{run/"target.exe"}"','if errorlevel 1 exit /b 1',f'cl {flags} "{P/"human_rules_debug_publish_controller.cpp"}" /Fe:"{run/"publisher.exe"}"','if errorlevel 1 exit /b 1']
 cmd=run/'build.cmd';cmd.write_text('\n'.join(commands)+'\n',encoding='utf-8')
 result=subprocess.run(['cmd','/d','/c',str(cmd)],cwd=run,capture_output=True)
 (run/'build.stdout.txt').write_bytes(result.stdout);(run/'build.stderr.txt').write_bytes(result.stderr)
 if result.returncode:raise RuntimeError(result.stdout.decode(errors='replace'))
 cases=[]
 for case in ['routes','rip-in-range','identity-reject','preimage-drift','protection-drift','target-exception']+[f'rollback-{i}' for i in range(6)]+['uncertain']:
  r=subprocess.run([str(run/'publisher.exe'),str(run/'target.exe'),sha(run/'target.exe'),case],cwd=run,capture_output=True,timeout=25)
  (run/f'{case}.stdout.txt').write_bytes(r.stdout);(run/f'{case}.stderr.txt').write_bytes(r.stderr)
  if r.returncode:raise RuntimeError(f'{case} exit {r.returncode}: '+r.stdout.decode(errors='replace'))
  cases.append(json.loads(r.stdout.decode().splitlines()[-1]))
 files=['human_rules_debug_publish_shared.h','human_rules_debug_publish_target.asm','human_rules_debug_publish_target.cpp','human_rules_debug_publish_controller.cpp','human_rules_debug_publish_test.py']
 report=dict(result='PASS',cases=cases,source_sha256={f:sha(P/f) for f in files},target_sha256=sha(run/'target.exe'),publisher_sha256=sha(run/'publisher.exe'),game_access=False,native_business_drain=False,arbitrary_pid_attachment=False)
 (run/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(result='PASS',path=str(run/'result.json'))))
if __name__=='__main__':main()

