"""Recover what old stage observations actually establish, without inventing subday."""
from pathlib import Path
import json
from collections import Counter
from analyze_lockstep import rows
ROOT=Path(__file__).resolve().parent

def changes(x,y):
    result=[]
    for kind in ('armies','cities'):
        a,b=dict(x[kind]),dict(y[kind])
        for identity in sorted(a.keys()|b.keys()):
            if a.get(identity)==b.get(identity):continue
            if identity not in a or identity not in b:
                result.append({'kind':kind,'id':identity,'membership_changed':True});continue
            u,v=bytes.fromhex(a[identity]),bytes.fromhex(b[identity])
            fields=[{'offset':hex(i+0x10),'before':p,'after':q} for i,(p,q) in enumerate(zip(u,v)) if p!=q]
            result.append({'kind':kind,'id':identity,'fields':fields})
    return result

def main():
    result={}
    for name in ('run-a','run-b'):
        data=rows(ROOT/'lockstep-traces'/name/'trace.jsonl')
        stages=[r for r in data if r['event']=='stage']
        assert len(stages)==3720
        assert all(r['stage']==i%31 for i,r in enumerate(stages))
        details=[]
        for i in range(31*12-1):
            a,b=stages[i:i+2]
            c=changes(a,b)
            if c or a['global_rng']!=b['global_rng']:
                details.append({'index':i,'cycle_index_inferred_from_stage_sequence':i//31,
                    'stage':a['stage'],'changes':c,'rng_before':a['global_rng'],'rng_after':b['global_rng']})
        batches=Counter()
        current=None;index=-1
        for row in data:
            if row['event']=='stage':index+=1;current=row
            elif row['event']=='casualty_request' and current:
                batches[(current['date'][2],index//31%12,current['stage'])]+=1
        result[name]={'stage_sequence_complete':True,'stage_samples':len(stages),
            'first_day_transitions':details,
            'casualty_batches':[{'day':d,'cycle_inferred':c,'stage':s,'count':n} for (d,c,s),n in batches.items()],
            'scope':'Sequence proves stage dispatch points were visited; it does not prove the cached time gate or every callee executed. Subday was not recorded.'}
    path=ROOT/'lockstep-traces/old-stage-transition-audit.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,r in result.items():
        print(name,json.dumps([{'index':x['index'],'cycle':x['cycle_index_inferred_from_stage_sequence'],'stage':x['stage'],
            'changes':len(x['changes']),'fields':dict(Counter(f['offset'] for o in x['changes'] for f in o.get('fields',[]))),
            'rng_changed':x['rng_before']!=x['rng_after']} for x in r['first_day_transitions']],ensure_ascii=True))

if __name__ == '__main__':
    main()
