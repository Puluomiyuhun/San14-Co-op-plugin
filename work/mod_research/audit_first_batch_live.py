"""Compare the new complete first-batch trace to saved A/B/F evidence, offline."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from analyze_lockstep import baseline_difference
from analyze_first_batch import analyze
from analyze_battle_branches import decode_side, identity

ROOT=Path(__file__).resolve().parent
TRACES=ROOT/'lockstep-traces'
name=sys.argv[1]
assert name.replace('-','').isalnum()
folder=TRACES/name
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
rows=lambda p:[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
trace=rows(folder/'trace.jsonl')
classification=analyze(trace)
assert classification['status']=='COMPLETE'
gate=classification['selected_gate'];boundary=classification['boundary'];ready=classification['build_return']
decisions=[r for r in trace if r['event']=='pair_eligibility']
damage=[r for r in trace if r['event']=='casualty_request']
damage_keys=('source_kind','source_id','target_kind','target_id','amount','caller_rva')
ordered_damage=[{k:r[k] for k in damage_keys} for r in damage]
assert ready and ready['pair_count']==len(ready['pairs'])==len(decisions)
assert [identity(r['pair']) for r in decisions]==[identity(p) for p in ready['pairs']]

def objects_diff(a,b):
    x,y=dict(a),dict(b)
    differences=[]
    for key in sorted(x.keys()|y.keys()):
        if x.get(key)==y.get(key):continue
        if key not in x or key not in y:
            differences.append({'id':key,'membership_changed':True});continue
        aa,bb=bytes.fromhex(x[key]),bytes.fromhex(y[key])
        differences.append({'id':key,'byte_changes':[{'offset':hex(i+0x10),'a':v,'b':w} for i,(v,w) in enumerate(zip(aa,bb)) if v!=w],
                            'lengths':[len(aa),len(bb)]})
    return differences

historical={}
for old in ('run-a','run-b'):
    oldtrace=rows(TRACES/old/'trace.jsonl')
    stages=[r for r in oldtrace if r['event']=='stage']
    a,b=stages[167],stages[168]
    assert (a['stage'],b['stage'],a['date'],b['date'])==(12,13,[203,8,11],[203,8,11])
    requests=[{k:r[k] for k in damage_keys} for r in oldtrace if r['event']=='casualty_request' and a['seq']<r['seq']<b['seq']]
    historical[old]={'before_army_record_differences':objects_diff(a['armies'],gate['armies']),
                     'after_army_record_differences':objects_diff(b['armies'],boundary['armies']),
                     'ordered_damage_requests_equal':requests==ordered_damage,'old_request_count':len(requests),
                     'first_batch_rng_old':a['global_rng'],'first_batch_rng_new':gate['global_rng']}

ftrace=rows(TRACES/'branch-run-f/trace.jsonl')
fready=next(r for r in ftrace if r['event']=='pairs_ready')
fdecisions=[r for r in ftrace if r['event']=='pair_eligibility' and r['date']==[203,8,11] and r['subday']==10]
raw_changes=[]
for i,(a,b) in enumerate(zip(fready['pairs'],ready['pairs'])):
    for side in ('a','b'):
        aa,bb=bytes.fromhex(a[side]),bytes.fromhex(b[side])
        if aa!=bb:
            raw_changes.append({'pair_index':i,'side':side,'bytes':[{'offset':hex(n),'f':u,'new':v} for n,(u,v) in enumerate(zip(aa,bb)) if u!=v]})
f_comparison={'count_equal':len(fready['pairs'])==len(ready['pairs']),
              'decoded_pair_records_equal':[[decode_side(p[s]) for s in ('a','b')] for p in fready['pairs']]==[[decode_side(p[s]) for s in ('a','b')] for p in ready['pairs']],
              'identity_order_equal':[identity(p) for p in fready['pairs']]==[identity(p) for p in ready['pairs']],
              'eligibility_order_equal':[(identity(r['pair']),r['eligibility_before_special_filter']) for r in fdecisions]==[(identity(r['pair']),r['eligibility_before_special_filter']) for r in decisions],
              'raw_side_records_equal':not raw_changes,'raw_side_record_changes':raw_changes,
              'unknown_bytes_policy':'Retained as differences; decoded equality is not raw or full-state equality.'}

troop_changes=[]
start,end=dict(gate['armies']),dict(boundary['armies'])
u16=lambda raw,off:int.from_bytes(bytes.fromhex(raw)[off-0x10:off-0x10+2],'little')
for army in sorted(start.keys()&end.keys()):
    old=(u16(start[army],0x16),u16(start[army],0x18))
    new=(u16(end[army],0x16),u16(end[army],0x18))
    if old!=new:troop_changes.append({'army_id':army,'soldiers_before':old[0],'soldiers_after':new[0],
                                    'wounded_before':old[1],'wounded_after':new[1]})
rejected=[]
for r in decisions:
    if r['eligibility_before_special_filter']:continue
    a,b=identity(r['pair'])
    prior=[{**{k:d[k] for k in damage_keys},'seq':d['seq']} for d in damage
           if d['seq']<r['seq'] and (d['target_kind'],d['target_id'])==a]
    rejected.append({'identity':identity(r['pair']),'seq':r['seq'],'resolved_forces':r['resolved_forces'],
                     'prior_requests_targeting_attacker':prior,
                     'attacker_soldiers_before':u16(start[a[1]],0x16) if a[0]==27 and a[1] in start else None,
                     'attacker_soldiers_at_boundary':u16(end[a[1]],0x16) if a[0]==27 and a[1] in end else None,
                     'scope':'Temporal and boundary evidence; individual prefilter subpredicates are not separately traced.'})

end_sample=load(folder/'end.json')
end_comparisons={old:baseline_difference(load(TRACES/path),end_sample) for old,path in
                 [('b','after-run-b.json'),('f','branch-run-f/after.json'),('n','rng-pairs-live-n/end.json')]}
before=load(folder/'before.json')
before_branch=load(folder/'before-branch-inputs.json')
oldforces=[{'id':x['id'],'field_12':x['field_12'],'field_194':x['field_194'],'relations':x['field_ea_11d_hex']} for x in before_branch['forces']]
new_fields={'force_fields_planning_gate_ready_boundary_equal':oldforces==gate['forces']==ready['forces']==boundary['forces'],
            'force_12_nonzero_at_gate':[{k:f[k] for k in ('id','field_12')} for f in gate['forces'] if f['field_12']],
            'force_194_nonzero_at_gate':[{k:f[k] for k in ('id','field_194')} for f in gate['forces'] if f['field_194']],
            'nonzero_relation_bytes_at_gate':sum(sum(v!=0 for v in bytes.fromhex(f['relations'])) for f in gate['forces']),
            'input_list_counts':{k:[{'root_offset':hex(r['root_offset']),'count':r['count']} for r in v['input_lists']] for k,v in [('gate',gate),('ready',ready),('boundary',boundary)]},
            'input_lists':{k:v['input_lists'] for k,v in [('gate',gate),('ready',ready),('boundary',boundary)]}}
report={'schema':'san14.first-batch-live-comparison.v1','created':datetime.now().astimezone().isoformat(),'trial':name,
        'counts':dict(Counter(r['event'] for r in trace)),'classification':classification['branch'],
        'gate_sequence':[{'subday':r['subday'],'rsi_substep':r['rsi_substep'],'rbp_gate':r['rbp_gate']} for r in trace if r['event']=='combat_gate'],
        'ordered_pair_visits_match_rebuilt_list':True,
        'scheduled_gate_to_boundary_elapsed_tick_ms':boundary['tick_ms']-gate['tick_ms'],
        'observer_game_code_or_data_writes':False,'observer_timing_effects_absent_proven':False,
        'historical_comparisons':historical,'F_pair_comparison':f_comparison,
        'ordered_damage_requests':ordered_damage,'troop_changes':troop_changes,'rejected_pairs':rejected,
        'new_field_coverage':new_fields,'end_comparisons':end_comparisons,
        'start_rng':before['random_inputs'],'observed_gate_rng':[r['global_rng'] for r in trace if r['event']=='combat_gate'],
        'complete_world_equality_proven':False,'original_A_root_cause_proven':False,
        'limits':['Only the first scheduled batch is traced; remaining turn has endpoint snapshot only.',
                  'RNG at planning and combat differs from original A/B; not a matched-start lockstep trial.',
                  'A had no corresponding gate, list or force-relation capture, so current values cannot explain it retrospectively.'],
        'trace_sha256':hashlib.sha256((folder/'trace.jsonl').read_bytes()).hexdigest()}
with (folder/'comparative-audit.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({'counts':report['counts'],'historical':{k:{x:y for x,y in v.items() if not x.endswith('record_differences')} for k,v in historical.items()},
                  'army_differences_vs_b':{k:len(v) for k,v in historical['run-b'].items() if k.endswith('record_differences')},
                  'F_pairs':{k:v for k,v in f_comparison.items() if k!='raw_side_record_changes'},
                  'rejected':rejected,'troop_changes':troop_changes,
                  'end_comparisons':{k:{'sample_changes':len(v['sampled_record_changes_excluding_known_runtime_pointer']),
                                         'focused_equal':v['focused_state_equal'],'tasks_equal':v['person_task_sample_equal'],'rng_equal':v['random_inputs_equal']} for k,v in end_comparisons.items()},
                  'new_fields':{k:v for k,v in new_fields.items() if k!='input_lists'}},ensure_ascii=True))
