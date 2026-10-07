"""Verify one real load-time handoff without claiming full UI/multiplayer support."""
from datetime import datetime
import json
from pathlib import Path
from run_second_force_reward import BattleObserver,capture,CHECKPOINT
from startup_identity_reader import capture_startup_context
from start_startup_switch import ROOT,load,save,sha,no_debugger,CHECKPOINT_SHA

def validate_trace(rows):
    if not rows or rows[-1]!={'event':'detached','captured':True,'registers_restored':True}:
        raise ValueError('Handoff recorder has not cleanly detached')
    if any(r.get('event') in ('error','error_cleanup','process_exit') for r in rows):
        raise ValueError('Recorder reported an error; inspect trace and reserved attempt before recovery')
    names=('deserialize_return','load_worker_result','title_selection_boundary','title_selection_written',
           'native_identity_initializer','native_identity_return','strategy_initialize','user_strategy_initialize',
           'first_user_update','target_user_state_observed')
    diagnostics=[r for r in rows if r.get('event')=='checkpoint_sample_comparison']
    if diagnostics and (len(diagnostics)!=1 or diagnostics[0].get('checked_records')!=783 or
        diagnostics[0].get('different_records')!=0 or diagnostics[0].get('different_bytes')!=0 or
        diagnostics[0].get('unreadable_records')!=0 or diagnostics[0].get('differences')):
        raise ValueError('Checkpoint sample guard did not pass')
    events=[r for r in rows if r.get('event') not in ('attached','armed','detached','checkpoint_sample_comparison')]
    if [r.get('event') for r in events]!=list(names):raise ValueError('Missing, duplicate, or out-of-order startup stage')
    p=dict(zip(names,events))
    seq=[r['seq'] for r in events if 'seq' in r]
    if seq!=list(range(1,9)):raise ValueError('Trace sequence is not contiguous')
    if p['load_worker_result']['ebx']!=1:raise ValueError('Load worker failed')
    for name in ('deserialize_return','load_worker_result','title_selection_boundary','native_identity_initializer'):
        if p[name]['world_context']['force']!=12:raise ValueError('Source identity differs before native initializer')
    wrote=p['title_selection_written']
    if not (wrote['adapter_written_bytes']==16 and wrote['source_force']==12 and wrote['target_force']==2 and
            wrote['source_ruler']==666 and wrote['target_ruler']==952 and wrote['world_identity_written_by_adapter'] is False):
        raise ValueError('Wrong write scope')
    native=p['native_identity_initializer'];witness=native.get('native_handoff_context')
    if native['initializer_person_id']!=952 or native.get('initializer_return_rva')!=0x4DA3BE or not witness:
        raise ValueError('Wrong native initializer argument/caller')
    if not (witness['selected_force_id']==2 and witness['selected_person_id']==witness['force_ruler_id']==952
            and witness['argument_matches_title_person'] is True and witness['selected_pair_matches'] is True):
        raise ValueError('Title selection and native argument disagree')
    for name in ('native_identity_return','strategy_initialize','user_strategy_initialize','first_user_update'):
        if p[name]['world_context']['force']!=2 or p[name]['world_context']['rank_derived_count']!=1:
            raise ValueError('Target identity not preserved after native initialization')
    for row in events:
        if 'seq' in row and row.get('date')!=[203,8,11]:raise ValueError('Date changed during startup')
    end=p['first_user_update'];state=end['state_context'];marker=p['target_user_state_observed']
    if not (end['complete_path_seen'] is True and state['field_470_raw']==2 and state['field_478_raw'] and state['field_618_raw']):
        raise ValueError('Constructed target user state not observed')
    if marker['force']!=2 or marker['native_gameplay_enabled'] is not False:raise ValueError('Invalid completion marker')
    return {'ordered_points':p,'visual_menu_verification_pending':True,'native_gameplay_enabled':False}

def compare_records(before,after):
    if before['records'].keys()!=after['records'].keys():raise ValueError('Sampled membership changed')
    runtime=[];other=[]
    for key,hx in before['records'].items():
        a,b=bytes.fromhex(hx),bytes.fromhex(after['records'][key])
        if len(a)!=len(b):raise ValueError('Record length changed')
        changed=[i+0x10 for i,(x,y) in enumerate(zip(a,b)) if x!=y]
        if not changed:continue
        row={'object':key,'offsets':[hex(i) for i in changed]}
        if key.startswith('army:') and all(0x148<=i<0x150 for i in changed):runtime.append(row)
        else:other.append(row)
    return {'sampled_records':len(before['records']),'runtime_pointer_changes':runtime,'other_record_changes':other,
            'active_army_semantics_equal':before['focused']['all_active_units']==after['focused']['all_active_units'],
            'task_fields_equal':before['eligibility']['task_fields_sha256']==after['eligibility']['task_fields_sha256'],
            'scope':before['record_scope']}

def main():
    meta=load(ROOT/'startup-switch-active.json');folder=Path(meta['directory'])
    rows=[json.loads(s) for s in (folder/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
    trace=validate_trace(rows);reader=BattleObserver()
    try:
        no_debugger(reader);after=capture(reader);ctx=capture_startup_context(reader)
        assert after==capture(reader) and ctx==capture_startup_context(reader),'State not stable'
        assert ctx['snapshot']['player']['force_id']==2 and ctx['snapshot']['player']['ruler_id']==952
        assert reader.pointer(reader.memory.base+0x12CC4A8+0x28)==reader.memory.base+0x3F9B00
        before=load(folder/'before.json');comparison=compare_records(before,after)
        save(folder/'after.json',after);save(folder/'context-after.json',ctx)
        # Preserve unexpected effects as evidence, never silently normalize them.
        sample_ok=not comparison['other_record_changes'] and comparison['active_army_semantics_equal'] and comparison['task_fields_equal']
        assert sha(CHECKPOINT)==CHECKPOINT_SHA
        report={'schema':'san14.startup-switch-result.v1','created':datetime.now().astimezone().isoformat(),
                'result':'TARGET_NATIVE_USER_STATE_REACHED' if sample_ok else 'TARGET_REACHED_WITH_UNEXPLAINED_SAMPLE_CHANGES',
                'trace':trace,'comparison':comparison,'current_context':ctx,'directory':str(folder),
                'sampled_gameplay_matches_checkpoint':sample_ok,'checkpoint34_unchanged':True,'debugger_attached':False,
                'original_user_update_unchanged':True,'known_rng_before':before['global_rng'],'known_rng_after':after['global_rng'],
                'pool_samples_before':before['pools'],'pool_samples_after':after['pools'],
                'local_identity_expected_difference':{'force':[12,2],'ruler':[666,952],'rank_derived_count':[2,1]},
                'b_visual_menu_verified':False,'two_real_clients_verified':False,'ai_human_protection_installed':False,
                'native_gameplay_enabled':False,'restore34_required_after_ui_observation':True,'automatic_retry_allowed':False,
                'scope':'One live process at a single checkpoint. UI objects plus sampled state, not full native menu/event/AI or deterministic simulation proof.'}
        save(folder/'result.json',report);save(ROOT/'startup-switch-live-result.json',report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('trace','comparison','current_context')},ensure_ascii=True,indent=2))
    finally:reader.close()

if __name__=='__main__':main()
