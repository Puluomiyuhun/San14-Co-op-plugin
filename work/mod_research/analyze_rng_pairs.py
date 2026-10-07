"""Audit paired helper calls and classify only stack-verified candidate origins."""
from pathlib import Path
from collections import Counter,defaultdict
import json,sys
from unwind_rng_stack import Unwinder
ROOT=Path(__file__).resolve().parent
def next_state(seed):
    def rotate(n):return ((n<<16)|(n>>16))&0xffffffff
    n=(seed&15)+1
    for _ in range(n):seed=rotate(((seed-123)*0x693d4b5+123456)&0xffffffff)
    return rotate((seed*0x41c64e6d+12345)&0xffffffff)
def analyze(rows,base,unwinder=None,fixture=False):
    entries={};returns={};writes=[]
    for row in rows:
        if row['event']=='rng_entry':
            assert row['call_id'] not in entries;entries[row['call_id']]=row
        elif row['event']=='rng_return':
            assert row['call_id'] in entries and row['call_id'] not in returns;returns[row['call_id']]=row
        elif row['event']=='rng_write':writes.append(row)
    by_call=defaultdict(list)
    for w in writes:by_call[w['call_id']].append(w)
    calls=[];route_counts=Counter();failures=[]
    for identity,e in entries.items():
        ret=returns.get(identity)
        call={'call_id':identity,'thread':e['thread'],'kind':e['kind'],'argument':e['argument'],
              'date':e.get('date'),'stage':e.get('stage'),'entry_seq':e['seq'],'completed':ret is not None}
        if unwinder:
            stack=unwinder.walk(e);stack['scope']='Call-site-checked bounded ordinary-frame unwind; actual stack bytes='+str(len(e['stack_hex'])//2)+'.'
            pcs=[r['pc_rva'] for r in stack['frames']]
            call['unwind']=stack
            # An actual leaf return PC exactly equals the voice draw callsite's next instruction.
            route='voice_candidate' if e['caller']==base+0x3b3779 else 'text_scope_candidate' if '0x1ab6f9' in pcs else 'native_or_unknown'
        else:route='fixture'
        call['candidate_route']=route;route_counts[route]+=1
        if not ret:calls.append(call);continue
        assert ret['thread']==e['thread'] and ret['caller']==e['caller'] and ret['return_rsp']==e['entry_rsp']+8
        assert ret['kind']==e['kind'] and ret['argument']==e['argument']
        own=by_call[identity];no_draw=e['kind']=='range' and e['argument']<2
        other=[w['seq'] for w in writes if e['seq']<w['seq']<ret['seq'] and w['thread']!=e['thread']]
        call.update({'return_seq':ret['seq'],'actual_result':ret['result'],'own_write_count':len(own),
                     'other_thread_write_sequences':other,'entry_rng_snapshot':e['rng_snapshot'],'return_rng_snapshot':ret['rng_snapshot']})
        problems=[];stored=None;expected=None
        if no_draw:
            expected=0
            if own:problems.append('range below two unexpectedly has a paired write')
        elif len(own)!=1:problems.append('expected exactly one paired native helper write')
        else:
            w=own[0];stored=w['registers']['rax' if e['kind']=='range' else 'rcx']&0xffffffff
            if not fixture:
                expected_pc=base+(0x3aa80b if e['kind']=='range' else 0x3aa441)
                if w['rip']!=expected_pc:problems.append('write PC differs from audited native store')
            expected=((stored&0x7fffffff)%e['argument']) if e['kind']=='range' else int((stored&0x7fffffff)%100<e['argument'])
            call['stored_value_from_writer_register']=stored
            # If any other write interleaves, entry snapshot is not the guaranteed input read by the helper.
            if not other and stored!=next_state(e['rng_snapshot']):problems.append('entry snapshot recurrence mismatch without recorded intervening writer')
        call['expected_result_from_native_store']=expected
        if expected is not None and expected!=ret['result']:problems.append('observed native result mismatch')
        call['checks_pass']=not problems;call['problems']=problems
        if problems:failures.append(identity)
        calls.append(call)
    detached=next((r for r in reversed(rows) if r['event']=='detached'),None)
    return {'entry_count':len(entries),'return_count':len(returns),'write_count':len(writes),
            'unpaired_call_ids':sorted(set(entries)-set(returns)),'helper_result_mismatch_call_ids':failures,
            'candidate_route_counts':dict(route_counts),'no_draw_calls':sum(c['kind']=='range' and c['argument']<2 for c in calls),
            'writes_outside_paired_helpers':by_call[0],'calls':calls,'detached':detached,
            'scope':'Return values verified against audited helper rules; writer registers retain each thread store operand. No complete RNG-source inventory or battlefield determinism claim.'}
if __name__=='__main__':
    folder=ROOT/'lockstep-traces'/sys.argv[1]
    meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'));base=int(meta['base'],16)
    rows=[json.loads(line) for line in (folder/'trace.jsonl').read_text().splitlines()]
    assert rows[-1]['event']=='detached','Trace still active or failed; preserve it for explicit closeout'
    u=Unwinder((ROOT/'game-runtime-image.bin').read_bytes(),(ROOT/'runtime-pdata.bin').read_bytes(),base)
    result=analyze(rows,base,u)
    (folder/'paired-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('calls','writes_outside_paired_helpers','scope')},ensure_ascii=True))
