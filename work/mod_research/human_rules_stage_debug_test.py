"""Combine already-built owned target/stage/image with real OS debug publisher.

This never discovers, opens, attaches to or injects an existing game process.
The named target is a separately built fixture child, created by the publisher.
"""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import subprocess

P=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('artifacts',type=Path)
 args=parser.parse_args()
 artifacts=args.artifacts.resolve()
 files=[artifacts/'stage_debug_target.exe',artifacts/'stage_fixture.dll',artifacts/'owned_rules_image.dll',P/'game-runtime-image.bin']
 for path in files:
  if not path.is_file():raise FileNotFoundError(path)
 run=P/'human_rules_stage_debug_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 run.mkdir(parents=True)
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 cmd=run/'build.cmd'
 cmd.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT "'+str(P/'human_rules_stage_debug_publisher.cpp')+'" /Fe:"'+str(run/'publisher.exe')+'"\n',encoding='utf-8')
 result=subprocess.run(['cmd','/d','/c',str(cmd)],cwd=run,capture_output=True)
 (run/'build.stdout.txt').write_bytes(result.stdout)
 (run/'build.stderr.txt').write_bytes(result.stderr)
 if result.returncode:raise RuntimeError(result.stdout.decode(errors='replace'))
 command=[str(run/'publisher.exe')]
 for path in files:command.extend([str(path),sha(path)])
 cases=[]
 for case in ['success','native-seh']:
  result=subprocess.run(command+[case],cwd=run,capture_output=True,timeout=30)
  (run/f'{case}.stdout.txt').write_bytes(result.stdout)
  (run/f'{case}.stderr.txt').write_bytes(result.stderr)
  if result.returncode:raise RuntimeError(f'{case}: {result.returncode}: '+result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
  cases.append(json.loads(result.stdout.decode().splitlines()[-1]))
 sources=['human_rules_stage_debug_publisher.cpp','human_rules_stage_debug_test.py','human_rules_stage_debug_target.cpp','human_rules_stage_debug_target.asm','human_rules_passthrough_stage.h','human_rules_passthrough_stage.cpp','human_rules_hook_transport.cpp','human_rules_hook_unwind.h','human_ai_runtime_profile.h','human_economy_runtime_profile.h']
 report=dict(result='PASS',cases=cases,source_sha256={name:sha(P/name) for name in sources},binary_sha256={str(path):sha(path) for path in files+[run/'publisher.exe']},game_access=False,production_attach=False,policy_enabled=False,stage_dynamic_unwind_registration_evidence='Prepared from hash-bound stage using reviewed frozen Prepare; remote byte/xdata checks do not independently enumerate dynamic Windows function tables.')
 (run/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(result='PASS',path=str(run/'result.json'))))
if __name__=='__main__':main()
