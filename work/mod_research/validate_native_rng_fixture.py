import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=subprocess.run([str(ROOT/'native_rng_isolation_fixture.exe')],capture_output=True,text=True,timeout=20)
assert p.returncode==0,(p.returncode,p.stderr)
rows=[json.loads(x) for x in p.stdout.splitlines()]
assert len(rows)==10 and all(r['result']=='PASS' for r in rows)
assert rows[0]['checks']==144
cross=next(r for r in rows if r['case']=='two-client-synthetic-draw-schedule')
assert cross['logical_hash_a']==cross['logical_hash_b'] and cross['shared_stream_divergent_outputs']>0
report={'result':'PASS','fixture_sha256':hashlib.sha256((ROOT/'native_rng_isolation_fixture.exe').read_bytes()).hexdigest(),
 'source':json.loads((ROOT/'native-rng-fixture-source.json').read_text(encoding='utf-8')),'cases':rows,
 'scope':'Private executable uses relocated SAN14 native leaf RNG instructions. Tests state transitions and domain isolation, not game battlefield, hook correctness, queue draining or a complete RNG inventory.',
 'limits':['The 600-draw schedule is synthetic; the 144-state replay uses captured states, not all historical input arguments or return values.',
 'Concurrency test has one logical draw stream and two presentation workers. A mutex alone does not give deterministic ordering between multiple logical workers.',
 'Scope cleanup tested for C++ exception, not Windows structured exceptions or propagation to asynchronous game jobs.',
 'Game/presentation classification is supplied by the fixture; the correct production hook scope is not proven.']}
(ROOT/'native-rng-isolation-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','case_count':len(rows),'cases':rows,'fixture_sha256':report['fixture_sha256']}))
