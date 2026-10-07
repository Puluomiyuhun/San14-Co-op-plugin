"""Ensure incomplete or wrong-order evidence cannot certify a load path."""
from copy import deepcopy
import json
from pathlib import Path
from analyze_startup_identity import validate_trace
ROOT=Path(__file__).resolve().parent
sample=[json.loads(line) for line in (ROOT/'startup-identity-payload.jsonl').read_text().splitlines()][:6]
tail={'event':'detached','captured':True,'registers_restored':True}
rows=sample+[tail]
assert validate_trace(rows)['native_gameplay_enabled'] is False
results=[{'case':'ordered_synthetic_trace','result':'PASS'}]
bad=[]
bad.append(('still_armed',[{'event':'attached'},{'event':'armed'}]))
bad.append(('missing_worker',[r for r in rows if r['event']!='load_worker_result']))
changed=deepcopy(rows);changed[1]['ebx']=0;bad.append(('load_failed',changed))
changed=deepcopy(rows);changed[3]['event'],changed[4]['event']=changed[4]['event'],changed[3]['event'];bad.append(('unexpected_order',changed))
changed=deepcopy(rows);changed[5]['complete_path_seen']=False;bad.append(('incomplete_path',changed))
changed=deepcopy(rows);changed[-1]['registers_restored']=False;bad.append(('cleanup_not_verified',changed))
changed=deepcopy(rows);changed[5]['world_context']['force']=2;bad.append(('unexpected_identity_change',changed))
changed=deepcopy(rows);changed[5]['state_context']['field_478_raw']=0;bad.append(('missing_user_ui',changed))
for name,value in bad:
    try:validate_trace(value)
    except ValueError:results.append({'case':name,'result':'PASS'})
    else:raise AssertionError(name)
report={'result':'PASS','cases':results,'scope':'Synthetic parser guards only; no actual load-order proof.'}
(ROOT/'startup-identity-analysis-tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','cases':len(results)}))
