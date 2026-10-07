from pathlib import Path
from datetime import datetime
import subprocess,json,hashlib,shutil,queue,threading
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=P/'human_rules_bound_publish_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 source=run/'sources';source.mkdir();inputs=run/'inputs';inputs.mkdir()
 previous=P/'human_rules_stage_debug_rollback_runs/20261007-214414-327573'
 for f in (previous/'sources').iterdir():
  if f.is_file():shutil.copy2(f,source/f.name)
 for name in ['human_rules_bound_publish.cpp','human_rules_bound_publish_config.h','human_rules_bound_publish_target.cpp','human_rules_bound_publish_test.py']:shutil.copy2(P/name,source/name)
 for name in ['stage_fixture.dll','owned_rules_image.dll','game-runtime-image.bin']:shutil.copy2(previous/'inputs'/name,inputs/name)
 production=P/'human_rules_stage_live_builds/20261007-222216-250737/live_stage.dll';shutil.copy2(production,inputs/'live_stage.dll')
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 flags='/nologo /W4 /WX /EHa /std:c++17 /O2 /MT'
 def build(name,files,extra=''):
  cmd=run/f'build-{name}.cmd';cmd.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\ncl '+flags+' '+extra+' '+' '.join('"'+str(source/f)+'"' for f in files)+' /Fe:"'+str(inputs/name)+'"\n',encoding='utf-8')
  r=subprocess.run(['cmd','/d','/c',str(cmd)],cwd=run,capture_output=True);(run/f'build-{name}.txt').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stdout.decode(errors='replace'))
 build('target.exe',['human_rules_bound_publish_target.cpp'])
 (source/'human_rules_bound_fixture_hashes.h').write_text('#pragma once\nconstexpr unsigned ExpectedFixture=1;\nconstexpr const char* ApprovedExeSha="'+sha(inputs/'target.exe')+'";\nconstexpr const char* ApprovedStageSha="'+sha(inputs/'stage_fixture.dll')+'";\nconstexpr const char* ApprovedImageSha="'+sha(inputs/'owned_rules_image.dll')+'";\n')
 build('publisher-fixture.exe',['human_rules_bound_publish.cpp'],'/DHUMAN_RULES_BOUND_FIXTURE')
 build('publisher-production.exe',['human_rules_bound_publish.cpp'])
 cases=[]
 for case in ['success','native-seh']+[f'rollback-{i}' for i in range(6)]:
  child=subprocess.Popen([str(inputs/'target.exe'),case,str(inputs/'stage_fixture.dll'),str(inputs/'owned_rules_image.dll'),str(inputs/'game-runtime-image.bin')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  lines=queue.Queue()
  def consume():
   for line in child.stdout:lines.put(line)
  thread=threading.Thread(target=consume,daemon=True);thread.start()
  ready=json.loads(lines.get(timeout=15));assert ready['phase']=='prepared'
  def invoke(operation,production=False,birth=None):
   args=[str(inputs/('publisher-production.exe' if production else 'publisher-fixture.exe')),operation,str(ready['pid']),str(ready['birth'] if birth is None else birth),str(ready['image']),str(ready['descriptor']),str(inputs/('live_stage.dll' if production else 'stage_fixture.dll')),ready['nonce']]
   r=subprocess.run(args,capture_output=True,timeout=15)
   label=case+'-'+operation+('-production' if production else '')+('-wrongbirth' if birth else '')
   (run/(label+'.stdout.txt')).write_bytes(r.stdout);(run/(label+'.stderr.txt')).write_bytes(r.stderr)
   out=json.loads(r.stdout.decode().splitlines()[-1]);return r.returncode,out
  if case=='success':
   code,denied=invoke('install',production=True);assert code and not denied['attached']
   cases.append(dict(case='production_rejects_fixture_before_attach',report=denied))
   code,denied=invoke('install',birth=ready['birth']^1);assert code and not denied['attached']
   cases.append(dict(case='wrong_birth_rejected_before_attach',report=denied))
  code,installed=invoke(case if case.startswith('rollback') else 'install')
  assert installed['detached'] and installed['held_create_process_event'] and not installed['uncertain'],installed
  if case.startswith('rollback'):assert code==17 and installed['status']=='CLEAN_ROLLBACK' and installed['written_mask']==installed['rolled_mask'],installed
  else:assert code==0 and installed['status']=='INSTALLED_PASSTHROUGH',installed
  child.stdin.write(b'g');child.stdin.flush();middle=json.loads(lines.get(timeout=15));assert middle['phase']=='ready_restore',middle
  restored=None
  if not case.startswith('rollback'):
   code,restored=invoke('restore');assert code==0 and restored['status']=='RESTORED' and restored['detached'],restored
  child.stdin.write(b'f');child.stdin.flush();last=json.loads(lines.get(timeout=15));exit_code=child.wait(timeout=10);assert exit_code==0 and last['result']=='PASS',(exit_code,last)
  (run/f'{case}-target.stderr.txt').write_bytes(child.stderr.read());child.stdin.close();child.stdout.close();child.stderr.close()
  cases.append(dict(case=case,install=installed,restore=restored,target=last,child_natural_exit=exit_code))
 result=dict(result='PASS',cases=cases,source_sha256={f.name:sha(f)for f in source.iterdir()if f.is_file()},binary_sha256={f.name:sha(f)for f in inputs.iterdir()if f.is_file()},game_access=False,production_controller_compiled_but_not_attached_to_game=True,terminate_process_used=False)
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result='PASS',path=str(run/'result.json'))))
if __name__=='__main__':main()
