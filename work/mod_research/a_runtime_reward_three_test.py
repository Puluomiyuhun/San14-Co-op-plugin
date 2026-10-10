"""Actual two-window reward Runtime in owned native processes; no game access.
Does not produce a deployable reward-export DLL or claim room/menu integration.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,shutil,re
from a_runtime_reward_three_sources import sources as generate
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
BASE=PRIVATE/'a_native_turn_mode0_runs/20261009-232744-407945'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=PRIVATE/'a_runtime_reward_three_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 overlay=run/'src';overlay.mkdir();original={}
 for f in P.iterdir():
  if f.is_file() and f.suffix in ('.cpp','.h','.inc','.py','.asm','.def'):
   original[f.name]=sha(f);shutil.copy2(f,overlay/f.name)
 generated=generate(P)
 for n,s in generated.items():(overlay/n).write_text(s,encoding='utf-8')
 result=dict(result='FAIL',game_access=False,steam_access=False,installed=False,
  room_reward_wired=False,reward_exports_wired=False,native_business_fixture=True)
 private={};used=set();home=BASE/'owned';out=run/'owned';out.mkdir()
 try:
  record=BASE/'result.json';assert sha(record)=='3b905485a78bf04e54eaa3031a07c6ef2fc7afebc7a8e60417256310025c0b18'
  private[str(record)]=sha(record)
  for n,h in json.loads(record.read_text())['sources'].items():
   assert sha(P/n)==h,'frozen native predecessor changed: '+n
   used.add(n)
  for f in home.glob('*.inc'):shutil.copy2(f,out/f.name);private[str(f)]=sha(f)
  for n in ('checkpoint_planning_hold.dll','planning.lib'):
   shutil.copy2(home/n,out/n);private[str(home/n)]=sha(home/n)
  private[str(PRIVATE/'checkpoint_planning_hold.lib')]=sha(PRIVATE/'checkpoint_planning_hold.lib')
  build=home/'build.cmd';private[str(build)]=sha(build);cmd=build.read_text()
  cmd=cmd.replace(str(home),str(out)).replace(str(P),str(overlay)).replace('a_native_turn_runtime.cpp','a_runtime_reward_three_runtime.cpp')
  cl=next(x for x in cmd.splitlines() if x.startswith('cl ') and 'a_runtime_reward_three_runtime.cpp' in x)
  add=cl.replace('a_runtime_reward_three_runtime.cpp','a_runtime_reward_source.cpp').replace('/Fo:runtime.obj','/Fo:reward_source.obj')
  cmd=cmd.replace(cl,add+'\nif errorlevel 1 exit /b 1\n'+cl,1)
  cmd='\n'.join(x.replace(' fixture_runtime.obj',' reward_source.obj fixture_runtime.obj') if x.startswith('link ') else x for x in cmd.splitlines())+'\n'
  original_fixture=home/'scoped_fixture.cpp';private[str(original_fixture)]=sha(original_fixture)
  fixture=original_fixture.read_text().replace('a_native_turn_runtime.h','a_runtime_reward_three_runtime.h')
  marker=' SECURITY_ATTRIBUTES sa'
  assert fixture.count(marker)==1
  fixture=fixture.replace(marker,' return runtimeThreeCase(*runtime,data,caseName);\n'+marker)
  fixture=fixture.replace('int wmain(int argc,wchar_t**argv)',(P/'a_runtime_reward_three_fixture.inc').read_text()+'\nint wmain(int argc,wchar_t**argv)')
  (out/'scoped_fixture.cpp').write_text(fixture,encoding='utf-8');(out/'build.cmd').write_text(cmd,encoding='utf-8')
  names=re.findall(re.escape(str(overlay))+r'\\([^"\n]+)',cmd)
  used.update(n for n in names if (P/n).is_file())
  used.update(('a_runtime_reward_three_sources.py','a_runtime_reward_three_fixture.inc','a_runtime_reward_three_test.py','a_save_three_cycle_sources.py','a_runtime_reward_planning_runtime.h','a_runtime_reward_planning_runtime.cpp','a_native_turn_owner.cpp','a_native_turn_mode0_owner.cpp'))
  # Record every generated predecessor and transitive local include actually compiled.
  used.update(n for n in generated if (P/n).is_file())
  todo=list(used)+['a_runtime_reward_three_runtime.h','a_runtime_reward_three_runtime.cpp']
  while todo:
   n=todo.pop()
   for inc in re.findall(r'#include\s+"([^"\n]+)"',(overlay/n).read_text(encoding='utf-8-sig')):
    if (P/inc).is_file() and inc not in used:used.add(inc);todo.append(inc)
  proc=subprocess.run(['cmd','/c',str(out/'build.cmd')],cwd=out,capture_output=True,text=True,errors='replace',timeout=180)
  (out/'compile.log').write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0,'native compilation failed'
  cases=[];exe=out/'fixture.exe'
  for case in ('normal','second-stop'):
   folder=run/case;folder.mkdir();proc=subprocess.run([str(exe),case,str(folder),sha(exe)],cwd=folder,capture_output=True,text=True,errors='replace',timeout=45)
   (folder/'run.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
   rows=[json.loads(x) for x in proc.stdout.splitlines() if x.startswith('{')]
   cases.append(dict(case=case,exit=proc.returncode,rows=rows));result['cases']=cases
   assert proc.returncode==0 and rows[-1]['passed'],'owned native case failed: '+case
  assert all(sha(P/n)==original[n] for n in used),'source drift'
  assert all(sha(Path(n))==h for n,h in private.items()),'private source drift'
  result['result']='PASS'
 except Exception as e:result['error']=repr(e)
 result['sources']={str(P/n):original[n] for n in sorted(used)}
 result['private_inputs']=private
 result['generated_sources']={str(overlay/n):sha(overlay/n) for n in generated}
 result['artifacts']={str(f.relative_to(run)):sha(f) for f in run.rglob('*') if f.is_file()}
 path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(result=result['result'],path=str(path))));return result['result']!='PASS'
if __name__=='__main__':raise SystemExit(main())
