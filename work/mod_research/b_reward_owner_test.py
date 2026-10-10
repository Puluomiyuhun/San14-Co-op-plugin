"""Real retained Runtime/parent/Owner integration; owned memory/native bodies only."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,shutil,os,sys,re
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
BASE=PRIVATE/'a_native_turn_mode0_runs/20261009-232744-407945'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def execute(args,folder,log,timeout=180):
 r=subprocess.run(args,cwd=folder,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
 log.write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,str(log);return r


def main():
 run=PRIVATE/'b_reward_owner_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 result={'result':'FAIL','game_access':False,'steam_access':False};sources={};private={}
 try:
  approved=PRIVATE/'a_runtime_reward_planning_runs/20261010-021152-669026'
  old=load(approved/'result.json');assert sha(approved/'result.json')=='45dbe45c21460e598a8f8889a381be69f21a1d5057ac0b0195fc535d9dc017ea'
  for n,h in old['sources'].items():assert sha(P/n)==h,n;sources[n]=h
  for f in P.glob('b_reward_*'):
   if f.suffix in ('.h','.cpp','.inc') or f.name=='b_reward_owner_test.py':sources[f.name]=sha(f)
  todo=list(sources)
  while todo:
   n=todo.pop()
   for inc in re.findall(r'#include\s+"([^"\n]+)"',(P/n).read_text(encoding='utf-8-sig')):
    f=P/inc
    if f.is_file() and inc not in sources:sources[inc]=sha(f);todo.append(inc)
  home=approved/'owned';out=run/'owned';out.mkdir()
  for f in home.glob('*.inc'):shutil.copy2(f,out/f.name);private[str(f)]=sha(f)
  for n in ('checkpoint_planning_hold.dll','planning.lib'):shutil.copy2(home/n,out/n);private[str(home/n)]=sha(home/n)
  cmd=(home/'build.cmd').read_text();private[str(home/'build.cmd')]=sha(home/'build.cmd')
  cmd=cmd.replace(str(home),str(out)).replace('a_save_planning_mode_input.cpp','b_reward_input.cpp')
  cl=next(x for x in cmd.splitlines()if x.startswith('cl ')and '/Fo:fixture_runtime.obj' in x)
  add=cl.replace('a_runtime_reward_planning_runtime.cpp','b_reward_owner.cpp').replace('/Fo:fixture_runtime.obj','/Fo:b_reward.obj')+' /DB_REWARD_FIXTURE'
  cmd=cmd.replace(cl,add+'\nif errorlevel 1 exit /b 1\n'+cl,1)
  cmd=cmd.replace('link /nologo /OUT:fixture.exe','link /nologo /OUT:fixture.exe b_reward.obj')
  original=home/'scoped_fixture.cpp';private[str(original)]=sha(original)
  s=original.read_text().replace('#include "a_runtime_reward_planning_runtime.h"','#include "a_runtime_reward_planning_runtime.h"\n#include "b_reward_owner.h"')
  s=s.replace('int wmain(int argc,wchar_t**argv)',(P/'b_reward_fixture.inc').read_text()+'\nint wmain(int argc,wchar_t**argv)')
  s=s.replace('RewardData data;parentLayout();','RewardData data;if(caseName==L"b-reward"||caseName==L"b-load-conflict"||caseName==L"b-stop-queued")return bRewardCase(data,caseName,argv[2]);parentLayout();',1)
  (out/'scoped_fixture.cpp').write_text(s);(out/'build.cmd').write_text(cmd)
  execute(['cmd','/c',str(out/'build.cmd')],out,out/'compile.log')
  # Independent production DLL: no A Runtime, Driver, Gate or parent object.
  prod=run/'production';prod.mkdir();shutil.copy2(home/'planning.lib',prod/'planning.lib');shutil.copy2(home/'checkpoint_planning_hold.dll',prod/'checkpoint_planning_hold.dll')
  vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
  opts=f'/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT /I"{P}" /I"{PRIVATE}"'
  names=['b_reward_owner','b_reward_input','a_runtime_reward_source','a_save_local_binding','a_save_early_guard','checkpoint_load_hook_set','a_reward_save_owner_bridge','native_storage_read_core']
  lines=['@echo off',f'call "{vc}" >nul','if errorlevel 1 exit /b 1']
  for n in names:lines.extend([f'cl {opts} /c "{P/(n+".cpp")}" /Fo:{n}.obj','if errorlevel 1 exit /b 1'])
  lines.extend([f'cl {opts} /c "{P/"checkpoint_reward_owned_replay.cpp"}" /Fo:reward.obj','if errorlevel 1 exit /b 1',f'ml64 /nologo /c /Fobridge_asm.obj "{P/"a_save_user_owner_bridge.asm"}"','if errorlevel 1 exit /b 1','link /nologo /DLL /OUT:b_reward_owner.dll '+' '.join(n+'.obj'for n in names)+' reward.obj bridge_asm.obj planning.lib bcrypt.lib','if errorlevel 1 exit /b 1'])
  (prod/'build.cmd').write_text('\n'.join(lines)+'\n');execute(['cmd','/c',str(prod/'build.cmd')],prod,prod/'compile.log')
  rows=[];exe=out/'fixture.exe'
  for case in ('b-reward','b-load-conflict','b-stop-queued'):
   folder=run/case;folder.mkdir();r=execute([str(exe),case,str(folder),sha(exe)],folder,folder/'run.log',30)
   data=[json.loads(x)for x in r.stdout.splitlines()if x.startswith('{')];assert data[-1]['passed'];rows.append({'case':case,'output':data})
  assert all(sha(P/n)==h for n,h in sources.items());assert all(sha(Path(n))==h for n,h in private.items())
  result.update(result='PASS',cases=rows,production_dll=str(prod/'b_reward_owner.dll'),production_sha256=sha(prod/'b_reward_owner.dll'),dependencies=[{'path':str(prod/'checkpoint_planning_hold.dll'),'sha256':sha(prod/'checkpoint_planning_hold.dll')}])
 except Exception as e:result['error']=repr(e)
 result.update(sources=sources,private_inputs=private,artifacts={str(f.relative_to(run)):sha(f)for f in run.rglob('*')if f.is_file()})
 save(run/'result.json',result);print(run);print(result['result']);return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
