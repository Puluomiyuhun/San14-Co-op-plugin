"""Actual two-window reward Runtime in owned native processes; no game access.
Builds production exports; native success fixture still substitutes game business.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,shutil,re
from a_runtime_reward_three_exports_sources import sources as generate
import a_runtime_reward_three_contract as wire
import a_save_three_repeat_contract as repeat_wire
import ctypes as C
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
BASE=PRIVATE/'a_native_turn_mode0_runs/20261009-232744-407945'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def production(run,overlay,used,private,result):
 home=BASE/'bundle/abi/production/build';out=run/'production';out.mkdir()
 for f in home.glob('*.inc'):shutil.copy2(f,out/f.name);private[str(f)]=sha(f)
 for n in ('checkpoint_planning_hold.dll','planning.lib'):
  shutil.copy2(home/n,out/n);private[str(home/n)]=sha(home/n)
 origin=home/'build.cmd';private[str(origin)]=sha(origin)
 cmd=origin.read_text().replace(str(home),str(out)).replace(str(P),str(overlay))
 cmd=cmd.replace('a_native_turn_runtime.cpp','a_runtime_reward_three_runtime.cpp').replace('a_native_turn_exports.cpp','a_runtime_reward_three_exports.cpp')
 cl=next(x for x in cmd.splitlines() if x.startswith('cl ') and 'a_runtime_reward_three_runtime.cpp' in x)
 sourcecl=cl.replace('a_runtime_reward_three_runtime.cpp','a_runtime_reward_source.cpp').replace('/Fo:runtime.obj','/Fo:reward_source.obj')
 cmd=cmd.replace(cl,sourcecl+'\nif errorlevel 1 exit /b 1\n'+cl,1)
 cmd='\n'.join(x.replace(' runtime.obj',' reward_source.obj runtime.obj') if x.startswith('lib ') else x for x in cmd.splitlines())+'\n'
 (out/'build.cmd').write_text(cmd,encoding='utf-8')
 proc=subprocess.run(['cmd','/c',str(out/'build.cmd')],cwd=out,capture_output=True,text=True,errors='replace',timeout=180)
 (out/'compile.log').write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0,'production DLL compilation failed'
 schema=['#include "a_runtime_reward_three_exports.h"','#include "a_save_repeat_exports.h"','#include <cstdio>','#include <cstddef>','int main(){puts("{");']
 native_names={n:'a_runtime_reward_wire::'+n for n in wire.TYPES}
 native_names.update(Open='a_runtime_reward_planning_wire::Open',PlanningSnapshot='a_runtime_reward_planning_wire::Snapshot')
 all_types=dict(wire.TYPES)
 for n,t in wire.base.TYPES.items():all_types['Runtime.'+n]=t;native_names['Runtime.'+n]='a_save_runtime_wire::'+n
 for n,t in repeat_wire.TYPES.items():all_types['Repeat.'+n]=t;native_names['Repeat.'+n]='a_save_repeat_wire::'+('Snapshot' if n=='RepeatSnapshot' else n)
 for index,(name,kind) in enumerate(all_types.items()):
  native=native_names[name]
  schema.append('printf("'+ (' ,' if index else '') +'\\"'+name+'\\":{\\"size\\":%zu,\\"fields\\":{",sizeof('+native+'));')
  for field_index,(field,_) in enumerate(kind._fields_):
   schema.append('printf("'+(',' if field_index else '')+'\\"'+field+'\\":{\\"offset\\":%zu,\\"size\\":%zu}",offsetof('+native+','+field+'),sizeof((('+native+'*)0)->'+field+'));')
  schema.append('puts("}}");')
 schema.append('puts("}");return 0;}')
 (out/'schema.cpp').write_text('\n'.join(schema),encoding='utf-8')
 abi=r'''#include "a_runtime_reward_three_exports.h"
#include "a_save_repeat_exports.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
namespace w=a_save_runtime_wire;namespace r=a_runtime_reward_wire;namespace p=a_runtime_reward_planning_wire;
using Fn=DWORD(WINAPI*)(void*);
void need(bool x){if(!x){puts("FAIL ABI");exit(2);}}
template<class T>void check(HMODULE dll,const char*name,unsigned op){
 auto fn=reinterpret_cast<Fn>(GetProcAddress(dll,name));need(fn&&fn(nullptr)==unsigned(w::Result::BadEnvelope));T q{};
 q.header={w::Magic,1,sizeof q,op,0};memset(q.nonce,0x37,32);need(fn(&q)==unsigned(w::Result::NotPrepared));
 q.header={0x31585241,1,sizeof q,op,0};need(fn(&q)==unsigned(w::Result::BadEnvelope));
 q.header={w::Magic,1,sizeof q-1,op,0};need(fn(&q)==unsigned(w::Result::BadEnvelope));
 q.header={w::Magic,1,sizeof q,op+1,0};need(fn(&q)==unsigned(w::Result::BadEnvelope));
}
int wmain(int argc,wchar_t**argv){need(argc==2);auto dll=LoadLibraryExW(argv[1],nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);need(dll!=nullptr);
need(!GetProcAddress(dll,"ASaveRewardThreeFixtureBind"));
check<r::Configure>(dll,"ASaveRuntimeRewardConfigure",11);check<r::Submit>(dll,"ASaveRuntimeRewardSubmit",12);check<r::Snapshot>(dll,"ASaveRuntimeRewardSnapshot",13);check<p::Open>(dll,"ASaveRuntimeOpenPlanning",14);check<p::Snapshot>(dll,"ASaveRuntimePlanningSnapshot",15);
check<a_save_repeat_wire::Next>(dll,"ASaveRuntimeRequestNext",9);check<a_save_repeat_wire::Snapshot>(dll,"ASaveRuntimeRepeatSnapshot",10);
puts("PASS 5 reward/planning + 2 repeat exports: old Magic, size, opcode, pre-Prepare refused; fixture export absent");return 0;}
'''
 (out/'abi.cpp').write_text(abi,encoding='utf-8')
 basecl=cl[:cl.index(' /c ')];abi_cmd=cmd.splitlines()[:3]
 for stem in ('schema','abi'):
  abi_cmd += [basecl+' "'+str(out/(stem+'.cpp'))+'" /Fe:'+stem+'.exe','if errorlevel 1 exit /b 1']
 # Existing eight-export lifecycle checks also use the dedicated new header.
 used.add('a_save_runtime_exports_test.cpp')
 abi_cmd += [basecl+' "'+str(overlay/'a_save_runtime_exports_test.cpp')+'" /Fe:base-abi.exe','if errorlevel 1 exit /b 1']
 (out/'abi.cmd').write_text('\n'.join(abi_cmd)+'\n',encoding='utf-8')
 proc=subprocess.run(['cmd','/c',str(out/'abi.cmd')],cwd=out,capture_output=True,text=True,errors='replace',timeout=120)
 (out/'abi-compile.log').write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0,'export schema/ABI compilation failed'
 proc=subprocess.run([str(out/'schema.exe')],capture_output=True,text=True,timeout=10);assert proc.returncode==0
 native=json.loads(proc.stdout)
 (out/'schema.json').write_text(json.dumps({n:native[n] for n in wire.TYPES},indent=2)+'\n',encoding='utf-8')
 for name,kind in all_types.items():
  assert native[name]['size']==C.sizeof(kind)
  assert set(native[name]['fields'])=={n for n,_ in kind._fields_}
  for field,typ in kind._fields_:assert native[name]['fields'][field]==dict(offset=getattr(kind,field).offset,size=C.sizeof(typ))
 for section,types in (('Runtime',wire.base.TYPES),('Repeat',repeat_wire.TYPES)):
  path=out/('schema-'+section.lower()+'.json');path.write_text(json.dumps(dict(structures={n:native[section+'.'+n] for n in types}),indent=2)+'\n',encoding='utf-8')
  result['schema_snapshot' if section=='Runtime' else 'schema_repeat']=dict(path=str(path),sha256=sha(path))
 for stem in ('abi','base-abi'):
  proc=subprocess.run([str(out/(stem+'.exe')),str(out/'a_save_local_runtime.dll')],cwd=out,capture_output=True,text=True,errors='replace',timeout=20)
  (out/(stem+'.log')).write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0,'DLL export ABI checks failed: '+stem
 result.update(production_dll=dict(path=str(out/'a_save_local_runtime.dll'),sha256=sha(out/'a_save_local_runtime.dll')),
   dependency_dll=dict(path=str(out/'checkpoint_planning_hold.dll'),sha256=sha(out/'checkpoint_planning_hold.dll')),
   schema_reward=dict(path=str(out/'schema.json'),sha256=sha(out/'schema.json')),schema_fields_verified=True,production_abi_executed=True)
def main():
 run=PRIVATE/'a_runtime_reward_three_exports_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 overlay=run/'src';overlay.mkdir();original={}
 for f in P.iterdir():
  if f.is_file() and f.suffix in ('.cpp','.h','.inc','.py','.asm','.def'):
   original[f.name]=sha(f);shutil.copy2(f,overlay/f.name)
 generated=generate(P)
 for n,s in generated.items():(overlay/n).write_text(s,encoding='utf-8')
 result=dict(result='FAIL',schema='san14.a-three-reward-exports-build.v1',game_access=False,steam_access=False,installed=False,
  room_reward_wired=False,reward_exports_wired=True,native_business_fixture=True)
 private={};used=set();home=BASE/'owned';out=run/'owned';out.mkdir()
 try:
  nonce=bytes([0x37])*32
  for operation,kind in wire.OPERATIONS.items():
   q=wire.envelope(kind,operation,nonce);assert bytes(wire.decode(kind,operation,nonce,bytes(q)))==bytes(q)
   for badnonce in (bytes(32),bytes(31),bytearray(nonce)):
    try:wire.envelope(kind,operation,badnonce)
    except ValueError:pass
    else:raise AssertionError('bad nonce accepted')
   q.header.magic=0x31585241
   try:wire.decode(kind,operation,nonce,bytes(q))
   except ValueError:pass
   else:raise AssertionError('old Magic accepted')
  try:wire.envelope(wire.base.Snapshot,'Snapshot',nonce)
  except ValueError:pass
  else:raise AssertionError('foreign exact type accepted')
  result['python_contract_verified']=True
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
  exportcl=cl.replace('a_runtime_reward_three_runtime.cpp','a_runtime_reward_three_exports.cpp').replace('/Fo:runtime.obj','/Fo:fixture_exports.obj').replace(' /c ', ' /DA_SAVE_REPEAT_FIXTURE /DA_REWARD_THREE_EXPORTS_FIXTURE /c ')
  cmd=cmd.replace(cl,exportcl+'\nif errorlevel 1 exit /b 1\n'+cl,1)
  cmd=cmd.replace('sampler.obj turncontrol.obj fixture_runtime.obj','sampler.obj turncontrol.obj fixture_runtime.obj fixture_exports.obj')
  cmd='\n'.join(x.replace(' fixture_runtime.obj',' reward_source.obj fixture_runtime.obj') if x.startswith('link ') else x for x in cmd.splitlines())+'\n'
  original_fixture=home/'scoped_fixture.cpp';private[str(original_fixture)]=sha(original_fixture)
  fixture=original_fixture.read_text().replace('a_native_turn_runtime.h','a_runtime_reward_three_runtime.h')
  marker=' SECURITY_ATTRIBUTES sa'
  assert fixture.count(marker)==1
  fixture=fixture.replace(marker,' return runtimeThreeCase(*runtime,data,caseName);\n'+marker)
  reward_fixture=(P/'a_runtime_reward_three_fixture.inc').read_text()
  reward_fixture=reward_fixture.replace(' using namespace a_save_local_runtime;',' using namespace a_save_local_runtime;RewardExportProxy proxy;')
  for method in ('ConfigureReward','OpenPlanning','PlanningSnapshot','SubmitReward','RewardSnapshot','RequestNext','Stop'):
   reward_fixture=reward_fixture.replace('runtime.'+method+'(', 'proxy.'+method+'(')
  reward_fixture=(P/'a_runtime_reward_three_export_fixture.inc').read_text()+'\n'+reward_fixture
  fixture=fixture.replace('session=runtime->FixtureOwner()', 'ASaveRewardThreeFixtureBind(runtime,&conf);session=runtime->FixtureOwner()')
  fixture=fixture.replace('int wmain(int argc,wchar_t**argv)',reward_fixture+'\nint wmain(int argc,wchar_t**argv)')
  (out/'scoped_fixture.cpp').write_text(fixture,encoding='utf-8');(out/'build.cmd').write_text(cmd,encoding='utf-8')
  names=re.findall(re.escape(str(overlay))+r'\\([^"\n]+)',cmd)
  used.update(n for n in names if (P/n).is_file())
  used.update(('a_runtime_reward_three_exports_test.py','a_runtime_reward_three_exports_sources.py','a_runtime_reward_three_exports.h','a_runtime_reward_three_exports.cpp','a_runtime_reward_three_export_fixture.inc','a_runtime_reward_three_contract.py','a_save_three_runtime_contract.py','a_save_three_repeat_contract.py','a_runtime_reward_three_sources.py','a_runtime_reward_three_fixture.inc','a_runtime_reward_three_test.py','a_save_three_cycle_sources.py','a_runtime_reward_planning_runtime.h','a_runtime_reward_planning_runtime.cpp','a_native_turn_owner.cpp','a_native_turn_mode0_owner.cpp'))
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
  observations=[]
  for f in sorted((run/'normal').glob('*.bin')):
   kind,op=(wire.Snapshot,'Snapshot') if f.name.startswith('reward-') else (wire.PlanningSnapshot,'PlanningSnapshot')
   q=wire.decode(kind,op,bytes([0x37])*32,f.read_bytes());assert q.header.result==0
   observations.append(dict(path=str(f),operation=op,period=q.context.period,state=q.state,completed=getattr(q,'completed',None)))
  assert {x['period'] for x in observations if x['operation']=='PlanningSnapshot' and x['state']==2}=={1,2}
  assert [x['completed'] for x in observations if x['operation']=='Snapshot']==[1,2,3,4]
  result['export_observations']=observations
  production(run,overlay,used,private,result)
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
