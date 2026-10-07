"""Close only a sample-check rejection that occurred before any write intent."""
from datetime import datetime
from pathlib import Path
import json
from start_startup_switch import ROOT,load,save,sha,no_debugger,JOURNAL,CHECKPOINT_SHA
from run_second_force_reward import BattleObserver,capture,CHECKPOINT
from startup_identity_reader import capture_startup_context
from analyze_startup_switch import compare_records
meta=load(ROOT/'startup-switch-active.json');folder=Path(meta['directory'])
rows=[json.loads(s) for s in (folder/'trace.jsonl').read_text().splitlines()]
assert rows[-2:]==[{'event':'error','message':'checkpoint_sample_mismatch_no_write'},
                  {'event':'error_cleanup','registers_restored':True,'detached':True}]
assert not JOURNAL.exists()
assert [r['event'] for r in rows]==['attached','armed','deserialize_return','load_worker_result','title_selection_boundary','error','error_cleanup']
assert rows[4]['handoff_written'] is False
assert sha(folder/'artifacts/startup_identity_switch.exe')==meta['binary_sha256']
reader=BattleObserver()
try:
    no_debugger(reader);current=capture(reader);context=capture_startup_context(reader)
    assert current==capture(reader) and context==capture_startup_context(reader)
    assert reader.pointer(reader.memory.base+0x12CC4A8+0x28)==reader.memory.base+0x3F9B00
    baseline=load(ROOT/'startup-identity-traces/20261006-110512-181614/after.json')
    comparison=compare_records(baseline,current)
    assert sha(CHECKPOINT)==CHECKPOINT_SHA
    assert context['snapshot']['player']['force_id']==12 and context['snapshot']['player']['ruler_id']==666
    save(folder/'after-rejection.json',current);save(folder/'context-after-rejection.json',context)
    result={'schema':'san14.startup-switch-rejection.v1','created':datetime.now().astimezone().isoformat(),
        'result':'REJECTED_AT_SAMPLE_GUARD_BEFORE_WRITE','directory':str(folder),'trace':rows,
        'current_context':context,'planning_sample_comparison':comparison,
        'execution_intent_created':False,'adapter_game_data_writes':0,'debugger_attached':False,
        'original_user_update_unchanged':True,'checkpoint34_unchanged':True,
        'mismatching_load_boundary_field_recorded':False,
        'scope':'Date/player/title/ownership/load-order guards passed; partial record comparison rejected before write. This trace lacks per-field mismatch details; cannot retrospectively identify the transient field.'}
    save(folder/'rejection.json',result);save(ROOT/'startup-switch-rejection-latest.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('trace','current_context')},ensure_ascii=True,indent=2))
finally:reader.close()
