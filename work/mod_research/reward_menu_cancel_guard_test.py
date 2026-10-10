"""Single creation claim with mutually exclusive confirmation and guarded cancellation; owned only."""
from pathlib import Path
from datetime import datetime
import argparse,hashlib,json,subprocess
import reward_menu_completion_audit as audit
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
VC=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
CASES=('normal','zero-payload','duplicate-notify','confirm','pending-confirm','no-creation','wrong-top-before','prequeued','wrong-generation','foreign-callback','source-tamper','wrong-thread','queued-only','duplicate-close','wrong-top-after')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-root',type=Path,required=True);args=parser.parse_args()
 run=PRIVATE/'reward_menu_cancel_guard_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 units=('reward_menu_cancel_guard','reward_menu_closed_publication','reward_menu_dispatch','reward_menu_lifecycle','reward_menu_handoff_gate')
 names=[n+s for n in units for s in ('.cpp','.h')]+['reward_menu_cancel_guard_fixture.cpp','reward_menu_cancel_guard_test.py','reward_menu_creation.cpp','reward_menu_creation.h','reward_menu_creation_bridge.asm','reward_menu_creation_fixture.asm','reward_menu_dispatch_fixture.cpp','reward_menu_dispatch_bridge.asm','reward_menu_observation_decode.inc','reward_menu_completion_audit.py']
 sources={str(P/n):sha(P/n)for n in names};private={};result=dict(result='FAIL',cases=[],production_permit=False,game_access=False,steam_access=False)
 try:
  evidence,_,image=audit.inspect(args.archive_root);pdata=image.with_name('runtime-pdata.bin');private={str(image):sha(image),str(pdata):sha(pdata)};raw=image.read_bytes()
  full=((0x67A930,0x67A9C1),(0x10A60,0x10AEA),(0x509FE0,0x50B690))+audit.RANGES[3:]+((0xEF9F20,0xEF9F41),(0x17D2400,0x17D2440))
  creation=((0x3FA094,0x3FA0B4),(0x3FC270,0x3FCAB4),(0x3E2CF0,0x3E2E59),(0x509EC0,0x509EE2),(0x509E10,0x509EBD),(0x6082E0,0x6083A5))
  for name,ranges in (('completion-code',full),('creation-code',creation)):
   (run/(name+'.bin')).write_bytes(b''.join(raw[a:b]for a,b in ranges));result[name]=[dict(start=hex(a),end=hex(b),sha256=hashlib.sha256(raw[a:b]).hexdigest())for a,b in ranges]
  (run/'archive-audit.json').write_text(json.dumps(evidence,indent=2)+'\n')
  (run/'callback-code.bin').write_bytes(raw[0x5CC180:0x5CC18E]+raw[0x4D4AA0:0x4D4AB5])
  flags=f'/nologo /std:c++17 /EHa /O2 /W4 /WX /MT /I"{P}"'
  lines=['@echo off',f'call "{VC}" >nul','if errorlevel 1 exit /b 1']
  objects=[]
  for n in ('reward_menu_creation_bridge','reward_menu_creation_fixture','reward_menu_dispatch_bridge'):
   lines += [f'ml64 /nologo /c /Fo{n}.obj "{P/(n+".asm")}"','if errorlevel 1 exit /b 1'];objects.append(n+'.obj')
  lines += [f'cl {flags} /c "{P/"reward_menu_creation.cpp"}" /Fo:creation_production.obj','if errorlevel 1 exit /b 1',f'cl {flags} /DREWARD_MENU_CREATION_FIXTURE /c "{P/"reward_menu_creation.cpp"}" /Fo:creation_fixture.obj','if errorlevel 1 exit /b 1'];objects.append('creation_fixture.obj')
  for n in units+('reward_menu_cancel_guard_fixture',):
   lines += [f'cl {flags} /c "{P/(n+".cpp")}" /Fo:{n}.obj','if errorlevel 1 exit /b 1'];objects.append(n+'.obj')
  lines += ['link /nologo /OUT:fixture.exe '+' '.join(objects),'if errorlevel 1 exit /b 1'];cmd=run/'build.cmd';cmd.write_text('\n'.join(lines)+'\n')
  r=subprocess.run(['cmd','/c',str(cmd)],cwd=run,capture_output=True,timeout=120);(run/'build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,'compile failed'
  for case in CASES:
   r=subprocess.run([str(run/'fixture.exe'),str(run/'completion-code.bin'),str(run/'creation-code.bin'),str(run/'callback-code.bin'),case],cwd=run,capture_output=True,timeout=15);(run/(case+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,(case,r.returncode,r.stderr.decode(errors='replace'));row=json.loads(r.stdout);assert row['passed'] and row['cancel_published']==(case in ('normal','zero-payload','duplicate-notify')) and row['confirm_published']==(case=='confirm') and row['original_rewards']==0
   if row['cancel_published']:assert row['handoff_captures']==row['handoff_takes']==0 and row['notifications']==1
   result['cases'].append(row)
  assert all(sha(Path(n))==h for n,h in sources.items()),'source drift';assert all(sha(Path(n))==h for n,h in private.items()),'archive drift';result['result']='PASS'
 except Exception as e:result['error']=repr(e)
 result.update(sources=sources,private_inputs=private,artifacts={str(f):sha(f)for f in run.rglob('*')if f.is_file()},boundary='One actually archived-created menu allocation, one creation.Take, then exclusive confirm or cancel. Actual archived cancellation callback 5CC180, Reward slot 4D4AA0 and pop 10A60 execute; full archived 509FE0 is guarded before teardown. Cancel publishes only CancelReceipt, with zero proposal captures/takes and zero reward execution. UI selection/layout, callback object allocation/registration, world-force getter, task/list/parent services remain owned doubles. Owned dispatcher splices are not a production installer. Physical button-to-event mapping, full User/UI permission, picker lifecycle, gameplay execution, room export, parent lease and live exception handling remain unproven.')
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run);print(result['result']);return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
