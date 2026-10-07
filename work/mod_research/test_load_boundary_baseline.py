"""Check lossless stage reconstruction and reject incomplete/corrupt evidence."""
from copy import deepcopy
from pathlib import Path
import json
from prepare_load_boundary_baseline import ROOT,REFERENCE,load,save,reconstruct
report=load(ROOT/'startup-checkpoint-diagnostic-latest.json')
reference=load(REFERENCE);comparison=report['boundary_comparison']
planning=load(Path(report['directory'])/'after-diagnostic.json')
assert reconstruct(reference,comparison,planning)==load(ROOT/'startup-load-boundary-baseline.json')['records']
tests=[{'case':'exact_reconstruction_of_recorded_stage','result':'PASS'}]
cases=[]
def bad(name,fn):
    c=deepcopy(comparison);p=deepcopy(planning);fn(c,p);cases.append((name,c,p))
bad('wrong_stage',lambda c,p:c.update(stage='first_user_update'))
bad('incomplete_sample',lambda c,p:c.update(checked_records=782))
bad('unreadable_object',lambda c,p:c.update(unreadable_records=1))
bad('missing_diff_record',lambda c,p:c['differences'].pop())
bad('incorrect_byte_count',lambda c,p:c.update(different_bytes=c['different_bytes']+1))
bad('incorrect_expected_byte',lambda c,p:c['differences'][0]['changes'][0].update(expected=17))
bad('out_of_bounds_offset',lambda c,p:c['differences'][0]['changes'][0].update(object_offset=1000000))
bad('invalid_actual_byte',lambda c,p:c['differences'][0]['changes'][0].update(actual=256))
def duplicate(c,p):
    row=deepcopy(c['differences'][0]);c['differences'].append(row);c['different_records']+=1;c['different_bytes']+=len(row['changes'])
bad('duplicate_object',duplicate)
def pointer(c,p):
    row=next(r for r in c['differences'] if r['table_rva']==0x7DF60)
    row['changes'][0]['object_offset']=0x148
bad('excluded_pointer_not_observed',pointer)
def not_returned(c,p):
    row=c['differences'][0];kind={0xDAA8:'city',0x7DF60:'army'}[row['table_rva']];key=f"{kind}:{row['id']}"
    b=bytearray.fromhex(p['records'][key]);b[row['changes'][0]['object_offset']-0x10]^=1;p['records'][key]=b.hex()
bad('did_not_return_on_map',not_returned)
for name,c,p in cases:
    try:reconstruct(reference,c,p)
    except ValueError:tests.append({'case':name,'result':'PASS'})
    else:raise AssertionError(name)
result={'result':'PASS','cases':tests,'scope':'Offline data reconstruction only; not a second live sample at the load boundary.'}
save(ROOT/'load-boundary-baseline-tests.json',result)
print(json.dumps({'result':'PASS','cases':len(tests)}))
