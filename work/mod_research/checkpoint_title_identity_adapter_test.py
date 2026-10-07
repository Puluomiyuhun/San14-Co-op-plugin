"""Own-process real bridge/atomic CAS; no game discovery, installer or live API."""
from pathlib import Path
from datetime import datetime
import subprocess,json,hashlib
P=Path(__file__).resolve().parent
CASES=('early','late','transition-during-native','other-transparent','nested-other',
 'wrong-token','missing-completion','missing-join','bad-byte-hash','wrong-owner','wrong-vtable','wrong-caller',
 'wrong-stack','wrong-phase','three-phase13','wrong-slot','wrong-source','wrong-ruler','wrong-person-id',
 'wrong-district','wrong-district-force','wrong-district-leader','missing-person-map','wrong-world-source',
 'guard-before','guard-before-intent','guard-before-cas','guard-after-cas','guard-after','guard-seh',
 'cas-conflict','existing-intent','stop-before-cas','stop-during-native','duplicate-worker',
 'native-no-change','native-wrong-control','native-seh','native-cpp')
SOURCES=('checkpoint_title_identity_adapter.h','checkpoint_title_identity_adapter.cpp','checkpoint_title_identity_adapter_fixture.cpp',
 'checkpoint_title_identity_adapter_fixture.asm','checkpoint_title_identity_adapter_build.cmd','checkpoint_title_identity_adapter_test.py',
 'checkpoint_identity_pair_commit.h','checkpoint_identity_pair_commit.cpp','checkpoint_cc_load_lifecycle.h','checkpoint_cc_load_lifecycle.cpp',
 'checkpoint_cc_load_observer.h','checkpoint_cc_load_observer.cpp','checkpoint_load_worker_bridge.h','checkpoint_load_worker_bridge.cpp',
 'checkpoint_load_worker_bridge.asm','native_storage_read_core.h','native_storage_read_core.cpp')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 run=P/'checkpoint_title_identity_adapter_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 build=subprocess.run(['cmd','/c',str(P/'checkpoint_title_identity_adapter_build.cmd')],cwd=P,capture_output=True)
 (run/'build.stdout.txt').write_bytes(build.stdout);(run/'build.stderr.txt').write_bytes(build.stderr)
 if build.returncode:print(build.stdout.decode(errors='replace'));raise SystemExit(build.returncode)
 rows=[]
 for case in CASES:
  try:
   proc=subprocess.run([str(P/'checkpoint_title_identity_adapter_fixture.exe'),case,str(run/(case+'.intent'))],cwd=P,capture_output=True,timeout=15)
   (run/(case+'.stdout.txt')).write_bytes(proc.stdout);(run/(case+'.stderr.txt')).write_bytes(proc.stderr)
   lines=[x for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
   row=json.loads(lines[-1]) if lines else {'case':case,'passed':False,'error':'No report'}
   row['exit_code']=proc.returncode;row['passed']=bool(row['passed'] and proc.returncode==0)
  except subprocess.TimeoutExpired:row={'case':case,'passed':False,'error':'Own fixture timeout'}
  rows.append(row)
 result={'schema':'san14.checkpoint-title-identity-adapter-fixtures.v1','result':'PASS' if all(x['passed'] for x in rows) else 'FAIL','cases':rows,
  'source_sha256':{x:sha(P/x) for x in SOURCES},'fixture_binary_sha256':sha(P/'checkpoint_title_identity_adapter_fixture.exe'),
  'production_object_sha256':sha(P/'checkpoint_title_identity_adapter.obj'),'game_access':False,'native_initializer_called':False,'live_installer':False,
  'scope':'Actual own-process finally bridge, original ABI/exception propagation, CREATE_NEW intent and atomic128 commit. Synthetic lifecycle/byte receipts, objects and original identity initializer; old Load page NOACCESS in every case. No real Steam, game or world identity initialization.'}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[x['case'] for x in rows if not x['passed']],'path':str(run/'result.json')}))
 raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
