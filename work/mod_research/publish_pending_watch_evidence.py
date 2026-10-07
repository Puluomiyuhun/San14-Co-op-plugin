"""Publish negative evidence without turning it into a universal exclusion."""
from datetime import datetime
import hashlib,json
from pathlib import Path
from analyze_lockstep import baseline_difference
ROOT=Path(__file__).resolve().parent
TRACES=ROOT/'lockstep-traces';RUN=TRACES/'pending-run-g';OUT=ROOT.parents[1]/'outputs/san14-link'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
a=load(RUN/'pending-analysis.json');ends=load(RUN/'end-comparisons.json');close=load(TRACES/'pending-g-closeout.json')
fixtures=load(ROOT/'pending-watch-fixtures.json')
assert a['capture_complete'] and not a['observation_chain_gaps']
assert len(a['writes'])==2 and all(r['slot']==0 and r['previous_observed']==r['observed_after']==0 for r in a['writes'])
assert all(r['writer']['verified'] and r['writer']['rva']=='0x16c6a7' for r in a['writes'])
assert all([f['pc_rva'] for f in r['unwind']['frames'][:2]]==['0x16c6ad','0x3f935a'] for r in a['writes'])
assert not a['writes_before_first_scheduled_combat']
assert len(a['load_markers'])==1 and a['load_markers'][0]['setter_value']==4136155758
assert len(a['save_markers'])==1 and a['save_markers'][0]['setter_value']==a['save_markers'][0]['global_rng']==1138287528
assert len(a['gate_comparisons_with_f'])==19 and all(set(c['different_fields'])<= {'global_rng'} for c in a['gate_comparisons_with_f'])
assert len(fixtures)==3 and all(x['result']=='PASS' for x in fixtures)
for name,r in ends.items():
    if name=='after-run-a.json':assert len(r['sampled_record_changes_excluding_known_runtime_pointer'])==25;continue
    assert not r['sampled_record_changes_excluding_known_runtime_pointer'] and r['focused_state_equal'] and r['person_task_sample_equal']
assert not close['debugger_attached'] and close['original_strategy_update_restored']
assert close['save34_sha256']==close['backup_sha256']=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
restored=load(RUN/'restored.json');before=load(RUN/'before.json')
restoration=baseline_difference(before,restored)
assert not restoration['sampled_record_changes_excluding_known_runtime_pointer']
assert all(restoration[k] for k in ('focused_state_equal','person_task_sample_equal','random_inputs_equal'))
aux_before=load(RUN/'before-branch-inputs.json');aux_after=load(RUN/'restored-branch-inputs.json')
nonpair_changes=[k for k in aux_before if k!='pairs' and aux_before[k]!=aux_after[k]]
pair_identity=lambda p:[[p[s]['type'],p[s]['id']] for s in ('a','b')]
decoded_equal=lambda p,q:all({k:v for k,v in p[s].items() if k!='record_00_18_hex'}=={k:v for k,v in q[s].items() if k!='record_00_18_hex'} for s in ('a','b'))
raw_diffs=[]
for left,right in zip(aux_before['pairs'],aux_after['pairs']):
    for side in ('a','b'):
        x=bytes.fromhex(left[side]['record_00_18_hex']);y=bytes.fromhex(right[side]['record_00_18_hex'])
        changes=[{'offset':hex(i),'before':u,'after':v} for i,(u,v) in enumerate(zip(x,y)) if u!=v]
        if changes:raw_diffs.append({'pair':pair_identity(left),'side':side,'changes':changes})
aux={'nonpair_changes':nonpair_changes,'identity_order_equal':[pair_identity(p) for p in aux_before['pairs']]==[pair_identity(p) for p in aux_after['pairs']],
     'decoded_fields_equal':len(aux_before['pairs'])==len(aux_after['pairs']) and all(decoded_equal(p,q) for p,q in zip(aux_before['pairs'],aux_after['pairs'])),
     'raw_side_record_differences':raw_diffs,'raw_bytes_equal':not raw_diffs}
assert not nonpair_changes and aux['identity_order_equal'] and aux['decoded_fields_equal']
paths=[RUN/n for n in ['metadata.json','trace.jsonl','before.json','after.json','restored.json','before-branch-inputs.json','after-branch-inputs.json','restored-branch-inputs.json','pending-analysis.json','end-comparisons.json']]
paths += [TRACES/'pending-g-closeout.json',TRACES/'pending-dry-closeout.json']
paths += [ROOT/n for n in ['make_pending_watch_observer.py','observe_pending_writes.cpp','observe_pending_writes.exe','start_pending_watch_observer.py','pending_watch_fixture.cpp','pending-watch-fixtures.json','analyze_pending_writes.py','unwind_rng_stack.py','survey-1622f0.txt','survey-3f8e10.txt','survey-16c640.txt','survey-166aa0.txt']]
report={'schema':'san14.lockstep.pending-writes.v1','created':datetime.now().astimezone().isoformat(),
    'result':'NO_PENDING_RESIDUE_OR_SKIP_IN_RUN_G_ORIGINAL_A_STILL_UNRESOLVED',
    'analysis':a,'end_comparisons':ends,'restoration_vs_this_run_start':restoration,'additional_restoration':aux,
    'closeout':{k:close[k] for k in ['date','player','sampled_records','debugger_attached','original_strategy_update_restored','save34_sha256','backup_sha256','restored_diagnostics','rng_state_rewritten']},
    'fixtures':[{'case':r['case'],'result':r['result'],'writes':r['writes'],'fixture':r['fixture']} for r in fixtures],
    'shared_rng_setter_note':'The raw label load_rng_setter names one instrumented function, not every event context. One CLoadState restored save RNG; one CSaveState re-stored the same current value. No second load is inferred.',
    'remaining_candidates':[
        {'path':'0x3F9344 scheduled gate','known':'RBP must be nonzero; normal G gates agree with F.','missing_in_a':'Actual subday and cached gate register; original logger sampled stage but not these.'},
        {'path':'0x1622F0 pair builder','known':'Return boolean is derived from resulting manager+0xC0 list count at 0x16298B..0x162996. Sources include a separate live linked list and 0x210D40 predicate.','missing_in_a':'Post-build pair identities/count and live-list membership.'},
        {'path':'0x15BE80 pair processing','known':'Per-side state/force predicates and optional special filter can skip pairs.','missing_in_a':'Per-pair reasons and special-filter value; normal F was already recorded.'},
        {'path':'0x3F8E10 frame scheduling','known':'Timer budget check precedes the original stage observation. Both old runs used identical observer hash.','missing_in_a':'Per-invocation timing and scheduler return path; no proof the observer caused divergence.'}],
    'decision':'Downgrade residual pending94 from leading explanation to unconfirmed conditional mechanism; do not patch flags. Audit missing battle-input inventories and observer timing before requesting more ordinary replay trials.',
    'original_a_cause_proven':False,'deterministic_lockstep_proven':False,'complete_world_equality_proven':False,
    'manifest':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
path=OUT/'战斗等待标志写入追查第五轮证据.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert load(path)==report
print(json.dumps({'published':str(path),'observed_field_writes':len(a['writes']),'gate_samples':19,'end_sample_count':len(load(RUN/'after.json')['records']),
    'restored_rng':restored['random_inputs']['global_18eb8b0'],'aux_raw_side_differences':len(raw_diffs),'debugger_attached':close['debugger_attached']},ensure_ascii=True))
