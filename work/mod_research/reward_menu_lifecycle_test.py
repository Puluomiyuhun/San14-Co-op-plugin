"""Owned archived queue/consumer plus real handoff capture. No live entry."""
from pathlib import Path
from datetime import datetime
import argparse,hashlib,json,subprocess
import reward_menu_completion_audit as audit
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
VC=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--archive-root',type=Path,required=True);args=a.parse_args()
 run=PRIVATE/'reward_menu_lifecycle_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 names=['reward_menu_lifecycle.h','reward_menu_lifecycle.cpp','reward_menu_lifecycle_bridge.asm','reward_menu_lifecycle_fixture.cpp','reward_menu_lifecycle_test.py','reward_menu_handoff_gate.h','reward_menu_handoff_gate.cpp','reward_menu_observation_decode.inc','reward_menu_completion_audit.py','reward_menu_completion_fixture.cpp','reward_menu_completion_fixture.asm']
 sources={n:sha(P/n)for n in names};private={};result={'result':'FAIL','game_access':False,'production_permit':False,'cases':[]}
 try:
  evidence,_,image=audit.inspect(args.archive_root);private={str(image):sha(image),str(image.with_name('runtime-pdata.bin')):sha(image.with_name('runtime-pdata.bin'))}
  raw=image.read_bytes();ranges=((0x67A930,0x67A9C1),)+audit.RANGES[1:]
  code=run/'owned-code.bin';code.write_bytes(b''.join(raw[a:b]for a,b in ranges))
  (run/'archive-audit.json').write_text(json.dumps(evidence,indent=2))
  flags=f'/nologo /std:c++17 /EHa /W4 /WX /O2 /MT /I"{P}"'
  lines=['@echo off',f'call "{VC}" >nul','if errorlevel 1 exit /b 1',f'ml64 /nologo /c /Fobridge.obj "{P/"reward_menu_lifecycle_bridge.asm"}"','if errorlevel 1 exit /b 1']
  for n in ('reward_menu_lifecycle','reward_menu_handoff_gate','reward_menu_lifecycle_fixture'):
   lines.extend([f'cl {flags} /c "{P/(n+".cpp")}" /Fo:{n}.obj','if errorlevel 1 exit /b 1'])
  lines.extend(['link /nologo /OUT:fixture.exe reward_menu_lifecycle.obj reward_menu_handoff_gate.obj reward_menu_lifecycle_fixture.obj bridge.obj','if errorlevel 1 exit /b 1'])
  cmd=run/'build.cmd';cmd.write_text('\n'.join(lines)+'\n')
  r=subprocess.run(['cmd','/c',str(cmd)],cwd=run,capture_output=True,timeout=120);(run/'build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,'compile failed'
  for case in ('normal','normal-freed','wrong-top','duplicate','queued-only'):
   r=subprocess.run([str(run/'fixture.exe'),str(code),case],cwd=run,capture_output=True,timeout=15);(run/(case+'.log')).write_bytes(r.stdout+r.stderr)
   assert r.returncode==0,(case,r.returncode,r.stderr.decode(errors='replace'))
   row=json.loads(r.stdout);assert row['passed'];result['cases'].append(row)
  assert all(sha(P/n)==h for n,h in sources.items());assert all(sha(Path(n))==h for n,h in private.items());result['result']='PASS'
 except Exception as e:result['error']=repr(e)
 result.update(sources=sources,private_inputs=private,artifacts={str(f.relative_to(run)):sha(f)for f in run.rglob('*')if f.is_file()})
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run);print(result['result']);return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
