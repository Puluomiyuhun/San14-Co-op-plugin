"""Own process atomic-pair mechanics; no process attach or native game calls."""
from pathlib import Path
from datetime import datetime
import subprocess,json,hashlib
P=Path(__file__).resolve().parent
run=P/'checkpoint_identity_pair_commit_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
sources=['checkpoint_identity_pair_commit'+s for s in ('.h','.cpp','_fixture.cpp','_build.cmd','_test.py')]
build=subprocess.run(['cmd','/c',str(P/'checkpoint_identity_pair_commit_build.cmd')],cwd=P,capture_output=True)
(run/'build.stdout.txt').write_bytes(build.stdout);(run/'build.stderr.txt').write_bytes(build.stderr)
if build.returncode:raise SystemExit(build.returncode)
cases=['success','repeat','wrong-thread','wrong-source','reject-before','reject-intent','reject-commit','reject-after','guard-seh','after-seh','readonly','null','unaligned','zero-owner','same-target','existing-intent','cas-conflict','path-no-terminator','path-unreadable']
rows=[]
for case in cases:
    proc=subprocess.run([str(P/'checkpoint_identity_pair_commit_fixture.exe'),case,str(run/(case+'.intent'))],cwd=P,capture_output=True,timeout=15)
    (run/(case+'.stdout.txt')).write_bytes(proc.stdout);(run/(case+'.stderr.txt')).write_bytes(proc.stderr)
    lines=[line for line in proc.stdout.decode('utf8',errors='replace').splitlines() if line.startswith('{')]
    row=json.loads(lines[-1]) if lines else {'case':case,'passed':False}
    row['exit_code']=proc.returncode;row['passed']=row['passed'] and not proc.returncode;rows.append(row)
def sha(name):return hashlib.sha256((P/name).read_bytes()).hexdigest()
result={'schema':'san14.identity-atomic-pair-fixture.v1','result':'PASS' if all(r['passed'] for r in rows) else 'FAIL',
    'cases':rows,'source_sha256':{name:sha(name) for name in sources},'binary_sha256':sha('checkpoint_identity_pair_commit_fixture.exe'),
    'game_access':False,'native_initializer_called':False,'production_boundary_guard_implemented':False,
    'scope':'Real CMPXCHG16B on own synthetic Title pair plus durable once/guard/failure tests; no native ownership, checkpoint semantics or world initialization proof.'}
(run/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({'result':result['result'],'cases':len(rows),'path':str(run/'result.json')}))
raise SystemExit(0 if result['result']=='PASS' else 1)
