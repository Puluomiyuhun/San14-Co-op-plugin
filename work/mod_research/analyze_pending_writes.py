"""Offline audit of pending/effect write history and combat snapshots."""
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
import sys
from analyze_combat_gates import delta, gate_key
from unwind_rng_stack import Unwinder
saved_argv=sys.argv[:]
sys.argv=sys.argv[:1]
import disasm_chained as d
sys.argv=saved_argv
ROOT=Path(__file__).resolve().parent

def load(path):return json.loads(path.read_text(encoding='utf-8'))
def rows(path):return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]

def predecessor(row,base):
    rva=row['rip']-base
    i=bisect_right(d.starts,rva-1)-1
    if i<0 or rva>d.entries[i][1]:return {'verified':False,'reason':'Outside captured runtime-function metadata'}
    entry=d.entries[i]
    insns=list(d.decoder.disasm(d.image[entry[0]:rva],entry[0]))
    if not insns or insns[-1].address+insns[-1].size!=rva:
        return {'verified':False,'reason':'No decoded instruction ending at post-write RIP'}
    ins=insns[-1]
    start=row.get('code_window_start',0)-base
    raw=bytes.fromhex(row.get('code_window_hex',''))
    matches=bool(raw) and start>=0 and d.image[start:start+len(raw)]==raw
    operands=[o for o in ins.operands if o.type==d.capstone.x86.X86_OP_MEM and o.access&d.capstone.CS_AC_WRITE]
    return {'verified':matches and bool(operands),'rva':hex(ins.address),'instruction':ins.mnemonic+' '+ins.op_str,
        'function_root':hex(d.primary(entry)[0]),'captured_code_matches':matches,
        'writes_memory':bool(operands),'scope':'Decoded from known function fragment; hardware watch identifies the watched range. No inference from arbitrary backward decoding.'}

def main():
    folder=ROOT/'lockstep-traces'/sys.argv[1]
    data=rows(folder/'trace.jsonl');meta=load(folder/'metadata.json');base=int(meta['base'],16)
    assert data[-1]['event']=='detached' and data[-1]['registers_restored'],'Capture still active or cleanup incomplete'
    assert not any(r['event'].startswith('error') for r in data)
    u=Unwinder(d.image,(ROOT/'runtime-pdata.bin').read_bytes(),base)
    baseline=next(r for r in data if r['event']=='watch_baseline')
    previous=[baseline['pending_94'],baseline['effect_pending_98']]
    writes=[];gaps=[]
    for r in data:
        if r['event']=='field_write':
            slot=r['slot'];assert slot in (0,1)
            if previous[slot]!=r['previous_observed']:
                gaps.append({'seq':r['seq'],'kind':'previous_observation_mismatch','expected':previous[slot]})
            previous[slot]=r['observed_after']
            writes.append({k:v for k,v in r.items() if k not in ('stack_hex','code_window_hex','registers')}
                |{'writer':predecessor(r,base),'unwind':u.walk(r)})
        if r['event'] in ('field_write','combat_gate','load_rng_setter'):
            current=[r['pending_94'],r['effect_pending_98']]
            if current!=previous:gaps.append({'seq':r['seq'],'kind':'snapshot_vs_tracked_values','tracked':previous[:],'snapshot':current})
    gates=[r for r in data if r['event']=='combat_gate']
    setters=[{k:v for k,v in r.items() if k not in ('stack_hex','code_window_hex','registers')}
        |{'unwind':u.walk(r),'context':'load' if 'CLoadState' in r['states'] else 'save' if 'CSaveState' in r['states'] else 'other'}
        for r in data if r['event']=='load_rng_setter']
    reference={gate_key(r):r for r in rows(ROOT/'lockstep-traces/branch-run-f/trace.jsonl') if r['event']=='combat_gate'}
    comparisons=[]
    fields={'armies':'armies','global_rng':'global_rng','rbp_gate':'rbp_gate','rsi_substep':'rsi_substep',
            'pending_94':'pending_94','worker_90':'worker_90','effect_pending_98':'effect_pending_98',
            'effect_count_38':'effect_count','pair_count_c0':'pair_count'}
    for r in gates:
        key=gate_key(r)
        if key not in reference:continue
        ref=reference[key]
        comparisons.append({'key':list(key),'different_fields':[k for k,v in fields.items() if r[k]!=ref[v]],'troop_differences':delta(ref,r)})
    first=next((r for r in gates if r['rbp_gate']),None)
    timeline=[{k:r[k] for k in ('event','seq','date','subday','pending_94','effect_pending_98','worker_90','effect_count_38','pair_count_c0','global_rng','rbp_gate') if k in r} for r in data if r['event'] not in ('attached','armed','detached')]
    result={'run':folder.name,'event_counts':dict(Counter(r['event'] for r in data)),
        'capture_complete':bool(gates) and gates[-1]['date']==[203,8,12] and gates[-1]['subday']==12,
        'baseline':baseline,'rng_setter_calls':setters,'load_markers':[r for r in setters if r['context']=='load'],
        'save_markers':[r for r in setters if r['context']=='save'],'writes':writes,'observation_chain_gaps':gaps,
        'writes_before_first_scheduled_combat':[r for r in writes if first and r['seq']<first['seq']],
        'first_scheduled_combat':None if first is None else {k:v for k,v in first.items() if k not in ('armies','stack_hex','code_window_hex','registers')},
        'gate_comparisons_with_f':comparisons,'timeline':timeline,
        'original_a_cause_proven':False,'complete_world_equality_proven':False,
        'limits':['Raw event name load_rng_setter identifies a shared setter; load/save are classified from state stack, not the name.',
                  'A/B did not record these flags.','This is a new observed run, not a controlled reproduction of A.',
                  'Data watch previous_observed is not an atomic before-store value.',
                  'Unwind supports ordinary frames, not arbitrary epilogs; unknown writers require manual validation.',
                  'The debugger changes wall-clock timing.']}
    (folder/'pending-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'events':result['event_counts'],'capture_complete':result['capture_complete'],
        'writers':dict(Counter((r['writer'].get('rva','unknown') for r in writes))),
        'gaps':gaps,'first_scheduled_combat':None if first is None else {k:first[k] for k in ('date','subday','rbp_gate','pending_94','effect_pending_98')},
        'gate_differences':comparisons},ensure_ascii=True))
if __name__=='__main__':main()
