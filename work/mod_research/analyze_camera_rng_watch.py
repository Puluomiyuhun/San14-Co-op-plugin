"""Post-write RNG trace analysis. Never confuse last-observed with atomic before."""
import argparse,json
from collections import Counter
from pathlib import Path
from analyze_lockstep import rows,load,baseline_difference
from analyze_combat_gates import next_rng
from unwind_rng_stack import Unwinder
ROOT=Path(__file__).resolve().parent;TR=ROOT/'lockstep-traces'
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('after');a=p.parse_args()
assert all(s.replace('-','').isalnum() for s in (a.run,a.after))
folder=TR/a.run;trace=rows(folder/'trace.jsonl');meta=load(folder/'metadata.json')
assert trace[-1]['event']=='detached' and trace[-1]['registers_restored'], 'Capture is not cleanly complete'
assert not any(r['event'].startswith('error') for r in trace)
events=[r for r in trace if 'seq' in r];assert [r['seq'] for r in events]==list(range(1,len(events)+1))
before=load(folder/'before.json');after=load(TR/(a.after+'.json'))
expected=next(r['value'] for r in trace if r['event']=='rng_watch_baseline')
gaps=[];writes=[];non_native=[]
u=Unwinder((ROOT/'game-runtime-image.bin').read_bytes(),(ROOT/'runtime-pdata.bin').read_bytes(),int(meta['base'],16))
known={0x3aa80b:'range_helper',0x3aa3db:'unbounded_helper',0x3aa441:'percentage_helper',0x3aa3e6:'setter'}
for r in events:
    observed=r['previous_observed'] if r['event']=='rng_write' else r['global_rng']
    if observed!=expected:gaps.append({'seq':r['seq'],'expected':expected,'observed':observed,'event':r['event']})
    if r['event']=='rng_write':
        assert r['global_rng']==r['observed_after']
        v=u.walk(r);v['scope']='Captured stack length '+str(len(bytes.fromhex(r['stack_hex'])))+' bytes; ordinary frames only; call sites verified. No general epilog simulation.'
        entry={k:r[k] for k in ('seq','date','subday','stage','thread','previous_observed','observed_after','rip_after_rva','states')}
        entry.update({'known_writer':known.get(r['rip_after_rva'],'other'),
            'matches_one_native_step_from_previous_observation':next_rng(r['previous_observed'])==r['observed_after'],'unwind':v})
        writes.append(entry)
        if not entry['matches_one_native_step_from_previous_observation']:non_native.append(r['seq'])
        expected=r['observed_after']
    else:expected=observed
(folder/'rng-writes-unwound.json').write_text(json.dumps(writes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
gates=[r for r in events if r['event']=='combat_gate']
oldfolder=TR/'camera-route-far-k';oldgates=[r for r in rows(oldfolder/'trace.jsonl') if r['event']=='combat_gate']
key=lambda r:tuple(r['date'])+(r['subday'],)
old={key(r):r for r in oldgates};new={key(r):r for r in gates}
assert len(new)==len(gates)
changes=[]
for k in sorted(old.keys()&new.keys()):
    left,right=old[k],new[k];la,ra=dict(left['armies']),dict(right['armies'])
    changed=[i for i in sorted(la.keys()|ra.keys()) if la.get(i)!=ra.get(i)]
    if changed:changes.append({'date_subday':list(k),'army_ids':changed})
start_compare=baseline_difference(load(oldfolder/'before.json'),before)
end_compare=baseline_difference(load(TR/'after-camera-far-k.json'),after)
table={int(r['address'],16):r for r in load(folder/'tactics-table.json')}
tactics=[]
for r in events:
    if r['event'] not in ('tactic_dispatch','tactic_camera_decision'):continue
    addr=int.from_bytes(bytes.fromhex(r['tactic_record']['raw_hex'])[:8],'little')
    mapped=table.get(addr)
    tactics.append({k:r[k] for k in ('seq','event','date','subday','stage','tactic_record')}|
        {'tactic_id':mapped['id'] if mapped else None,'tactic_name':mapped['name'] if mapped else None,
         'camera_level':r['camera']['level'],'scene_eligible':r.get('scene_eligible')})
report={'run':a.run,'clean_detach':True,'event_counts':dict(Counter(r['event'] for r in trace)),
 'camera_states':[{'level':k[0],'fraction':k[1],'linked':k[2],'events':v} for k,v in Counter((r['camera']['level'],r['camera']['fraction'],r['camera']['linked_present']) for r in events).items()],
 'rng':{'writes':len(writes),'writers':dict(Counter(r['known_writer'] for r in writes)),'continuity_gaps':gaps,
   'not_matching_one_native_step':non_native,'last_recorded':expected,'end_state':after['random_inputs']['global_18eb8b0'],
   'end_matches_last_recorded':expected==after['random_inputs']['global_18eb8b0']},
 'tactics':tactics,'far_gate_comparison':{'old_count':len(old),'new_count':len(new),'shared_keys':len(old.keys()&new.keys()),'changed_army_samples':changes},
 'far_start_comparison':start_compare,'far_end_comparison':end_compare,
 'controlled_camera_only_experiment':False,
 'limits':['Different recorder from old far run changes timing. Planning RNG also differs unless explicitly aligned.',
           'Known shared RNG address only; last-observed value is not an atomic before value for racing threads.',
           'Date-21 auto-stop can precede report random consumption; residual end RNG difference is not automatically a missed combat write.',
           'Army records are partial boundary samples, not a full damage/animation sequence. Original A root cause remains unproven.']}
(folder/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('run','event_counts','camera_states','rng','tactics','far_gate_comparison')},ensure_ascii=True))
