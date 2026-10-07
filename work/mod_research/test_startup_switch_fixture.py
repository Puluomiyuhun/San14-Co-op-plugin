"""Isolated guard/write/native-initializer checks. Never opens SAN14."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'identity-pair-traces/20261006-012420-879770/input.bin'
assert hashlib.sha256(INPUT.read_bytes()).hexdigest()=='e87afe9317b9059eb222a93e53a397e1aea6960fb88652685fb8a41297b113d3'
folder=ROOT/'startup-switch-fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
folder.mkdir(parents=True)
cases=('execute','dry','wrong_instruction','wrong_order','wrong_title_type','wrong_stack','wrong_pair',
       'wrong_date','wrong_mode','wrong_ruler','wrong_district','wrong_rank','wrong_code','readonly_title',
       'existing_journal','repeat_blocked','wrong_checkpoint','wrong_load_phase')
rows=[]
for case in cases:
    p=subprocess.run([str(ROOT/'startup_switch_fixture.exe'),str(INPUT),case,str(folder/(case+'.once.json')),
                      str(folder/(case+'.trace.jsonl'))],capture_output=True,text=True,timeout=15,
                     creationflags=subprocess.CREATE_NO_WINDOW)
    (folder/(case+'.stdout')).write_text(p.stdout,encoding='utf-8')
    (folder/(case+'.stderr')).write_text(p.stderr,encoding='utf-8')
    assert p.returncode==0,(case,p.returncode,p.stdout,p.stderr)
    row=json.loads(p.stdout);assert row['result']=='PASS' and row['game_process_access'] is False
    trace=[json.loads(line) for line in (folder/(case+'.trace.jsonl')).read_text().splitlines()]
    diagnostics=[r for r in trace if r['event']=='checkpoint_sample_comparison']
    if case in ('execute','dry','readonly_title','existing_journal','repeat_blocked','wrong_checkpoint','wrong_load_phase'):
        assert len(diagnostics)==1
        diagnostic=diagnostics[0]
        assert diagnostic['checked_records']==783 and diagnostic['unreadable_records']==0
        if case=='wrong_checkpoint':
            assert diagnostic['different_records']==diagnostic['different_bytes']==2
            assert {(r['table_rva'],r['id'],r['changes'][0]['object_offset']) for r in diagnostic['differences']}=={(0x148,952,0x120),(0xDAA8,13,0x34)}
            row['all_mismatch_details_verified']=True
        elif case=='wrong_load_phase':
            assert diagnostic['different_records']==1 and diagnostic['different_bytes']>0
            changed=diagnostic['differences'][0]
            assert changed['table_rva']==0xDAA8 and changed['id']==13
            assert all(0xA0<=d['object_offset']<0xA4 and d['expected']==0 for d in changed['changes'])
            row['stage_specific_fields_still_checked']=True
        else:assert not diagnostic['differences'] and diagnostic['different_records']==diagnostic['different_bytes']==0
    rows.append(row)
result={'result':'PASS','created':datetime.now().astimezone().isoformat(),'directory':str(folder),'cases':rows,
        'binary_sha256':hashlib.sha256((ROOT/'startup_identity_switch.exe').read_bytes()).hexdigest(),
        'fixture_sha256':hashlib.sha256((ROOT/'startup_switch_fixture.exe').read_bytes()).hexdigest(),
        'scope':'Synthetic title/load stack with captured world/person/force data; actual copied native identity initializer runs in two isolated cases. No real game load or menu test.'}
(ROOT/'startup-switch-fixture-tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','cases':len(rows),'copied_native_initializer_calls':sum(r['native_initializer_calls'] for r in rows),'game_access':False}))
