"""Compare gate snapshots and audit observed RNG transitions without game writes."""
import json
from pathlib import Path
from collections import Counter
from analyze_lockstep import rows, baseline_difference, load

ROOT=Path(__file__).resolve().parent
TRACES=ROOT/'lockstep-traces'

def next_rng(state):
    def rol16(x):
        x &= 0xffffffff
        return ((x<<16)|(x>>16)) & 0xffffffff
    for _ in range((state&15)+1):
        state=rol16((state-123)*0x693d4b5+123456)
    return rol16(state*0x41c64e6d+12345)

def troops(row):
    return {identity:int.from_bytes(bytes.fromhex(raw)[6:8],'little') for identity,raw in row['armies']}

def delta(a,b):
    a,b=troops(a),troops(b)
    return [{'id':i,'before':a.get(i),'after':b.get(i)} for i in sorted(a.keys()|b.keys()) if a.get(i)!=b.get(i)]

def gate_key(row):
    return tuple(row['date'])+(row['subday'],)

def analyze():
    c=rows(TRACES/'gate-run-c/trace.jsonl')
    d=rows(TRACES/'rng-run-d/trace.jsonl')
    initial=load(TRACES/'rng-run-d/before.json')
    assert c[-1]['event']=='detached' and c[-1]['registers_restored']
    assert d[-1]['event']=='detached' and d[-1]['registers_restored']
    assert not any(r['event'].startswith('error') for r in c+d)
    reports={}
    for day in (11,12):
        batch={r['event']:r for r in c if r.get('date')==[203,8,day] and r.get('subday')==10}
        reports[str(day)]={k:{f:v for f,v in r.items() if f!='armies'} for k,r in batch.items()}
        reports[str(day)]['troop_changes']=delta(batch['combat_entry'],batch['combat_return'])
    cg={gate_key(r):r for r in c if r['event']=='combat_gate'}
    dg={gate_key(r):r for r in d if r['event']=='combat_gate'}
    comparisons=[]
    fields=('world_inputs','global_rng','rbp_gate','rsi_substep','worker_90','pending_94','effect_count','effect_pending_98','pair_count','armies')
    for key in sorted(cg.keys()&dg.keys()):
        a,b=cg[key],dg[key]
        differences=[field for field in fields if a[field]!=b[field]]
        comparisons.append({'key':key,'different_fields':differences,'troop_differences':delta(a,b),
                            'rng':{'c':a['global_rng'],'d':b['global_rng']}})
    rng=[r for r in d if r['event']=='rng_update']
    previous=initial['random_inputs']['global_18eb8b0']
    chain_breaks=[];algorithm_mismatches=[]
    for r in d:
        if r['event']=='rng_update':
            if previous!=r['before']:chain_breaks.append({'seq':r['seq'],'expected':previous,'observed':r['before']})
            if next_rng(r['before'])!=r['after']:algorithm_mismatches.append(r)
            previous=r['after']
        elif r['event']=='combat_gate' and previous!=r['global_rng']:
            chain_breaks.append({'seq':r['seq'],'expected':previous,'observed':r['global_rng'],'at':'gate'})
    calls=Counter((r['writer_rva'],r['caller_rva']) for r in rng)
    first_batch={r['event']:r for r in c if r.get('date')==[203,8,11] and r.get('subday')==10}
    old_matches={}
    for name in ('run-a','run-b'):
        stages=[r for r in rows(TRACES/name/'trace.jsonl') if r['event']=='stage']
        old_matches[name]={'first_batch_before_army_bytes_equal':stages[167]['armies']==first_batch['combat_entry']['armies'],
                           'first_batch_after_army_bytes_equal':stages[168]['armies']==first_batch['combat_return']['armies']}
    result={
        'c_batches':reports,'c_first_batch_vs_old':old_matches,
        'd_event_counts':dict(Counter(r['event'] for r in d)),
        'c_d_gate_comparisons':comparisons,
        'first_c_d_gate_difference':next((r for r in comparisons if r['different_fields']),None),
        'rng_chain_breaks':chain_breaks,'rng_algorithm_mismatches':algorithm_mismatches,
        'rng_callers':[{'writer_rva':hex(w),'caller_return_rva':hex(caller),'count':count} for (w,caller),count in calls.most_common()],
        'rng_observations':rng,
        'rng_coverage':'Three known sequential writer instructions only; chain checks detect unexplained changes at observed points, not all possible RNG sources.',
        'baseline_c_d':baseline_difference(load(TRACES/'gate-run-c/before.json'),initial),
        'original_a_root_cause_proven':False,
    }
    (TRACES/'gate-rng-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rng_observations','c_batches','baseline_c_d','c_d_gate_comparisons')},ensure_ascii=True,indent=2))

if __name__=='__main__':
    analyze()
