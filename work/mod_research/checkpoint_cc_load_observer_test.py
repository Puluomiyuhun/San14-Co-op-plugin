"""Only own-process PE callbacks and archived bytes; never discovers a game."""
from pathlib import Path
from datetime import datetime
import subprocess,json,hashlib
P=Path(__file__).resolve().parent
CASES=('success','title-transparent','concurrent-unowned','unowned-only','bad-binding','guard-bind','guard-worker',
 'wrong-worker-owner','wrong-worker-vtable','wrong-worker-caller','wrong-read-caller','wrong-parent',
 'wrong-name','wrong-size','wrong-storage','bad-buffer','short-read','negative-read','wrong-hash',
 'guard-read','guard-seh','missing-read','native-failure','duplicate-read','duplicate-worker',
 'worker-seh','worker-cpp','read-seh','read-cpp','stop-before-read','stop-during-read')
SOURCES=('checkpoint_cc_load_observer.h','checkpoint_cc_load_observer.cpp','checkpoint_cc_load_observer_fixture.cpp',
 'checkpoint_cc_load_observer_fixture.asm','checkpoint_cc_load_observer_build.cmd','checkpoint_cc_load_observer_test.py',
 'checkpoint_load_worker_bridge.h','checkpoint_load_worker_bridge.cpp','checkpoint_load_worker_bridge.asm',
 'native_storage_read_core.h','native_storage_read_core.cpp')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 run=P/'checkpoint_cc_load_observer_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 build=subprocess.run(['cmd','/c',str(P/'checkpoint_cc_load_observer_build.cmd')],cwd=P,capture_output=True)
 (run/'build.stdout.txt').write_bytes(build.stdout);(run/'build.stderr.txt').write_bytes(build.stderr)
 if build.returncode:
  print(build.stdout.decode(errors='replace'));raise SystemExit(build.returncode)
 archive=P/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
 assert sha(archive)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
 rows=[]
 for case in CASES:
  try:
   proc=subprocess.run([str(P/'checkpoint_cc_load_observer_fixture.exe'),case,str(archive)],cwd=P,capture_output=True,timeout=20)
   (run/(case+'.stdout.txt')).write_bytes(proc.stdout);(run/(case+'.stderr.txt')).write_bytes(proc.stderr)
   lines=[x for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
   row=json.loads(lines[-1]) if lines else {'case':case,'passed':False,'error':'No report'}
   row['exit_code']=proc.returncode;row['passed']=bool(row['passed'] and proc.returncode==0)
  except subprocess.TimeoutExpired:row={'case':case,'passed':False,'error':'Own fixture timeout'}
  rows.append(row)
 result={'schema':'san14.checkpoint-cc-load-observer-fixtures.v1','result':'PASS' if all(x['passed'] for x in rows) else 'FAIL',
  'cases':rows,'source_sha256':{name:sha(P/name) for name in SOURCES},'fixture_binary_sha256':sha(P/'checkpoint_cc_load_observer_fixture.exe'),
  'production_object_sha256':sha(P/'checkpoint_cc_load_observer.obj'),'archive_sha256':sha(archive),
  'game_access':False,'steam_api_called':False,'load_authorized':False,
  'scope':'Real PE two-slot finally bridge; fixture-only caller labels and synthetic native body/objects. Actual archived 274880 bytes hashed. No real Steam or game-world deserialization.'}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[r['case'] for r in rows if not r['passed']],'path':str(run/'result.json')}))
 raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
