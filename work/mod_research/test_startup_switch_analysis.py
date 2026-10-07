"""Synthetic trace rejection checks; not evidence of a real identity switch."""
from copy import deepcopy
import json
from analyze_startup_switch import validate_trace,compare_records
from start_startup_switch import ROOT,load,save
old=load(ROOT/'startup-identity-live-result.json')['analysis']
p=old['ordered_points'];native=deepcopy(old['identity_initializer_events'][0])
boundary=deepcopy(native);boundary['event']='title_selection_boundary';boundary.pop('initializer_person_id')
native['initializer_person_id']=952;native['initializer_return_rva']=0x4DA3BE
native['native_handoff_context']={'title_phase_raw':15,'selected_force_id':2,'selected_person_id':952,'force_ruler_id':952,
                                'argument_matches_title_person':True,'selected_pair_matches':True}
returned=deepcopy(native);returned['event']='native_identity_return'
ordered=[deepcopy(p['deserialize_return']),deepcopy(p['load_worker_result']),boundary,native,returned,
         deepcopy(p['strategy_initialize']),deepcopy(p['user_strategy_initialize']),deepcopy(p['first_user_update'])]
for i,row in enumerate(ordered,1):
    row['seq']=i
    if i>=5:row['world_context']['force']=2;row['world_context']['rank_derived_count']=1
rows=ordered[:3]+[{'event':'title_selection_written','adapter_written_bytes':16,'source_force':12,'target_force':2,
                  'source_ruler':666,'target_ruler':952,'world_identity_written_by_adapter':False}]+ordered[3:]+[
                  {'event':'target_user_state_observed','force':2,'native_gameplay_enabled':False},
                  {'event':'detached','captured':True,'registers_restored':True}]
assert validate_trace(rows)['native_gameplay_enabled'] is False
results=[{'case':'ordered_synthetic_success','result':'PASS'}]
cases=[]
with_diagnostic=deepcopy(rows)
with_diagnostic.insert(3,{'event':'checkpoint_sample_comparison','checked_records':783,'different_records':0,
                         'different_bytes':0,'unreadable_records':0,'differences':[]})
assert validate_trace(with_diagnostic)['native_gameplay_enabled'] is False
results.append({'case':'complete_zero_difference_diagnostic','result':'PASS'})
for key in ('different_records','different_bytes','unreadable_records'):
    bad=deepcopy(with_diagnostic);bad[3][key]=1;cases.append((f'failed_sample_guard_{key}',bad))
def change(name,index,key,value):
    r=deepcopy(rows);target=r[index]
    for k in key[:-1]:target=target[k]
    target[key[-1]]=value;cases.append((name,r))
change('cleanup_failed',-1,['registers_restored'],False)
change('sequence_gap',4,['seq'],17)
change('worker_failed',1,['ebx'],0)
change('source_changed_too_early',2,['world_context','force'],2)
change('excess_write',3,['adapter_written_bytes'],17)
change('world_byte_patch',3,['world_identity_written_by_adapter'],True)
change('wrong_native_ruler',4,['initializer_person_id'],666)
change('wrong_native_caller',4,['initializer_return_rva'],0x4DA3BF)
change('title_person_mismatch',4,['native_handoff_context','argument_matches_title_person'],False)
change('late_identity_overwrite',7,['world_context','force'],12)
change('rank_not_updated',5,['world_context','rank_derived_count'],2)
change('date_advanced',8,['date'],[203,8,21])
change('ui_missing',8,['state_context','field_478_raw'],0)
change('phase_not_ready',8,['state_context','field_470_raw'],0)
change('completion_not_proven',8,['complete_path_seen'],False)
r=deepcopy(rows);r.insert(-1,{'event':'error','message':'synthetic'});cases.append(('recorder_error',r))
r=deepcopy(rows);r[4],r[5]=r[5],r[4];cases.append(('wrong_stage_order',r))
for name,r in cases:
    try:validate_trace(r)
    except ValueError:results.append({'case':name,'result':'PASS'})
    else:raise AssertionError(name)
source=load(ROOT/'startup-identity-active.json');folder=ROOT/'startup-identity-traces'/__import__('pathlib').Path(source['directory']).name
before=load(folder/'before.json');after=load(folder/'after.json')
comparison=compare_records(before,after);assert not comparison['other_record_changes']
changed=deepcopy(after);value=bytearray.fromhex(changed['records']['city:13']);value[0x24]^=1;changed['records']['city:13']=value.hex()
assert compare_records(before,changed)['other_record_changes'][0]['object']=='city:13'
result={'result':'PASS','trace_cases':results,'sample_comparison_cases':2,'scope':'Synthetic trace parser cases and saved sample classification only.'}
save(ROOT/'startup-switch-analysis-tests.json',result)
print(json.dumps({'result':'PASS','trace_cases':len(results),'sample_comparison_cases':2}))
