"""Own-process integration only. Never discovers/opens/installs into the game."""
from pathlib import Path
from datetime import datetime
import subprocess,json,hashlib
P=Path(__file__).resolve().parent
CASES=('success-early','success-late','actual-byte-mismatch','load-exception','title-exception','read-exception')
ARCHIVE=P/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
EXPECTED='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
SOURCES=('checkpoint_guest_load_observation_chain_fixture.cpp','checkpoint_guest_load_observation_chain_fixture.asm','checkpoint_guest_load_observation_chain_build.cmd','checkpoint_guest_load_observation_chain_test.py',
 'checkpoint_title_identity_adapter.h','checkpoint_title_identity_adapter.cpp','checkpoint_identity_pair_commit.h','checkpoint_identity_pair_commit.cpp',
 'checkpoint_cc_load_lifecycle.h','checkpoint_cc_load_lifecycle.cpp','checkpoint_cc_load_observer.h','checkpoint_cc_load_observer.cpp',
 'checkpoint_load_worker_bridge.h','checkpoint_load_worker_bridge.cpp','checkpoint_load_worker_bridge.asm',
 'checkpoint_push_bridge.h','checkpoint_push_bridge.cpp','checkpoint_push_bridge.asm','native_storage_read_core.h','native_storage_read_core.cpp')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 if ARCHIVE.stat().st_size!=274880 or sha(ARCHIVE)!=EXPECTED:raise SystemExit('Archive identity mismatch')
 run=P/'checkpoint_guest_load_observation_chain_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 proc=subprocess.run(['cmd','/c',str(P/'checkpoint_guest_load_observation_chain_build.cmd')],cwd=P,capture_output=True)
 (run/'build.stdout.txt').write_bytes(proc.stdout);(run/'build.stderr.txt').write_bytes(proc.stderr)
 if proc.returncode:print(proc.stdout.decode(errors='replace'));raise SystemExit(proc.returncode)
 rows=[]
 for case in CASES:
  try:
   r=subprocess.run([str(P/'checkpoint_guest_load_observation_chain_fixture.exe'),case,str(ARCHIVE),str(run/(case+'.intent'))],cwd=P,capture_output=True,timeout=20)
   (run/(case+'.stdout.txt')).write_bytes(r.stdout);(run/(case+'.stderr.txt')).write_bytes(r.stderr)
   reports=[x for x in r.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
   row=json.loads(reports[-1]) if reports else {'case':case,'passed':False,'error':'No fixture report'}
   row['exit_code']=r.returncode;row['passed']=bool(row['passed'] and r.returncode==0)
  except subprocess.TimeoutExpired:row={'case':case,'passed':False,'error':'Own fixture timeout'}
  rows.append(row)
 result={'schema':'san14.checkpoint-guest-load-observation-chain.v1','result':'PASS' if all(x['passed'] for x in rows) else 'FAIL','cases':rows,
  'source_sha256':{x:sha(P/x) for x in SOURCES},'fixture_binary_sha256':sha(P/'checkpoint_guest_load_observation_chain_fixture.exe'),
  'archive_sha256':sha(ARCHIVE),'archive_bytes':ARCHIVE.stat().st_size,'game_access':False,'native_game_code_executed':False,'upstream_receipts_fabricated':False,
  'scope':'Real bytes observer+lifecycle+Title adapter+atomic commit; shared real finally worker/FileRead bridges and original Update bridge. Real archived full buffer copied by a FileRead double, then actually hashed by core. Actual own-process OS worker thread/join; native game dispatcher/body/join-fields/finalizer/initializer are explicit fixture doubles. Lifecycle and byte reports are never directly assigned. Historical Load page NOACCESS before Title dispatch. No live Steam, game, installer, target file or actual world deserialization.'}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[x['case'] for x in rows if not x['passed']],'path':str(run/'result.json')}))
 raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
