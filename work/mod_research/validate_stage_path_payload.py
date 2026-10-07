from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
data=[json.loads(x) for x in (ROOT/'stage-path-payload-fixture.jsonl').read_text().splitlines()]
assert len(data)==12
assert [r['event'] for r in data]==['stage','battle_entry','pairs_ready']+['pair_phase']*7+['stage']*2
assert data[0]['subday']==10 and data[0]['rbp']==1 and data[0]['rsi']==5
assert data[0]['frame_start_ms']==1234 and data[0]['budget_elapsed_ms']==3
assert [r[0] for r in data[0]['armies']]==[1,2]
assert len(data[0]['cities'])==len(data[0]['forces'])==52
assert data[0]['input_lists'][0]['entries']==[1,2]
assert data[0]['input_lists'][4]['entries'][0]['army_members']==[2,1,2]
assert data[1]['caller_rva']==0x3F935A
assert data[2]['eax']==1 and data[2]['pair_count']==len(data[2]['pairs'])==1
assert [r['phase'] for r in data[3:10]]==list(range(1,8))
assert data[-1]['stage']==0 and data[-1]['subday']==12
fixtures=json.loads((ROOT/'stage-path-fixtures.json').read_text())
assert len(fixtures)==3 and all(r['result']=='PASS' for r in fixtures)
report={'result':'PASS','payload_scope':'Local synthetic map; all four observation payload paths, stopping boundary and three malformed-list rejections. Not a native combat test.',
    'observer_sha256':hashlib.sha256((ROOT/'observe_stage_path.exe').read_bytes()).hexdigest(),
    'payload_fixture_sha256':hashlib.sha256((ROOT/'stage_path_payload_fixture.exe').read_bytes()).hexdigest(),
    'parsed_payload_rows':len(data),'infrastructure':fixtures}
(ROOT/'stage-path-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
