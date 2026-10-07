from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
run=P/'checkpoint_load_dispatch_bridge_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
run.mkdir(parents=True)
proc=subprocess.run([str(P/'checkpoint_load_dispatch_bridge_fixture.exe')],capture_output=True,timeout=20)
(run/'stdout.txt').write_bytes(proc.stdout);(run/'stderr.txt').write_bytes(proc.stderr)
lines=[s for s in proc.stdout.decode().splitlines() if s.startswith('{')]
result=json.loads(lines[-1]) if lines else {'result':'INCOMPLETE'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result.update(exit_code=proc.returncode,source_sha256={p.name:sha(p) for p in P.glob('checkpoint_load_dispatch_bridge*') if p.suffix in ('.h','.cpp','.asm','.py','.cmd')},binary_sha256=sha(P/'checkpoint_load_dispatch_bridge_fixture.exe'))
assert proc.returncode==0 and result['result']=='PASS',result
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'result':result['result'],'checks':result['checks'],'path':str(run/'result.json')}))
