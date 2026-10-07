from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
run=P/'checkpoint_load_request_commit_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
build=subprocess.run(['cmd','/c',str(P/'checkpoint_load_request_commit_build.cmd')],capture_output=True)
(run/'build.stdout.txt').write_bytes(build.stdout);(run/'build.stderr.txt').write_bytes(build.stderr)
if build.returncode:print(build.stdout.decode(errors='replace'));raise SystemExit(build.returncode)
archive=P/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
rows=[]
for case in ('success','missing-menu','menu-selection','busy-user','pending-before','wrong-thread','storage-changed','read-short','read-corrupt','read-seh','pending-during-read','reject-before-cas','reject-after-cas','pending-after-cas','existing-intent'):
    case_dir=run/case;case_dir.mkdir()
    proc=subprocess.run([str(P/'checkpoint_load_request_commit_fixture.exe'),case,str(archive),str(case_dir/'svdexccSC03.s14'),str(case_dir/'request.intent')],capture_output=True,timeout=15)
    (case_dir/'stdout.txt').write_bytes(proc.stdout);(case_dir/'stderr.txt').write_bytes(proc.stderr)
    lines=[s for s in proc.stdout.decode(errors='replace').splitlines() if s.startswith('{')]
    row=json.loads(lines[-1]) if lines else {'case':case,'passed':False};row['exit_code']=proc.returncode;rows.append(row)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[p for p in P.glob('checkpoint_load_request_commit*') if p.suffix in ('.h','.cpp','.py','.cmd')]+[P/n for n in ('checkpoint_load_input_boundary.h','checkpoint_load_input_boundary.cpp','checkpoint_load_input_boundary_fixture_layout.h','native_storage_read_core.h','native_storage_read_core.cpp')]
result={'schema':'san14.checkpoint-load-request-commit.v1','result':'PASS' if all(r['passed'] and r['exit_code']==0 for r in rows) else 'FAIL','cases':rows,'source_sha256':{p.name:sha(p) for p in sources},'binary_sha256':sha(P/'checkpoint_load_request_commit_fixture.exe'),'game_access':False,'scope':'Real boundary inspector, real file hash/lease, unique durable intent and aligned pending CAS on synthetic native objects. Storage API doubles return archived full bytes. Does not start native loading.'}
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'result':result['result'],'failed':[x['case'] for x in rows if not x['passed']],'path':str(run/'result.json')}));raise SystemExit(result['result']!='PASS')
