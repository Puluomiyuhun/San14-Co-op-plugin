"""Summarize captured branch evidence without inferring unobserved branch values."""
import json
from collections import Counter
from pathlib import Path
import sys
from analyze_combat_gates import delta, gate_key

ROOT=Path(__file__).resolve().parent
TRACES=ROOT/'lockstep-traces'
PHASE_FUNCTIONS={1:'0x166CC0',2:'0x15C260',3:'0x15CD80',4:'0x15CBC0',5:'0x15C9B0',6:'0x161F10',7:'0x166AA0'}

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def rows(path):return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()]

def decode_side(raw):
    b=bytes.fromhex(raw)
    assert len(b)==24
    return {'id':int.from_bytes(b[:2],'little'),'type':int.from_bytes(b[4:8],'little'),
            'field_08':b[8],'field_0a':int.from_bytes(b[10:12],'little'),
            'field_0c':int.from_bytes(b[12:16],'little'),'force':int.from_bytes(b[16:20],'little'),
            'field_14':b[20]}

def identity(pair):
    return tuple((x['type'],x['id']) for x in (decode_side(pair['a']),decode_side(pair['b'])))

def analyze(name):
    folder=TRACES/name
    trace=rows(folder/'trace.jsonl')
    assert trace[-1]['event']=='detached' and trace[-1]['registers_restored']
    assert not any(r['event'].startswith('error') for r in trace)
    groups={}
    for r in trace:
        if 'date' in r:groups.setdefault(gate_key(r),[]).append(r)
    results=[];contradictions=[]
    for key,group in groups.items():
        gates=[r for r in group if r['event']=='combat_gate']
        ready=[r for r in group if r['event']=='pairs_ready']
        decisions=[r for r in group if r['event']=='pair_eligibility']
        phases=[r for r in group if r['event']=='pair_phase']
        if len(gates)!=1:contradictions.append({'key':key,'issue':'Expected one gate observation','observed':len(gates)})
        gate=gates[0] if gates else None
        checks=[];active=None
        for r in group:
            if r['event']=='pair_eligibility':
                active={'identity':identity(r['pair']),'a':decode_side(r['pair']['a']),'b':decode_side(r['pair']['b']),
                        'eligible_before_special_filter':bool(r['eligibility_before_special_filter']),
                        'special_filter_enabled':r['special_filter_enabled'],'phases':[],
                        'sequence':r['seq']}
                checks.append(active)
            elif r['event']=='pair_phase':
                if active is None or active['identity']!=identity(r['pair']):
                    contradictions.append({'key':key,'issue':'Phase does not match preceding observed pair','seq':r['seq']})
                    continue
                active['phases'].append(r['phase'])
                if not active['eligible_before_special_filter']:
                    contradictions.append({'key':key,'issue':'Ineligible pair entered phase loop','seq':r['seq']})
        if gate and not gate['rbp_gate']:
            classification='scheduled_gate_closed'
            if ready or decisions or phases:contradictions.append({'key':key,'issue':'Inner events at closed gate'})
        elif gate and gate['pending_94'] and not ready:
            classification='pending_path_no_new_batch_observed'
        elif len(ready)==1 and not ready[0]['eax']:
            classification='pair_rebuild_returned_false'
        elif len(ready)==1 and ready[0]['eax']:
            classification='rebuilt_batch_with_pair_observations'
        else:
            classification='insufficient_or_unexpected_observations'
        if ready and ready[0]['eax'] and len(checks)!=ready[0]['pair_count']:
            contradictions.append({'key':key,'issue':'Visited pair count differs from rebuilt inventory; investigate early stop or trace coverage',
                                   'visited':len(checks),'inventory':ready[0]['pair_count']})
        summary={'key':key,'classification':classification,'gate':{k:v for k,v in (gate or {}).items() if k not in ('armies','pairs','force_predicate_inputs')},
                 'pair_rebuild':[{k:v for k,v in r.items() if k not in ('armies','pairs','force_predicate_inputs')} for r in ready],
                 'pair_inventory':[{'a':decode_side(x['a']),'b':decode_side(x['b'])} for x in ready[0]['pairs']] if ready else None,
                 'pair_checks':checks,'phase_event_count':len(phases)}
        results.append(summary)
    # Delta brackets show observed changes across an interval; they do not ascribe
    # every change in that interval to a particular pair or phase.
    for index,item in enumerate(results[:-1]):
        group=groups[tuple(item['key'])]
        start=next((r for r in group if r['event']=='pairs_ready'),None)
        nextgate=next((r for r in groups[tuple(results[index+1]['key'])] if r['event']=='combat_gate'),None)
        if start and nextgate:item['army_troop_delta_to_next_gate']=delta(start,nextgate)
    c={gate_key(r):r for r in rows(TRACES/'gate-run-c/trace.jsonl') if r['event']=='combat_gate'}
    comparisons=[]
    for r in trace:
        if r['event']!='combat_gate' or gate_key(r) not in c:continue
        earlier=c[gate_key(r)]
        fields=('world_inputs','global_rng','rbp_gate','rsi_substep','worker_90','pending_94','effect_count','effect_pending_98','pair_count','armies')
        comparisons.append({'key':gate_key(r),'different_fields':[f for f in fields if earlier[f]!=r[f]],
                            'troop_differences':delta(earlier,r)})
    report={'schema':'san14.battle-branches.analysis.v1','trial':name,'event_counts':dict(Counter(r['event'] for r in trace)),
            'phase_entry_functions':PHASE_FUNCTIONS,'batches':results,'consistency_issues':contradictions,
            'gate_comparison_to_c':comparisons,'baseline_check':read(folder/'baseline-check.json'),
            'scope':'Branch diagnosis, not a matched-start determinism trial. Original A did not record these fields.',
            'limits':['The eligibility value is before the optional special filter; its exact predicate result is not separately observed.',
                      'Phase entries do not certify all nested calculations; no dedicated final damage/tactic event stream in this capture.',
                      'Between-gate troop deltas may include work outside the recorded batch.','Hardware breakpoints affect wall-clock timing.'],
            'original_a_root_cause_proven':False}
    (folder/'branch-analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'event_counts':report['event_counts'],'issues':contradictions,
        'active_batches':[{'key':r['key'],'classification':r['classification'],'pairs':len(r['pair_checks']),
                           'ineligible':sum(not p['eligible_before_special_filter'] for p in r['pair_checks']),
                           'phases':[p['phases'] for p in r['pair_checks']],
                           'troop_delta':r.get('army_troop_delta_to_next_gate')} for r in results if r['gate'].get('rbp_gate')]},ensure_ascii=True,indent=2))

if __name__=='__main__':analyze(sys.argv[1])
