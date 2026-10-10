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
 run=PRIVATE/'a_runtime_reward_planning_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 result={'result':'FAIL','game_access':False,'steam_access':False};sources={};private={}
 try:
  old=load(BASE/'result.json');assert sha(BASE/'result.json')=='3b905485a78bf04e54eaa3031a07c6ef2fc7afebc7a8e60417256310025c0b18'
  private[str(BASE/'result.json')]=sha(BASE/'result.json')
  execution=load(BASE/'execution.json') if (BASE/'execution.json').exists() else old
  for key in ('sources',):
   for n,h in execution.get(key,{}).items():
    path=P/n;assert sha(path)==h,n;sources[n]=h
  for f in P.glob('a_runtime_reward_*'):
   if f.suffix in ('.cpp','.h','.inc') or f.name=='a_runtime_reward_planning_test.py':sources[f.name]=sha(f)
  todo=list(sources)
  while todo:
   name=todo.pop()
   for inc in re.findall(r'#include\s+"([^"\n]+)"',(P/name).read_text(encoding='utf-8-sig')):
    f=P/inc
    if f.is_file() and inc not in sources:sources[inc]=sha(f);todo.append(inc)
  for label,home in (('production',BASE/'bundle/abi/production/build'),('owned',BASE/'owned')):
   out=run/label;out.mkdir()
   for f in home.glob('*.inc'):shutil.copy2(f,out/f.name);private[str(f)]=sha(f)
   for n in ('checkpoint_planning_hold.dll','planning.lib'):shutil.copy2(home/n,out/n);private[str(home/n)]=sha(home/n)
   cmd=(home/'build.cmd').read_text();private[str(home/'build.cmd')]=sha(home/'build.cmd')
   cmd=cmd.replace(str(home),str(out)).replace('a_native_turn_runtime.cpp','a_runtime_reward_planning_runtime.cpp').replace('a_native_turn_exports.cpp','a_runtime_reward_planning_exports.cpp')
   cl=next(x for x in cmd.splitlines() if x.startswith('cl ') and 'a_runtime_reward_planning_runtime.cpp' in x)
   add=cl.replace('a_runtime_reward_planning_runtime.cpp','a_runtime_reward_source.cpp').replace('/Fo:runtime.obj','/Fo:reward_source.obj').replace('/Fo:fixture_runtime.obj','/Fo:reward_source.obj')
   cmd=cmd.replace(cl,add+'\nif errorlevel 1 exit /b 1\n'+cl,1)
   lines=cmd.splitlines();cmd='\n'.join(x.replace(' runtime.obj',' reward_source.obj runtime.obj').replace(' fixture_runtime.obj',' reward_source.obj fixture_runtime.obj') if x.startswith(('link ','lib ')) else x for x in lines)+'\n'
   if label=='owned':
    original=home/'scoped_fixture.cpp';private[str(original)]=sha(original)
    s=original.read_text().replace('a_native_turn_runtime.h','a_runtime_reward_planning_runtime.h')
    marker='  SECURITY_ATTRIBUTES sa'
    if marker not in s:marker=' SECURITY_ATTRIBUTES sa'
    s=s.replace(marker,' if(caseName==L"bootstrap"||caseName==L"planning-stop")return runtimePlanningCase(*runtime,data,caseName,argv[2]);\n'+marker,1)
    s=s.replace('int wmain(int argc,wchar_t**argv)',(P/'a_runtime_reward_planning_fixture.inc').read_text()+'\nint wmain(int argc,wchar_t**argv)')
    (out/'scoped_fixture.cpp').write_text(s)
   (out/'build.cmd').write_text(cmd)
   execute(['cmd','/c',str(out/'build.cmd')],out,out/'compile.log')
  rows=[];exe=run/'owned/fixture.exe'
  for case in ('bootstrap','planning-stop','normal'):
   folder=run/case;folder.mkdir();r=execute([str(exe),case,str(folder),sha(exe)],folder,folder/'run.log',40)
   rows.append({'case':case,'output':[json.loads(x)for x in r.stdout.splitlines()if x.startswith('{')]})
   assert rows[-1]['output'][-1]['passed']
  assert all(sha(P/n)==h for n,h in sources.items())
  assert all(sha(Path(n))==h for n,h in private.items())
  result.update(result='PASS',cases=rows,production_dll=str(run/'production/a_save_local_runtime.dll'))
 except Exception as e:result['error']=repr(e)
 result.update(sources=sources,private_inputs=private,artifacts={str(f.relative_to(run)):sha(f)for f in run.rglob('*')if f.is_file()})
 save(run/'result.json',result);print(str(run));print(result['result']);return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
