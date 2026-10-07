"""Offline bounded two-bank Session routing. Workspace archives/own processes only."""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil,subprocess,sys
P=Path(__file__).resolve().parent
CASES=('two-generations','active-frame','native-exception','post-cas-retained','menu-outstanding','foreign-slot','binding-rejections','wrong-thread')
ARCHIVE=P/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
EXPECTED='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert sha(ARCHIVE)==EXPECTED and ARCHIVE.stat().st_size==274880
 frozen=json.loads((P/'checkpoint_session_generation_frozen_baseline.json').read_text())
 assert all(sha(P/k)==v for k,v in frozen.items()),'Frozen dependency changed'
 run=P/'checkpoint_session_generation_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 if '--no-build' not in sys.argv:
  b=subprocess.run(['cmd','/c',str(P/'checkpoint_session_generation_build.cmd')],capture_output=True,cwd=P)
  (run/'build.stdout.txt').write_bytes(b.stdout);(run/'build.stderr.txt').write_bytes(b.stderr)
  if b.returncode:print(b.stdout.decode(errors='replace'));raise SystemExit(b.returncode)
 rows=[]
 for case in CASES:
  d=run/case;d.mkdir();a=d/'bank-one.dll';b=d/'bank-two.dll';source=d/'svdexccSC03.s14'
  shutil.copyfile(P/'checkpoint_session_generation_fixture_bank.dll',a);shutil.copyfile(a,b);shutil.copyfile(ARCHIVE,source)
  result=subprocess.run([str(P/'checkpoint_session_generation_fixture.exe'),case,str(d),str(a),str(b),str(source)],cwd=P,capture_output=True,timeout=20)
  (d/'stdout.txt').write_bytes(result.stdout);(d/'stderr.txt').write_bytes(result.stderr)
  lines=[x for x in result.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
  row=json.loads(lines[-1]) if lines else {'case':case,'passed':False,'output':result.stdout.decode(errors='replace')}
  row['exit_code']=result.returncode;row['archive_unchanged']=sha(source)==EXPECTED
  row['passed']=bool(row.get('passed') and not result.returncode and row['archive_unchanged']);rows.append(row)
 assert all(sha(P/k)==v for k,v in frozen.items()),'Frozen dependency changed during tests'
 own={f.name:sha(f) for f in P.glob('checkpoint_session_generation_*') if f.suffix in ('.h','.cpp','.cmd','.py','.dll','.exe')}
 report={'schema':'san14.checkpoint-session-generation-fixtures.v1','result':'PASS' if all(r['passed'] for r in rows) else 'FAIL','cases':rows,'source_and_binary_sha256':own,'frozen_dependency_sha256':frozen,'archive_sha256':EXPECTED,'game_access':False,'native_game_code_executed':False,'two_complete_loads':False,'capacity':2,'scope':'Two separately mapped/pinned DLL banks each statically contain the unchanged real Session, request/core/observer implementations and 4+2 immutable assembly bridges. Same six owned slots; original bodies/attachment validators are fixture doubles. User uses actual ABI entry addresses. Only Menu/Game caller labels adapted for one real request CAS. No world deserialization, second CAS, global scheduler fence, admission/release authorization, or game installation.'}
 (run/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'result':report['result'],'path':str(run/'result.json'),'failed':[r['case'] for r in rows if not r['passed']]},ensure_ascii=False))
 raise SystemExit(0 if report['result']=='PASS' else 1)
if __name__=='__main__':main()
