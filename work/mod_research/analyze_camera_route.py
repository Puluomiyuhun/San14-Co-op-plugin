"""Analyze a bounded camera-route trace, retaining RNG gaps and scope limits."""
import argparse,json,struct
from pathlib import Path
from collections import Counter
from analyze_lockstep import rows,load,baseline_difference
from analyze_combat_gates import next_rng
from unwind_rng_stack import Unwinder
ROOT=Path(__file__).resolve().parent;TRACES=ROOT/'lockstep-traces'
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('after');args=p.parse_args()
assert args.name.replace('-','').isalnum() and args.after.replace('-','').isalnum()
run=TRACES/args.name;data=rows(run/'trace.jsonl');meta=load(run/'metadata.json');before=load(run/'before.json')
after=load(TRACES/(args.after+'.json'));events=[r for r in data if 'seq' in r]
gates=[r for r in events if r['event']=='combat_gate'];rng=[r for r in events if r['event']=='rng_update']
assert all(r['seq']==i+1 for i,r in enumerate(events))
u=Unwinder((ROOT/'game-runtime-image.bin').read_bytes(),(ROOT/'runtime-pdata.bin').read_bytes(),int(meta['base'],16))
unwound=[]
for r in rng:
    v=u.walk(r);v['scope']='Ordinary frames and decoded return sites only; bounded by the actual captured stack bytes, at most 2048 here.'
    unwound.append({'seq':r['seq'],'date':r['date'],'subday':r['subday'],'caller_rva':hex(r['caller_rva']),
        'before':r['before'],'after':r['after'],'frames':v['frames'],'stopped':v['stopped'],'scope':v['scope']})
(run/'unwound-stacks.json').write_text(json.dumps(unwound,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
expected=before['random_inputs']['global_18eb8b0'];gaps=[];algorithm=[]
for r in events:
    if r['global_rng']!=expected:gaps.append({'seq':r['seq'],'event':r['event'],'expected':expected,'observed':r['global_rng']})
    expected=r['global_rng']
    if r['event']=='rng_update':
        if next_rng(r['before'])!=r['after']:algorithm.append(r['seq'])
        assert r['before']==r['global_rng'];expected=r['after']

ends={}
for name in ('after-run-a','after-run-b','after-stage-path-i2','after-next-cell-j2'):
    ends[name]=baseline_difference(load(TRACES/(name+'.json')),after)
(run/'end-comparisons.json').write_text(json.dumps(ends,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
comparisons={}
for name in ('run-a','run-b'):
    old=[r for r in rows(TRACES/name/'trace.jsonl') if r['event']=='stage' and r['stage']==12]
    different=[]
    for i,(a,b) in enumerate(zip(old,gates)):
        ad=dict(a['armies']);bd=dict(b['armies']);changed=[]
        for ident in sorted(ad.keys()|bd.keys()):
            if ad.get(ident)==bd.get(ident):continue
            if ident not in ad or ident not in bd:changed.append({'id':ident,'membership':True});continue
            av,bv=bytes.fromhex(ad[ident]),bytes.fromhex(bd[ident])
            offsets=[j+0x10 for j,(v,w) in enumerate(zip(av,bv)) if v!=w]
            changed.append({'id':ident,'offsets':[hex(j) for j in offsets],
                'only_next_cell':all(j in (0x48,0x49) for j in offsets),
                'soldiers_before':int.from_bytes(av[6:8],'little'),'soldiers_current':int.from_bytes(bv[6:8],'little')})
        fields=[k for k in ('date','world_inputs','global_rng') if a[k]!=b[k]]
        if changed or fields:different.append({'index':i,'date':b['date'],'subday':b['subday'],'fields':fields,'armies':changed})
    comparisons[name]={'old_samples':len(old),'current_samples':len(gates),'different_samples':different,
        'scope':'Old stage-12 dispatch boundary versus current pre-combat gate; same logical stage, different instruction and instrumentation. Not a controlled camera-only comparison.'}

dispatch=[]
for r in events:
    if r['event']!='tactic_dispatch':continue
    t=r['tactic_record'];unit=before['records'].get('army:'+str(t['actor_id'])) if t['actor_type']==0x1b else None
    dispatch.append({k:r[k] for k in ('seq','thread','date','subday','stage','effect_count')}|
        {'actor_type':t['actor_type'],'actor_id':t['actor_id'],
         'leader_id_at_baseline':int.from_bytes(bytes.fromhex(unit)[2:4],'little') if unit else None,
         'tactic_address':hex(struct.unpack_from('<Q',bytes.fromhex(t['raw_hex']))[0]),
         'camera_level':r['camera']['level'],'global_rng':r['global_rng']})

report={'run':args.name,'clean_detach':bool(data and data[-1].get('event')=='detached' and data[-1].get('registers_restored')),
    'errors':[r for r in data if r['event'] in ('error','error_cleanup','process_exit')],
    'event_counts':dict(Counter(r['event'] for r in data)),
    'camera_before_level':struct.unpack_from('<i',bytes.fromhex(meta['camera_before_hex']),0x230)[0],
    'observed_camera_states':[{'level':k[0],'fraction':k[1],'mode_288':k[2],'linked_present':k[3],'events':v}
        for k,v in Counter((r['camera']['level'],r['camera']['fraction'],r['camera']['mode_288'],r['camera']['linked_present']) for r in events).items()],
    'gate_coverage':{'count':len(gates),'dates':sorted({tuple(r['date']) for r in gates}),
        'date_subday_pairs':[[r['date'],r['subday']] for r in gates],
        'gate_mismatches':[r['seq'] for r in gates if r['rbp_gate']!=int(r['subday']//2==5) or r['rsi_substep']!=r['subday']//2],
        'nonzero_wait_fields':[{k:r[k] for k in ('seq','date','subday','pending_94','effect_pending_98','effect_count')} for r in gates if r['pending_94'] or r['effect_pending_98'] or r['effect_count']]},
    'tactic_dispatches':dispatch,'camera_decisions':[{k:r[k] for k in ('seq','date','subday','scene_eligible','tactic_record')} for r in events if r['event']=='tactic_camera_decision'],
    'rng':{'calls':len(rng),'callers':{hex(k):v for k,v in Counter(r['caller_rva'] for r in rng).items()},
        'state_chain_gaps':gaps,'algorithm_mismatch_sequences':algorithm,'last_expected_state':expected,
        'end_state':after['random_inputs']['global_18eb8b0'],'end_matches_last_expected':after['random_inputs']['global_18eb8b0']==expected,
        'scope':'Primary writer observed before its store. No gaps in observed samples would not prove all intermediate writes are captured.'},
    'end_comparison':{k:{'different_records':len(v['sampled_record_changes_excluding_known_runtime_pointer']),
        'focused_equal':v['focused_state_equal'],'tasks_equal':v['person_task_sample_equal'],'rng_equal':v['random_inputs_equal']} for k,v in ends.items()},
    'gate_comparisons':comparisons,
    'camera_causation_proven':False,'original_a_root_cause_proven':False,'complete_world_determinism_proven':False}
(run/'camera-route-analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('run','clean_detach','errors','event_counts','camera_before_level','observed_camera_states','tactic_dispatches','camera_decisions','rng','end_comparison')},ensure_ascii=True))
print(json.dumps({'gate_coverage_count':len(gates),'gate_mismatches':report['gate_coverage']['gate_mismatches'],
    'old_gate_comparison':{name:{'army_difference_samples':sum(bool(x['armies']) for x in v['different_samples']),
        'soldier_difference_samples':sum(any(a.get('soldiers_before')!=a.get('soldiers_current') for a in x['armies']) for x in v['different_samples'])}
        for name,v in comparisons.items()}},ensure_ascii=True))
