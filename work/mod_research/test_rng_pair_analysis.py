from pathlib import Path
from copy import deepcopy
import json
from analyze_rng_pairs import analyze
ROOT=Path(__file__).resolve().parent
validation=json.loads((ROOT/'rng-pair-observer-validation.json').read_text(encoding='utf-8'))
rows=validation['cases'][0]['trace'];a=analyze(rows,0,fixture=True)
assert not a['helper_result_mismatch_call_ids'] and not a['unpaired_call_ids']
assert a['entry_count']==a['return_count']==83 and a['no_draw_calls']==4
assert len(a['writes_outside_paired_helpers'])==2
changed=deepcopy(rows)
target=next(r for r in changed if r['event']=='rng_return');target['result']+=1
b=analyze(changed,0,fixture=True)
assert b['helper_result_mismatch_call_ids']==[target['call_id']]
incomplete=[r for r in rows if not (r['event']=='rng_return' and r['call_id']==target['call_id'])]
c=analyze(incomplete,0,fixture=True);assert c['unpaired_call_ids']==[target['call_id']]
report={'result':'PASS','complete_native_calls':83,'no_draw_calls':4,'out_of_helper_writes_preserved':2,
        'overlapping_calls_observed_in_fixture':sum(bool(c.get('other_thread_write_sequences')) for c in a['calls']),
        'negative_control_corrupted_result_detected':True,'negative_control_missing_return_remains_incomplete':True,
        'scope':'Analyzer validation against real dedicated-process observations plus deliberate corrupt/missing return controls.'}
(ROOT/'rng-pair-analysis-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
