from pathlib import Path
from datetime import datetime
import hashlib,json,queue,re,shutil,subprocess,threading
from human_rules_activation_publish_counter_profile import generate
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 run=P/'human_rules_activation_publish_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 src=run/'src';inputs=run/'inputs';inputs.mkdir();captured={}
 generated={'human_rules_activation_publish_fixture_hashes.h','human_rules_activation_publish_fixture_counters.h'}
 def copy(path):
  path=path.resolve();relative=path.relative_to(ROOT)
  if str(relative)in captured:return
  out=src/relative;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,out);captured[str(relative)]=sha(out)
  for name in re.findall(r'^\s*#include\s+"([^"]+)"',path.read_text(encoding='utf-8-sig'),re.M):
   if name in generated:continue
   found=next((f for f in [path.parent/name,P/name,ROOT/'outputs/san14-link'/name]if f.is_file()),None)
   if found is None:raise FileNotFoundError(name)
   copy(found)
 own=['human_rules_activation_publish.cpp','human_rules_activation_publish_config.h','human_rules_activation_publish_inspect.h',
      'human_rules_activation_publish_fixture_stage.cpp','human_rules_activation_publish_target.cpp',
      'human_rules_activation_publish_test.py','human_rules_activation_publish_counter_profile.py','human_rules_activation_publish_production_counters.json']
 deps=['human_rules_activation.asm','human_rules_hook_transport.cpp','human_ai_runtime_adapter.cpp',
       'human_economy_runtime_adapter.cpp','human_ai_runtime_subject.cpp','human_ai_group_resolver.cpp']
 for f in own+deps:copy(P/f)
 sp=src/'work/mod_research'
 for name in ['owned_rules_image.dll','game-runtime-image.bin']:
  shutil.copy2(P/'human_rules_stage_debug_rollback_runs/20261007-214414-327573/inputs'/name,inputs/name)
 shutil.copy2(P/'human_rules_activation_runs/20261007-233145-854344/production.dll',inputs/'production.dll')
 assert sha(inputs/'production.dll')=='fffd793bfd65c7082c838f11aec15506d193fc489f45ee50bd53f22455b3222d'
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 flags='/nologo /W4 /WX /EHa /std:c++17 /O2 /MT /I"'+str(src/'outputs/san14-link')+'"'
 def commands(name,lines):
  cmd=run/f'build-{name}.cmd';cmd.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\nif errorlevel 1 exit /b 1\n'.join(lines)+'\n',encoding='utf-8')
  r=subprocess.run(['cmd','/d','/c',str(cmd)],cwd=run,capture_output=True);(run/f'build-{name}.txt').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stdout.decode(errors='replace'))
 def compile(name,files,extra=''):
  commands(name,['cl '+flags+' '+extra+' '+' '.join('"'+str(sp/f)+'"'for f in files)+' /Fe:"'+str(inputs/name)+'"'])
 commands('stage',['ml64 /nologo /c /Fo"'+str(run/'income.obj')+'" "'+str(sp/'human_rules_activation.asm')+'"',
  'cl '+flags+' /LD '+' '.join('"'+str(sp/f)+'"'for f in ['human_rules_activation_publish_fixture_stage.cpp']+deps[1:])+
  ' "'+str(run/'income.obj')+'" /link /EXPORT:HumanRulesActivationIncome /OUT:"'+str(inputs/'fixture.dll')+'"'])
 compile('target.exe',['human_rules_activation_publish_target.cpp'])
 generate(inputs/'fixture.dll',sp/'human_rules_activation_publish_fixture_counters.h')
 (sp/'human_rules_activation_publish_fixture_hashes.h').write_text('#pragma once\nconstexpr unsigned ExpectedFixture=1;\nconstexpr const char* ApprovedExeSha="'+sha(inputs/'target.exe')+'";\nconstexpr const char* ApprovedStageSha="'+sha(inputs/'fixture.dll')+'";\nconstexpr const char* ApprovedImageSha="'+sha(inputs/'owned_rules_image.dll')+'";\n')
 pub=['human_rules_activation_publish.cpp','human_ai_runtime_subject.cpp','human_ai_group_resolver.cpp']
 compile('publisher-fixture.exe',pub,'/DHUMAN_RULES_ACTIVATION_PUBLISH_FIXTURE')
 compile('publisher-production.exe',pub)
 cases=[]
 for case in ['success','native-seh','day-advanced','active-native','faulted']+[f'rollback-{i}'for i in range(6)]:
  child=subprocess.Popen([str(inputs/'target.exe'),case,str(inputs/'fixture.dll'),str(inputs/'owned_rules_image.dll'),str(inputs/'game-runtime-image.bin')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  lines=queue.Queue()
  def consume():
   for line in child.stdout:lines.put(line)
  threading.Thread(target=consume,daemon=True).start()
  try:ready=json.loads(lines.get(timeout=15))
  except queue.Empty:
   if child.poll() is not None:raise RuntimeError(child.stderr.read().decode(errors='replace'))
   raise
  assert ready['phase']=='prepared'
  config=run/f'{case}.binding.bin';config.write_bytes(bytes.fromhex(ready['binding_hex']))
  def invoke(operation,production=False,birth=None,binding=None):
   args=[str(inputs/('publisher-production.exe'if production else'publisher-fixture.exe')),operation,str(ready['pid']),str(ready['birth']if birth is None else birth),str(ready['image']),str(ready['descriptor']),str(inputs/('production.dll'if production else'fixture.dll')),ready['nonce'],str(binding or config)]
   # Deliberately no killing timeout: uncertain debugger remains responsible
   # for its target. All tested paths are finite clean success/rejection/rollback.
   r=subprocess.run(args,capture_output=True)
   label=case+'-'+operation+('-production'if production else'')+('-wrongbirth'if birth else'')+('-badbinding'if binding else'')
   (run/f'{label}.stdout.txt').write_bytes(r.stdout);(run/f'{label}.stderr.txt').write_bytes(r.stderr)
   return r.returncode,json.loads(r.stdout.decode().splitlines()[-1])
  if case=='success':
   for label,kwargs in [('production-refuses-fixture',{'production':True}),('wrongbirth',{'birth':ready['birth']^1})]:
    code,report=invoke('install',**kwargs);assert code and not report['attached'];cases.append({'case':label,'report':report})
   bad=run/'wrong-room.binding.bin';data=bytearray(config.read_bytes());data[32]^=1;bad.write_bytes(data)
   code,report=invoke('install',binding=bad);assert code and not report['attached'];cases.append({'case':'wrong-room-before-attach','report':report})
  code,installed=invoke(case if case.startswith('rollback')else'install')
  assert installed['detached'] and installed['held_create_process_event'] and not installed['uncertain'],installed
  if case.startswith('rollback'):assert code==17 and installed['status']=='CLEAN_ROLLBACK' and installed['written_mask']==installed['rolled_mask'],installed
  else:assert code==0 and installed['status']=='INSTALLED_HUMAN_RULES',installed
  child.stdin.write(b'g');child.stdin.flush();middle=json.loads(lines.get(timeout=15));assert middle['phase']=='ready_restore'
  restored=None
  if not case.startswith('rollback'):
   code,restored=invoke('restore')
   if case in ('faulted','active-native'):
    assert code and not restored['attached'] and restored['written_mask']==0,restored
    if case=='active-native':
     active_denial=restored;child.stdin.write(b'r');child.stdin.flush();again=json.loads(lines.get(timeout=15));assert again['phase']=='ready_restore'
     code,restored=invoke('restore');assert code==0 and restored['status']=='RESTORED' and restored['detached'],restored
     restored['earlier_actual_active_denial']=active_denial
   else:assert code==0 and restored['status']=='RESTORED' and restored['detached'],restored
  child.stdin.write(b'f');child.stdin.flush();last=json.loads(lines.get(timeout=15));exit_code=child.wait(timeout=10);assert exit_code==0 and last['result']=='PASS',(exit_code,last)
  (run/f'{case}-target.stderr.txt').write_bytes(child.stderr.read());child.stdin.close();child.stdout.close();child.stderr.close()
  cases.append({'case':case,'install':installed,'restore':restored,'target':last,'child_natural_exit':exit_code})
 for f in sp.iterdir():
  if f.is_file():captured[str(f.relative_to(src))]=sha(f)
 result={'result':'PASS','cases':cases,'source_sha256':captured,'binary_sha256':{f.name:sha(f)for f in inputs.iterdir()if f.is_file()},
         'game_access':False,'actual_mem_image_source':True,'actual_external_debugger':True,'target_function_called_by_publisher':False,
         'fixture_preparer_only_type_query_translation':True,'production_dll_unchanged':True,'production_attached':False}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':'PASS','path':str(run/'result.json')}))
if __name__=='__main__':main()
