"""Payload and classification checks using synthetic memory, never the game."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
from analyze_first_batch import analyze

ROOT = Path(__file__).resolve().parent
log = ROOT/'first-batch-payload-validated.jsonl'
assert not log.exists(), 'Do not overwrite evidence'
proc = subprocess.run([str(ROOT/'first_batch_payload_fixture.exe'),str(log)], capture_output=True, text=True, check=True)
native = json.loads(proc.stdout)
assert native['result'] == 'PASS'
events = [json.loads(x) for x in log.read_text().splitlines()]
assert [r['event'] for r in events] == ['combat_gate','combat_gate','combat_entry','pairs_ready','pair_eligibility','casualty_request','batch_boundary']
assert events[1]['subday'] == 10 and events[1]['rbp_gate'] == 1
assert events[3]['build_result'] == 1 and events[3]['pair_count'] == len(events[3]['pairs']) == 1
assert events[4]['resolved_forces'] == [1,2] and events[4]['eligibility_before_special_filter'] == 1
assert [events[5][x] for x in ('target_kind','target_id','amount','source_kind','source_id')] == [27,2,11,27,1]
assert len(events[-1]['forces']) == 52 and len(events[-1]['input_lists']) == 5
assert events[-1]['input_lists'][0]['entries'] == [1,2]
assert events[-1]['stage'] == 13

def wrap(ev):
    ev = deepcopy(ev)
    for i,r in enumerate(ev,1): r['seq'] = i
    return [{'event':'attached'}, {'event':'armed'}] + ev + [{'event':'detached','captured':True,'registers_restored':True}]

checks = []
def expect(name, ev, status, branch=None):
    actual = analyze(ev)
    assert actual['status'] == status and actual['branch'] == branch, (name,actual)
    checks.append({'case':name,'result':'PASS','classification':status,'branch':branch})
expect('damage observed',wrap(events),'COMPLETE','casualty_requests_observed')
expect('missing boundary',wrap(events[:-1]),'INCOMPLETE')
expect('missing detach',wrap(events)[:-1],'INCOMPLETE')
expect('observer error',wrap(events)+[{'event':'error'}],'INVALID')
expect('missing build event',wrap([r for r in events if r['event']!='pairs_ready']),'INVALID')
expect('missing function entry',wrap([r for r in events if r['event']!='combat_entry']),'INVALID')
ev = deepcopy(events[:2]+events[-1:]);ev[1]['rbp_gate']=0
expect('closed time gate',wrap(ev),'COMPLETE','time_gate_closed')
ev = deepcopy(events[:3]+events[-1:]);ev[2]['pending_94']=1
expect('pending bypass',wrap(ev),'COMPLETE','pending_path_without_rebuild')
ev = deepcopy(events[:4]+events[-1:]);ev[3]['build_result']=0
expect('builder returned zero',wrap(ev),'COMPLETE','builder_returned_zero')
ev = deepcopy(events[:4]+events[-1:]);ev[3]['pair_count']=0;ev[3]['pairs']=[]
expect('empty build list',wrap(ev),'COMPLETE','rebuilt_list_empty')
ev = deepcopy(events[:5]+events[-1:]);ev[4]['eligibility_before_special_filter']=0
expect('all filtered before special filter',wrap(ev),'COMPLETE','all_pairs_rejected_before_special_filter')
expect('eligible without damage',wrap(events[:5]+events[-1:]),'COMPLETE','pairs_built_without_observed_casualty_requests')
ev = wrap(events);ev[4]['seq']=999
expect('lost event',ev,'INVALID')
report = {'result':'PASS','scope':'Synthetic payloads and classifier; not a live combat or hardware adaptation test',
          'native':native,'checks':checks,
          'artifacts':[{'name':name,'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()}
                       for name in ('first_batch_observe.inc','observe_first_batch.exe','first_batch_payload_fixture.exe','analyze_first_batch.py')]}
with (ROOT/'first-batch-payload-validation.json').open('x',encoding='utf-8') as f: json.dump(report,f,indent=2)
print(json.dumps({'result':'PASS','classification_cases':len(checks),'native':native}))
