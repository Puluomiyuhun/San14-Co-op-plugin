"""Bounded archived reward creation/queue/activation in an owned process only."""
from pathlib import Path
from datetime import datetime
import argparse,hashlib,json,subprocess
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
VC=Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat')
RANGES=((0x3FA094,0x3FA0B4),(0x3FC270,0x3FCAB4),(0x3E2CF0,0x3E2E59),(0x509EC0,0x509EE2),(0x509E10,0x509EBD),(0x6082E0,0x6083A5),(0x50A7BA,0x50B3B6))
CASES=('normal','wrong-command','raw-source-tamper','source-tamper','wrong-world','wrong-menu','wrong-queue-menu','wrong-thread','foreign-call','queued-only','wrong-generation','bridge-registers')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-root',type=Path,required=True);args=parser.parse_args()
 run=PRIVATE/'reward_menu_creation_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 names=('reward_menu_creation.h','reward_menu_creation.cpp','reward_menu_creation_bridge.asm','reward_menu_creation_fixture.cpp','reward_menu_creation_fixture.asm','reward_menu_creation_test.py')
 sources={str(P/n):sha(P/n)for n in names};private={};result=dict(result='FAIL',cases=[],game_access=False,steam_access=False,production_permit=False,parent_scope_proven=False,dispatcher_window_owned=False)
 try:
  image=args.archive_root.resolve()/'game-runtime-image.bin';pdata=image.with_name('runtime-pdata.bin')
  assert sha(image)=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
  private={str(image):sha(image),str(pdata):sha(pdata)};raw=image.read_bytes();code=run/'owned-code.bin';code.write_bytes(b''.join(raw[a:b]for a,b in RANGES))
  result['ranges']=[dict(start=hex(a),end=hex(b),sha256=hashlib.sha256(raw[a:b]).hexdigest())for a,b in RANGES]
  lines=['@echo off',f'call "{VC}" >nul','if errorlevel 1 exit /b 1']
  for n in ('reward_menu_creation_bridge','reward_menu_creation_fixture'):
   lines += [f'ml64 /nologo /c /Fo{n}_asm.obj "{P/(n+".asm")}"','if errorlevel 1 exit /b 1']
  lines += [f'ml64 /nologo /c /DREWARD_MENU_CREATION_SHADOW_STRESS /Fobridge_stress.obj "{P/"reward_menu_creation_bridge.asm"}"','if errorlevel 1 exit /b 1']
  flags=f'/nologo /std:c++17 /EHa /O2 /W4 /WX /MT /I"{P}"'
  lines += [f'cl {flags} /c "{P/"reward_menu_creation.cpp"}" /Fo:production.obj','if errorlevel 1 exit /b 1',f'cl {flags} /DREWARD_MENU_CREATION_FIXTURE /c "{P/"reward_menu_creation.cpp"}" /Fo:creation.obj','if errorlevel 1 exit /b 1',f'cl {flags} "{P/"reward_menu_creation_fixture.cpp"}" creation.obj bridge_stress.obj reward_menu_creation_fixture_asm.obj /Fe:fixture.exe /Fo:fixture.obj /link /INCREMENTAL:NO','if errorlevel 1 exit /b 1']
  build=run/'build.cmd';build.write_text('\n'.join(lines)+'\n');r=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,timeout=120);(run/'build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,'compile failed'
  for case in CASES:
   r=subprocess.run([str(run/'fixture.exe'),str(code),case],cwd=run,capture_output=True,timeout=15);(run/(case+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,(case,r.returncode,r.stderr.decode(errors='replace'));row=json.loads(r.stdout);assert row['passed'];result['cases'].append(row)
  assert all(sha(Path(n))==h for n,h in sources.items());assert all(sha(Path(n))==h for n,h in private.items());result['result']='PASS'
 except Exception as e:result['error']=repr(e)
 result.update(sources=sources,private_inputs=private,source_boundary='Archived command-21 dispatch, creator, ctor, name-copy, queue consumer and stack push; alloc/list/UI/lower lifecycle and world-force-district getter services are owned doubles. Fixture-only observer shim overwrites all four home slots and XMM registers before tail-calling actual observer; production bridge is separately compiled without shim. User pre-tail, full scheduler, actor legality, real selection, exception unwinding through archived functions, installation and parent lease remain unproven.',artifacts={str(f):sha(f)for f in run.rglob('*')if f.is_file()})
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run);print(result['result']);return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
