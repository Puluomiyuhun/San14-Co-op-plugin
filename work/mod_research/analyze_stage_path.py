"""Classify observed branch coverage; never backfill the missing original A data."""
import argparse,json,statistics
from pathlib import Path
from analyze_lockstep import rows
from audit_old_stage_transitions import changes
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('name');args=p.parse_args();assert args.name.replace('-','').isalnum()
run=ROOT/'lockstep-traces'/args.name;data=rows(run/'trace.jsonl')
stages=[r for r in data if r['event']=='stage']
errors=[r for r in data if r['event'] in ('error','error_cleanup','process_exit')]
closed=bool(data and data[-1].get('event')=='detached' and data[-1].get('registers_restored'))
windows=[]
for i,a in enumerate(stages[:-1]):
    if a['stage']!=12:continue
    b=stages[i+1]
    middle=[r for r in data if r.get('event')!='observer_cost' and a['seq']<r.get('seq',0)<b['seq']]
    entry=[r for r in middle if r['event']=='battle_entry'];ready=[r for r in middle if r['event']=='pairs_ready'];phases=[r for r in middle if r['event']=='pair_phase']
    if not a['rbp']:classification='TIME_GATE_FALSE'
    elif not entry:classification='ENTRY_NOT_OBSERVED'
    elif entry[0]['pending_94']:classification='PENDING_BRANCH_NO_NEW_BATCH'
    elif not ready:classification='BUILDER_RETURN_NOT_OBSERVED'
    elif not ready[0]['eax']:classification='BUILDER_RETURNED_EMPTY'
    elif not phases:classification='BUILT_PAIRS_BUT_NO_PHASE_ENTRY'
    else:classification='BATTLE_PHASES_EXECUTED'
    windows.append({'date':a['date'],'subday':a['subday'],'stage_sequence_index':i,'cached_gate':a['rbp'],
        'classification':classification,'battle_entries':len(entry),'builder_returns':len(ready),'phase_entries':len(phases),
        'built_pair_count':ready[0]['pair_count'] if ready else None,'pairs':ready[0]['pairs'] if ready else None,
        'phase_sequences':phases,'state_changes_to_next_stage':changes(a,b),
        'budget_elapsed_ms_at_stage':a['budget_elapsed_ms'],'timer_start_ms':a['frame_start_ms'],
        'pending_at_stage':a['pending_94'],'input_lists_at_stage':a['input_lists']})
freq=next((r['qpc_frequency'] for r in data if r['event']=='attached'),None)
costs=[r['qpc_ticks']*1000/freq for r in data if r['event']=='observer_cost'] if freq else []
report={'run':args.name,'cleanly_detached':closed,'errors':errors,'stage_samples':len(stages),
    'stage_sequence_matches_prefix':all(r['stage']==i%31 for i,r in enumerate(stages)),
    'actual_subdays':sorted({r['subday'] for r in stages}),
    'gate_mismatches':[{'index':i,'subday':r['subday'],'rbp':r['rbp'],'rsi':r['rsi']} for i,r in enumerate(stages) if r['rsi']!=r['subday']//2 or r['rbp']!=int(r['subday']//2==5)],
    'windows':windows,'observer_handler_cost_ms':{'count':len(costs),'median':statistics.median(costs) if costs else None,'maximum':max(costs) if costs else None,'sum':sum(costs)},
    'timing_scope':'Cost covers synchronous handler reads/format/flush only, not full OS debug dispatch and resume delay. Timer starts are millisecond values, not unique frame IDs.',
    'original_a_cause_proven':False,'full_world_determinism_proven':False}
(run/'stage-path-analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='windows'},ensure_ascii=True))
print(json.dumps({'windows':[{k:w[k] for k in ('subday','classification','built_pair_count','phase_entries')} for w in windows]},ensure_ascii=True))
