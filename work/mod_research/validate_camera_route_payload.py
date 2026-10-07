import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
r=subprocess.run([str(ROOT/'camera_route_payload_fixture.exe')],capture_output=True,text=True,timeout=10)
assert r.returncode==0,(r.returncode,r.stderr)
data=[json.loads(x) for x in r.stdout.splitlines()]
assert len(data)==7
assert [x['event'] for x in data[:5]]==['tactic_dispatch','tactic_camera_decision','tactic_camera_decision','rng_update','combat_gate']
assert data[0]['tactic_record']['actor_id']==17
assert [x['scene_eligible'] for x in data[1:3]]==[1,0]
assert [x['camera']['level'] for x in data[1:3]]==[3,4]
assert data[3]['before']==1234 and data[3]['after']==5678 and data[3]['caller_rva']==0x3b3779
assert data[3]['camera']['linked_present'] and len(data[3]['camera']['linked_hex'])==0xb0*2
assert data[4]['stage']==12 and data[4]['states']==['CProgressState']
assert len(data[4]['armies'])==1 and data[4]['armies'][0][0]==17
assert all(x['result']=='PASS' for x in data[5:])
infra=json.loads((ROOT/'camera-route-fixtures.json').read_text())
assert len(infra)==3 and all(x['result']=='PASS' for x in infra)
report={'result':'PASS','observer_sha256':hashlib.sha256((ROOT/'observe_camera_route.exe').read_bytes()).hexdigest(),
    'payload_fixture_sha256':hashlib.sha256((ROOT/'camera_route_payload_fixture.exe').read_bytes()).hexdigest(),
    'scope':'Synthetic event snapshots, camera alternate route, native marker debugger infrastructure, timeout/cancel cleanup. Does not validate game semantics or zero timing interference.',
    'cases':[{k:v for k,v in x.items() if k not in ('camera','stack_hex','registers','armies')} for x in data], 'infrastructure':infra}
(ROOT/'camera-route-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','payload_rows':len(data),'infrastructure_cases':len(infra),'observer_sha256':report['observer_sha256']}))
