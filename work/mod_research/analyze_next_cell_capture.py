"""Classify observed producer/consumer order; do not infer unobserved barriers."""
import argparse,json,sys
from pathlib import Path
from bisect import bisect_right
p=argparse.ArgumentParser();p.add_argument('name');args=p.parse_args();sys.argv=sys.argv[:1]
import disasm_chained as d
ROOT=Path(__file__).resolve().parent
assert args.name.replace('-','').isalnum()
run=ROOT/'lockstep-traces'/args.name
data=[json.loads(s) for s in (run/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
active={};jobs=[];writes=[];consumers=[];errors=[];last_write=None
for r in data:
    event=r['event']
    if event.startswith('error'):errors.append(r)
    if event=='worker_enter':
        if r['thread'] in active:errors.append({'error':'nested worker entry','seq':r['seq']})
        job={'thread':r['thread'],'enter_seq':r['seq'],'return_seq':None,'working_ids':r['working_ids'],'write_sequences':[]}
        jobs.append(job);active[r['thread']]=job
    elif event=='worker_return':
        job=active.pop(r['thread'],None)
        if job:job['return_seq']=r['seq']
        else:errors.append({'error':'worker return without observed entry','seq':r['seq']})
    elif event=='next_cell_write':
        rip=r['rip_rva'];i=bisect_right(d.starts,rip-1)-1;instruction=None;function=None
        if i>=0 and rip-1<d.entries[i][1]:
            e=d.entries[i];function=hex(d.primary(e)[0])
            for ins in d.decoder.disasm(d.image[e[0]:e[1]],e[0]):
                if ins.address+ins.size==rip:instruction={'rva':hex(ins.address),'instruction':ins.mnemonic+' '+ins.op_str}
        job=active.get(r['thread'])
        item={k:r.get(k) for k in ('seq','thread','date','subday','progress_stage','previous_observed','observed_after','actual_cell','worker_90','task_done_70')}
        item.update({'writer':instruction,'function':function,'inside_observed_worker_callback':bool(job),
                     'worker_enter_seq':job['enter_seq'] if job else None})
        if job:job['write_sequences'].append(r['seq'])
        writes.append(item);last_write=item
    elif event=='movement_consume':
        item={k:r.get(k) for k in ('seq','thread','date','subday','progress_stage','next_cell','actual_cell','worker_90','task_done_70')}
        item['active_worker_callbacks']=list(active)
        item['latest_observed_write_seq']=last_write['seq'] if last_write else None
        item['value_matches_latest_observed_write']=r['next_cell']==last_write['observed_after'] if last_write else None
        consumers.append(item)
report={'run':args.name,'clean_detach':bool(data and data[-1].get('event')=='detached' and data[-1].get('registers_restored')),
    'errors':errors,'jobs':jobs,'writes':writes,'consumers':consumers,'callbacks_still_active_at_stop':list(active),
    'limits':['Data breakpoints report after the write. Previous value is the last observation, not a hardware pre-write capture.',
        'Worker-return marker precedes outer task-completion publication; worker_90 tracks lifecycle, task_done_70 can be stale when no task is active.',
        'No overlapping callbacks at a consumer does not establish a guaranteed program barrier.',
        'One army in one instrumented process; no full-world or two-client determinism proof.',
        'Stopping at the consumption marker does not itself prove the subsequent position store executed.']}
(run/'next-cell-capture-analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'run':args.name,'clean_detach':report['clean_detach'],'errors':len(errors),
    'jobs':len(jobs),'writes':len(writes),'consumers':consumers},ensure_ascii=True))
