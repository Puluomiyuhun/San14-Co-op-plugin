import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=subprocess.run([str(ROOT/'camera_rng_watch_payload_fixture.exe')],capture_output=True,text=True,timeout=10)
assert p.returncode==0,(p.returncode,p.stderr)
rows=[json.loads(x) for x in p.stdout.splitlines()]
assert len(rows)==11
assert [r['event'] for r in rows[:5]]==['tactic_dispatch','tactic_camera_decision','tactic_camera_decision','rng_write','combat_gate']
assert rows[0]['tactic_record']['actor_id']==17
assert [r['scene_eligible'] for r in rows[1:3]]==[1,0]
assert rows[4]['stage']==12 and len(rows[4]['armies'])==1
assert rows[3]['camera']['linked_present'] and len(rows[3]['camera']['linked_hex'])==352
writes=[r for r in rows if r['event']=='rng_write']
assert [(r['previous_observed'],r['observed_after']) for r in writes]==[(1234,5678),(5678,5679),(5679,5680),(5680,5681),(5681,5682)]
assert [r['rip_after_rva'] for r in writes]==[0x3aa80b,0x3aa3db,0x3aa441,0x3aa3e6,0x101010]
assert all(r['global_rng']==r['observed_after'] for r in writes)
assert all(len(r['stack_hex'])==4096 for r in writes)
assert all(r['result']=='PASS' for r in rows[-2:])
infra=json.loads((ROOT/'camera-rng-watch-fixtures.json').read_text(encoding='utf-8'))
assert len(infra)==3 and all(r['result']=='PASS' for r in infra)
report={'result':'PASS','observer_sha256':hashlib.sha256((ROOT/'observe_camera_rng_watch.exe').read_bytes()).hexdigest(),
 'payload_rows':len(rows),'write_origins_tested':len(writes),'infrastructure':infra,
 'scope':'Actual hardware watch: full/same/byte/halfword/overlapping eight-byte writes and newly created thread; timeout/cancel cleanup. Synthetic camera/gate payload and post-store RIP. Does not certify game determinism or absence of timing interference.',
 'limits':'previous_observed is the last captured value, not a guaranteed atomic pre-write value if multiple threads race. caller_rva is only a stack-top candidate for unfamiliar non-leaf writers; unwind required.'}
(ROOT/'camera-rng-watch-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('result','observer_sha256','payload_rows','write_origins_tested')}))
