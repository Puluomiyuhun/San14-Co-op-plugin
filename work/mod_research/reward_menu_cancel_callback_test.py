"""Owned archived cancellation-notification callback. No live UI claims."""
import argparse,hashlib,json,struct,subprocess
from pathlib import Path
from datetime import datetime
import reward_menu_completion_audit as audit
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-root',type=Path,required=True);args=parser.parse_args()
 run=PRIVATE/'reward_menu_cancel_callback_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 sources={str(P/n):sha(P/n)for n in ('reward_menu_cancel_callback_fixture.cpp','reward_menu_cancel_callback_test.py','reward_menu_completion_fixture.cpp','reward_menu_completion_fixture.asm','reward_menu_completion_audit.py')}
 result=dict(result='FAIL',game_access=False,production_permit=False,cases=[]);private={}
 try:
  evidence,code,image=audit.inspect(args.archive_root);raw=image.read_bytes();private={str(image):sha(image),str(image.with_name('runtime-pdata.bin')):sha(image.with_name('runtime-pdata.bin'))}
  base=struct.unpack_from('<Q',raw,0x1331078+40)[0]-0x67A930
  assert struct.unpack_from('<Q',raw,0x1331078+0x70)[0]==base+0x4D4AA0
  assert struct.unpack_from('<Q',raw,0x1337E00+16)[0]==base+0x5CC180
  assert raw[0x6749FC:0x674A01]==bytes.fromhex('ba64000000')
  assert raw[0x6749DC:0x6749E3]==bytes.fromhex('488d051d34cc00')
  (run/'completion-code.bin').write_bytes(code)
  (run/'callback-code.bin').write_bytes(raw[0x5CC180:0x5CC18E]+raw[0x4D4AA0:0x4D4AB5])
  lines=['@echo off',r'call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul','if errorlevel 1 exit /b 1',f'ml64 /nologo /c /Fobridge.obj "{P/"reward_menu_completion_fixture.asm"}"','if errorlevel 1 exit /b 1',f'cl /nologo /std:c++17 /EHa /O2 /W4 /WX /MT /I"{P}" "{P/"reward_menu_cancel_callback_fixture.cpp"}" bridge.obj /Fe:fixture.exe /Fo:fixture.obj','if errorlevel 1 exit /b 1']
  (run/'build.cmd').write_text('\n'.join(lines)+'\n');r=subprocess.run(['cmd','/c',str(run/'build.cmd')],cwd=run,capture_output=True,timeout=120);(run/'build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,'compile failed'
  for case in ('normal','changed-top','duplicate','zero-event'):
   r=subprocess.run([str(run/'fixture.exe'),str(run/'completion-code.bin'),str(run/'callback-code.bin'),case],cwd=run,capture_output=True,timeout=15);(run/(case+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,(case,r.returncode,r.stderr.decode(errors='replace'));row=json.loads(r.stdout);assert row['passed'];result['cases'].append(row)
  assert all(sha(Path(n))==h for n,h in sources.items());result['result']='PASS'
 except Exception as exc:result['error']=repr(exc)
 result.update(sources=sources,private_inputs=private,artifacts={str(f):sha(f)for f in run.rglob('*')if f.is_file()},boundary='Actual archived callback and untagged pop; event100 registration is static evidence. Button4/input notification mapping and full dispatcher not executed; allocator/UI are explicit doubles.')
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run);print(result['result']);return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
