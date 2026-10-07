"""Compare recorded end states and read names of Sun Jiao's existing tactics."""
import json
from pathlib import Path
from lockstep_baseline import BattleObserver
from analyze_lockstep import load,baseline_difference
ROOT=Path(__file__).resolve().parent
TRACES=ROOT/'lockstep-traces'
names=['run-a/before.json','after-run-a.json','after-run-b.json','after-gate-run-c.json','after-rng-run-d.json']
states={n:load(TRACES/n) for n in names}
reader=BattleObserver()
try:
    root=reader.pointer(reader.memory.base+0x1FCA1E0)
    tactics=[]
    for identity in (4,5,9):
        ptr=reader.pointer(root+0x76C00+identity*8)
        reader.require_type(ptr,'CTacticsData')
        name=reader.memory.read(ptr+0x10,10).decode('utf-16le').split('\0')[0]
        tactics.append({'id':identity,'name':name})
finally:
    reader.close()
comparisons={}
for a,b in [('after-run-b.json','after-gate-run-c.json'),('after-gate-run-c.json','after-rng-run-d.json')]:
    diff=baseline_difference(states[a],states[b])
    comparisons[a+' vs '+b]=diff
result={'sunjiao':{n:next(a for a in d['focused']['all_active_units'] if a['officer_id']==555) for n,d in states.items()},
    'tactic_names':tactics,'end_comparisons':comparisons,
    'observation':'User saw fire arrows but is unsure whether earlier runs used it. This is not an established action-sequence difference.',
    'tactic_execution_logged':False}
(TRACES/'sunjiao-and-end-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'tactics':tactics,'comparisons':{k:{x:y for x,y in v.items() if x!='rebuilt_army_runtime_pointers'} for k,v in comparisons.items()}},ensure_ascii=True,indent=2))
