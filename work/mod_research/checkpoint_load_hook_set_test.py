from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
run=P/'checkpoint_load_hook_set_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
build=subprocess.run(['cmd','/c',str(P/'checkpoint_load_hook_set_build.cmd')],capture_output=True)
(run/'build.stdout.txt').write_bytes(build.stdout);(run/'build.stderr.txt').write_bytes(build.stderr)
if build.returncode:print(build.stdout.decode(errors='replace'));raise SystemExit(build.returncode)
rows=[]
for case in ('normal','duplicate','unaligned','inaccessible','wrong-original','protection-drift','foreign-overwrite'):
    proc=subprocess.run([str(P/'checkpoint_load_hook_set_fixture.exe'),case],capture_output=True,timeout=10)
    (run/(case+'.stdout.txt')).write_bytes(proc.stdout);(run/(case+'.stderr.txt')).write_bytes(proc.stderr)
    row=json.loads(proc.stdout.decode().splitlines()[-1]);row['exit_code']=proc.returncode;rows.append(row)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'schema':'san14.checkpoint-load-hook-set.v1','result':'PASS' if all(x['passed'] and x['exit_code']==0 for x in rows) else 'FAIL','cases':rows,'source_sha256':{p.name:sha(p) for p in P.glob('checkpoint_load_hook_set*') if p.suffix in ('.h','.cpp','.cmd','.py')},'binary_sha256':sha(P/'checkpoint_load_hook_set_fixture.exe'),'scope':'Own allocation pointer slots and page protection only; no game, callback-drain or scheduler proof.'}
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'result':result['result'],'cases':len(rows),'path':str(run/'result.json')}));raise SystemExit(result['result']!='PASS')
