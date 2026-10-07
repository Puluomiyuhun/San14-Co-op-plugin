"""Check decoded fields and both adaptive transitions against synthetic memory."""
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
log=ROOT/'startup-identity-payload.jsonl'
p=subprocess.run([str(ROOT/'startup_identity_payload_fixture.exe'),str(log)],capture_output=True,text=True,timeout=10,
                 creationflags=subprocess.CREATE_NO_WINDOW)
assert p.returncode==0,(p.stdout,p.stderr)
result=json.loads(p.stdout)
rows=[json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
assert [r['event'] for r in rows[:7]]==['deserialize_return','load_worker_result','native_identity_initializer',
        'strategy_initialize','user_strategy_initialize','first_user_update','first_user_update']
assert [r['point_epoch'] for r in rows[:7]]==[1,2,2,2,2,2,2]
assert rows[2]['initializer_person_id']==952
assert rows[2]['initializer_return_rva']==0x4DA3BE
assert rows[2]['native_handoff_context']=={'title_phase_raw':15,'selected_force_id':2,'selected_person_id':952,
    'force_ruler_id':952,'argument_matches_title_person':True,'selected_pair_matches':True}
assert rows[3]['strategy_context']['field_470_raw']==0 and 'state_context' not in rows[3]
assert rows[4]['state_context']['field_478_raw']==0
assert rows[5]['state_context']['field_470_raw']==2 and rows[5]['state_context']['field_478_raw']==0x123000
assert rows[5]['state_context']['field_618_raw']==0x124000
assert rows[5]['complete_path_seen'] and not rows[6]['complete_path_seen']
assert rows[6]['date'] is None and 'world_context' not in rows[6] and 'state_context' not in rows[6]
assert all(r['world_context']['force']==12 and r['world_context']['cached_force']==12 and
           r['world_context']['rank_derived_count']==2 and r['world_context']['global_rng']==123 for r in rows[:6])
assert all(len(r['world_context']['rank_arrays_hex'])==60 for r in rows[:6])
assert len(rows)==12 and all(r['event']=='native_identity_initializer' for r in rows[7:])
assert rows[7]['initializer_return_rva']==0x4DA3BF and rows[7]['native_handoff_context'] is None
assert rows[8]['native_handoff_context'] is None
assert rows[9]['initializer_person_id'] is None and rows[9]['native_handoff_context']['argument_matches_title_person'] is False
assert rows[10]['native_handoff_context']['selected_pair_matches'] is False
assert rows[11]['initializer_return_rva'] is None and rows[11]['native_handoff_context'] is None
(ROOT/'startup-identity-payload-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
