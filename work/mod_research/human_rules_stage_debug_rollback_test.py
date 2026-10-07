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
import shutil
import re

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
 run=P/'human_rules_stage_debug_rollback_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 run.mkdir(parents=True)
 input_dir=run/'inputs';input_dir.mkdir()
 source_dir=run/'sources';source_dir.mkdir()
 originals=list(files)
 for path in originals:
  before=sha(path);shutil.copy2(path,input_dir/path.name)
  if sha(path)!=before or sha(input_dir/path.name)!=before:raise RuntimeError('input_changed_during_archive')
 files=[input_dir/path.name for path in originals]
 sources=['human_rules_stage_debug_publisher.cpp','human_rules_stage_debug_rollback_test.py','human_rules_stage_debug_target.cpp','human_rules_stage_debug_target.asm','human_rules_passthrough_stage.h','human_rules_passthrough_stage.cpp','human_rules_hook_transport.cpp','human_rules_hook_unwind.h','human_ai_runtime_profile.h','human_economy_runtime_profile.h']
 captured={}
 def capture(path):
  before=sha(path)
  if path.name in captured:
   if captured[path.name]!=before:raise RuntimeError('ambiguous_source_name')
   return
  shutil.copy2(path,source_dir/path.name)
  if sha(path)!=before or sha(source_dir/path.name)!=before:raise RuntimeError('source_changed_during_archive')
  captured[path.name]=before
  for include in re.findall(r'^\s*#include\s+"([^"]+)"',path.read_text(encoding='utf-8-sig'),re.M):
   candidates=[path.parent/include,P/include,artifacts/include,P.parent.parent/'outputs/san14-link'/include]
   found=next((candidate for candidate in candidates if candidate.is_file()),None)
   if found is None:raise FileNotFoundError(include)
   capture(found)
 for name in sources:capture(P/name)
 for path in artifacts.glob('*.cmd'):shutil.copy2(path,source_dir/('upstream-'+path.name))
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 cmd=run/'build.cmd'
 cmd.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT "'+str(source_dir/'human_rules_stage_debug_publisher.cpp')+'" /Fe:"'+str(run/'publisher.exe')+'"\n',encoding='utf-8')
 result=subprocess.run(['cmd','/d','/c',str(cmd)],cwd=run,capture_output=True)
 (run/'build.stdout.txt').write_bytes(result.stdout)
 (run/'build.stderr.txt').write_bytes(result.stderr)
 if result.returncode:raise RuntimeError(result.stdout.decode(errors='replace'))
 command=[str(run/'publisher.exe')]
 for path in files:command.extend([str(path),sha(path)])
 cases=[]
 for case in ['success','native-seh']+[f'rollback-{i}' for i in range(6)]:
  result=subprocess.run(command+[case],cwd=run,capture_output=True,timeout=30)
  (run/f'{case}.stdout.txt').write_bytes(result.stdout)
  (run/f'{case}.stderr.txt').write_bytes(result.stderr)
  if result.returncode:raise RuntimeError(f'{case}: {result.returncode}: '+result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
  cases.append(json.loads(result.stdout.decode().splitlines()[-1]))
 report=dict(result='PASS',cases=cases,source_sha256=captured,archived_sources=str(source_dir),binary_sha256={str(path):sha(path) for path in files+[run/'publisher.exe']},upstream_artifacts=str(artifacts),historical_two_case_target_superseded=True,game_access=False,production_attach=False,policy_enabled=False,stage_dynamic_unwind_registration_evidence='Prepared from hash-bound stage using reviewed frozen Prepare; remote byte/xdata checks do not independently enumerate dynamic Windows function tables.')
 (run/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(result='PASS',path=str(run/'result.json'))))
if __name__=='__main__':main()
