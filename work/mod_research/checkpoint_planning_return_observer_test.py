"""Read-only planning observer tests in our own process; no game discovery."""
from pathlib import Path
from datetime import datetime
import subprocess,json,hashlib
P=Path(__file__).resolve().parent
CASES=('success','reused-user','ui-context-different','early-user-then-success','missing-receipt','wrong-stack','historical-state','wrong-force','wrong-ruler','load-pending','queue-pending','modal-after','native-exception','epoch-after','wrong-caller')
SOURCES=('checkpoint_planning_return_observer.h','checkpoint_planning_return_observer.cpp','checkpoint_planning_return_observer_fixture.cpp','checkpoint_planning_return_observer_fixture.asm','checkpoint_planning_return_observer_build.cmd','checkpoint_planning_return_observer_test.py',
 'checkpoint_guest_native_session.h','checkpoint_guest_native_session.cpp','checkpoint_title_identity_adapter.h','checkpoint_title_identity_adapter.cpp','checkpoint_identity_pair_commit.h','checkpoint_identity_pair_commit.cpp','checkpoint_cc_load_lifecycle.h','checkpoint_cc_load_lifecycle.cpp','checkpoint_cc_load_observer.h','checkpoint_cc_load_observer.cpp',
 'checkpoint_load_request_commit.h','checkpoint_load_request_commit.cpp','checkpoint_load_hook_set.h','checkpoint_load_hook_set.cpp','checkpoint_load_input_boundary.h','checkpoint_load_input_boundary.cpp',
 'checkpoint_load_worker_bridge.h','checkpoint_load_worker_bridge.cpp','checkpoint_load_worker_bridge.asm','checkpoint_load_dispatch_bridge.h','checkpoint_load_dispatch_bridge.cpp','checkpoint_load_dispatch_bridge.asm','checkpoint_push_bridge.h','native_storage_read_core.h','native_storage_read_core.cpp')
def sha(n):return hashlib.sha256((P/n).read_bytes()).hexdigest()
def main():
 run=P/'checkpoint_planning_return_observer_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 build=subprocess.run(['cmd','/c',str(P/'checkpoint_planning_return_observer_build.cmd')],cwd=P,capture_output=True)
 (run/'build.stdout.txt').write_bytes(build.stdout);(run/'build.stderr.txt').write_bytes(build.stderr)
 if build.returncode:print(build.stdout.decode(errors='replace'));raise SystemExit(build.returncode)
 rows=[]
 for case in CASES:
  try:
   r=subprocess.run([str(P/'checkpoint_planning_return_observer_fixture.exe'),case],cwd=P,capture_output=True,timeout=15)
   (run/(case+'.stdout.txt')).write_bytes(r.stdout);(run/(case+'.stderr.txt')).write_bytes(r.stderr)
   lines=[x for x in r.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
   row=json.loads(lines[-1]) if lines else {'case':case,'passed':False,'error':'No report'}
   row['exit_code']=r.returncode;row['passed']=bool(row['passed'] and r.returncode==0)
  except subprocess.TimeoutExpired:row={'case':case,'passed':False,'error':'Own-process timeout'}
  rows.append(row)
 result={'schema':'san14.checkpoint-planning-return-observer-fixtures.v1','result':'PASS' if all(x['passed'] for x in rows) else 'FAIL','cases':rows,
  'source_sha256':{n:sha(n) for n in SOURCES},'production_object_sha256':sha('checkpoint_planning_return_observer_production.obj'),'fixture_binary_sha256':sha('checkpoint_planning_return_observer_fixture.exe'),
  'game_access':False,'steam_file_access':False,'synthetic_upstream_receipt':True,'actual_session_dispatch_wired':False,
  'scope':'Real four-slot bridge invokes standalone observer BEFORE/AFTER around a native-body fixture double, preserving original exception/return. Synthetic native layout and upstream frozen Session receipt. Old Load/Title pages NOACCESS; complete synthetic native arenas hashed before/after to establish observer zero writes. Session production forwarding to new User is explicitly not integrated. No native game code or full-world/input/pixel proof.'}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[r['case'] for r in rows if not r['passed']],'path':str(run/'result.json')}));raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
