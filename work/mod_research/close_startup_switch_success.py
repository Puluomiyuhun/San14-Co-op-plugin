"""Read-only confirmation of native load34 recovery after the identity pilot."""
from datetime import datetime
import json
from pathlib import Path
from start_startup_switch import ROOT,load,save,sha,no_debugger,JOURNAL,CHECKPOINT_SHA
from run_second_force_reward import BattleObserver,capture,CHECKPOINT
from startup_identity_reader import capture_startup_context
from analyze_startup_switch import compare_records,validate_trace

def main():
    meta=load(ROOT/'startup-switch-active.json');folder=Path(meta['directory'])
    rows=[json.loads(s) for s in (folder/'trace.jsonl').read_text().splitlines()];validate_trace(rows)
    assert sha(folder/'artifacts/startup_identity_switch.exe')==meta['binary_sha256']
    journal_sha=sha(JOURNAL);reader=BattleObserver()
    try:
        no_debugger(reader);current=capture(reader);context=capture_startup_context(reader)
        assert current==capture(reader) and context==capture_startup_context(reader),'Recovery sample changing'
        assert reader.pointer(reader.memory.base+0x12CC4A8+0x28)==reader.memory.base+0x3F9B00
        assert context['snapshot']['player']['force_id']==12 and context['snapshot']['player']['ruler_id']==666
        assert context['snapshot']['date']=={'year':203,'month':8,'day':11,'period':'中旬'}
        assert context['snapshot']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
        assert context['state_sample']['phase_raw']==2
        comparison=compare_records(load(folder/'before.json'),current)
        assert sha(CHECKPOINT)==CHECKPOINT_SHA and sha(JOURNAL)==journal_sha
        matches=not comparison['other_record_changes'] and comparison['active_army_semantics_equal'] and comparison['task_fields_equal']
        save(folder/'restored34.json',current);save(folder/'context-restored34.json',context)
        result={'schema':'san14.startup-switch-recovery.v1','created':datetime.now().astimezone().isoformat(),
                'result':'RESTORED_ZHANG_LU_CHECKPOINT_SAMPLE' if matches else 'RESTORED_IDENTITY_SAMPLE_CHANGES_RETAINED',
                'directory':str(folder),'current_context':context,'comparison':comparison,
                'checkpoint34_unchanged':True,'execution_journal_preserved':True,'execution_journal_sha256':journal_sha,
                'debugger_attached':False,'original_user_update_unchanged':True,'recovery_game_writes_by_tool':0,
                'known_rng_before':load(folder/'before.json')['global_rng'],'known_rng_restored':current['global_rng'],
                'all_shared_state_proven_restored':False,'automatic_retry_allowed':False,
                'scope':'Identity, planning phase, file integrity and sampled business state after user native load. Not full world/RNG equivalence.'}
        save(folder/'recovery.json',result);save(ROOT/'startup-switch-recovery.json',result)
        print(json.dumps({'result':result['result'],'player':context['snapshot']['player'],
                          'other_record_changes':comparison['other_record_changes'],
                          'army_semantics_equal':comparison['active_army_semantics_equal'],'task_fields_equal':comparison['task_fields_equal'],
                          'checkpoint34_unchanged':True,'debugger_attached':False,'execution_journal_preserved':True},ensure_ascii=False))
    finally:reader.close()

if __name__=='__main__':main()
