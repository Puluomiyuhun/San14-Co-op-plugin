"""Compare a read-only load-boundary mismatch record with the final map sample."""
from datetime import datetime
from pathlib import Path
import json
from start_startup_switch import ROOT,load,save,sha,no_debugger,JOURNAL,CHECKPOINT_SHA
from run_second_force_reward import BattleObserver,capture,CHECKPOINT
from startup_identity_reader import capture_startup_context
from analyze_startup_switch import compare_records
TABLES={0x148:'person',0xDAA8:'city',0xDE40:'district',0xDCA0:'force',0x7DF60:'army'}

def main():
    meta=load(ROOT/'startup-switch-active.json');assert meta['execute'] is False
    folder=Path(meta['directory']);rows=[json.loads(s) for s in (folder/'trace.jsonl').read_text().splitlines()]
    tail=rows[-1]
    assert tail in ({'event':'detached','captured':True,'registers_restored':True},
                    {'event':'error_cleanup','registers_restored':True,'detached':True})
    errors=[r for r in rows if r['event']=='error']
    assert not errors or errors==[{'event':'error','message':'checkpoint_sample_mismatch_no_write'}],errors
    assert not JOURNAL.exists() and not any(r['event']=='title_selection_written' for r in rows)
    samples=[r for r in rows if r['event']=='checkpoint_sample_comparison'];assert len(samples)==1
    sample=samples[0];assert sample['checked_records']==783 and sample['unreadable_records']==0
    reader=BattleObserver()
    try:
        no_debugger(reader);current=capture(reader);context=capture_startup_context(reader)
        assert current==capture(reader) and context==capture_startup_context(reader)
        assert context['snapshot']['player']['force_id']==12
        baseline=load(ROOT/'startup-identity-traces/20261006-110512-181614/after.json')
        comparisons=[]
        for item in sample['differences']:
            key=f"{TABLES[item['table_rva']]}:{item['id']}";expected=bytes.fromhex(baseline['records'][key]);now=bytes.fromhex(current['records'][key])
            changes=[]
            for byte in item['changes']:
                offset=byte['object_offset'];assert expected[offset-0x10]==byte['expected']
                changes.append({**byte,'object_offset_hex':hex(offset),'planning_value':now[offset-0x10],
                                'returned_to_expected_on_map':now[offset-0x10]==byte['expected']})
            comparisons.append({'object':key,'changes':changes})
        assert sha(CHECKPOINT)==CHECKPOINT_SHA
        save(folder/'after-diagnostic.json',current);save(folder/'context-after-diagnostic.json',context)
        result={'schema':'san14.startup-checkpoint-diagnostic.v1','created':datetime.now().astimezone().isoformat(),
                'result':'LOAD_BOUNDARY_DIFFERENCES_CAPTURED','directory':str(folder),'boundary_comparison':sample,
                'boundary_to_map_changes':comparisons,'planning_sample_comparison':compare_records(baseline,current),
                'current_context':context,'game_data_writes_by_adapter':0,'checkpoint34_unchanged':True,
                'debugger_attached':False,'scope':'Observes field changes between startup and planning; does not establish their meaning or authorize ignoring them.'}
        save(folder/'diagnostic.json',result);save(ROOT/'startup-checkpoint-diagnostic-latest.json',result)
        print(json.dumps({'result':result['result'],'different_records':sample['different_records'],
                          'different_bytes':sample['different_bytes'],'boundary_to_map_changes':comparisons},ensure_ascii=True,indent=2))
    finally:reader.close()

if __name__=='__main__':main()
