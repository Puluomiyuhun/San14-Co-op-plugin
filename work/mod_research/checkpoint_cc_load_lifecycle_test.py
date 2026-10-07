"""Own-process lifecycle observation only; synthetic native state mutations."""
from pathlib import Path
from datetime import datetime
import subprocess,json,hashlib
P=Path(__file__).resolve().parent
CASES=('success','wait-phase2','snapshot-after-free','wrong-closure-vt','wrong-closure-method','wrong-title-slot',
 'wrong-request-slot','wrong-request-name','wrong-caller','guard-bind','guard-after','phase1-no-start',
 'bad-byte-token','bad-byte-hash','byte-error','missing-byte-finally','join-handle-left','missing-join',
 'failure-status','failure-result','uncleared-slot','uncleared-flags','uncleared-name','uncleared-cache',
 'uncleared-tail','wrong-pop','two-pops','stop-during-final','original-seh','original-cpp')
SOURCES=('checkpoint_cc_load_lifecycle.h','checkpoint_cc_load_lifecycle.cpp','checkpoint_cc_load_lifecycle_fixture.cpp',
 'checkpoint_cc_load_lifecycle_fixture.asm','checkpoint_cc_load_lifecycle_build.cmd','checkpoint_cc_load_lifecycle_test.py',
 'checkpoint_push_bridge.h','checkpoint_push_bridge.cpp','checkpoint_push_bridge.asm','checkpoint_cc_load_observer.h','checkpoint_cc_load_observer.cpp',
 'checkpoint_load_worker_bridge.h','checkpoint_load_worker_bridge.cpp','checkpoint_load_worker_bridge.asm','native_storage_read_core.h','native_storage_read_core.cpp')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 run=P/'checkpoint_cc_load_lifecycle_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 build=subprocess.run(['cmd','/c',str(P/'checkpoint_cc_load_lifecycle_build.cmd')],cwd=P,capture_output=True)
 (run/'build.stdout.txt').write_bytes(build.stdout);(run/'build.stderr.txt').write_bytes(build.stderr)
 if build.returncode:print(build.stdout.decode(errors='replace'));raise SystemExit(build.returncode)
 rows=[]
 for case in CASES:
  try:
   proc=subprocess.run([str(P/'checkpoint_cc_load_lifecycle_fixture.exe'),case],cwd=P,capture_output=True,timeout=10)
   (run/(case+'.stdout.txt')).write_bytes(proc.stdout);(run/(case+'.stderr.txt')).write_bytes(proc.stderr)
   lines=[x for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
   row=json.loads(lines[-1]) if lines else {'case':case,'passed':False,'error':'No report'}
   row['exit_code']=proc.returncode;row['passed']=bool(row['passed'] and proc.returncode==0)
  except subprocess.TimeoutExpired:row={'case':case,'passed':False,'error':'Own fixture timeout'}
  rows.append(row)
 result={'schema':'san14.checkpoint-cc-load-lifecycle-fixtures.v1','result':'PASS' if all(x['passed'] for x in rows) else 'FAIL','cases':rows,
  'source_sha256':{x:sha(P/x) for x in SOURCES},'fixture_binary_sha256':sha(P/'checkpoint_cc_load_lifecycle_fixture.exe'),
  'production_object_sha256':sha(P/'checkpoint_cc_load_lifecycle.obj'),'game_access':False,'load_authorized':False,
  'scope':'Actual old PE before/after bridge and exception propagation; synthetic phase/worker/request mutations and explicit synthetic already-tested byte-observer receipt. No actual native join, Steam or world deserialization executed.'}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[r['case'] for r in rows if not r['passed']],'path':str(run/'result.json')}))
 raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
