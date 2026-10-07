"""Publish actual branch observations and separately scoped native-function fixtures."""
from collections import Counter
from datetime import datetime
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TRACES=ROOT/'lockstep-traces'
RUN=TRACES/'branch-run-f'
OUT=ROOT.parents[1]/'outputs/san14-link'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
analysis=read(RUN/'branch-analysis.json')
closeout=read(TRACES/'branch-f-closeout.json')
ends=read(RUN/'end-comparisons.json')
before=read(RUN/'before-branch-inputs.json')
restored=read(RUN/'restored-branch-inputs.json')
fixtures=[json.loads(s) for s in (ROOT/'native-gate-fixture-results.jsonl').read_text(encoding='utf-8-sig').splitlines()]
assert len(fixtures)==6 and all(r['result']=='PASS' for r in fixtures)
assert not analysis['consistency_issues'] and analysis['event_counts']['pair_phase']==224
assert all(not x['sampled_record_changes_excluding_known_runtime_pointer'] and x['focused_state_equal'] and x['person_task_sample_equal'] for x in ends.values())
assert all(x['different_fields']==['global_rng'] for x in analysis['gate_comparison_to_c'])
assert not closeout['debugger_attached'] and closeout['save34_sha256']==closeout['backup_sha256']
identity=lambda p:[[p[k]['type'],p[k]['id']] for k in ('a','b')]
assert [identity(p) for p in before['pairs']]==[identity(p) for p in restored['pairs']]
unmapped=[]
for left,right in zip(before['pairs'],restored['pairs']):
    for side in ('a','b'):
        assert {k:v for k,v in left[side].items() if k!='record_00_18_hex'}=={k:v for k,v in right[side].items() if k!='record_00_18_hex'}
        a=bytes.fromhex(left[side]['record_00_18_hex']);b=bytes.fromhex(right[side]['record_00_18_hex'])
        changes=[{'offset':hex(i),'before':x,'after':y} for i,(x,y) in enumerate(zip(a,b)) if x!=y]
        if changes:unmapped.append({'pair':identity(left),'side':side,'changes':changes})
for k in before:
    if k!='pairs':assert before[k]==restored[k]
active=[r for r in analysis['batches'] if r['gate'].get('rbp_gate')]
assert len(active)==2
summary=[]
for r in active:
    summary.append({'date_subday':r['key'],'pairs_observed':len(r['pair_checks']),
                    'eligible':sum(p['eligible_before_special_filter'] for p in r['pair_checks']),
                    'phase_histogram':[{'phases':list(k),'pairs':v} for k,v in Counter(tuple(p['phases']) for p in r['pair_checks']).items()],
                    'skipped_pairs':[p for p in r['pair_checks'] if not p['phases']],
                    'army_troop_delta_to_next_gate':r.get('army_troop_delta_to_next_gate')})
paths=[RUN/n for n in ('metadata.json','trace.jsonl','before.json','after.json','restored.json','before-branch-inputs.json','after-branch-inputs.json','restored-branch-inputs.json','branch-analysis.json','end-comparisons.json')]
paths += [TRACES/'branch-f-closeout.json']
paths += [ROOT/n for n in ('observe_battle_branches.cpp','observe_battle_branches.exe','battle_branch_inputs.py','start_battle_branch_observer.py','battle-branch-fixtures.json',
    'native_gate_fixture.cpp','native_gate_fixture.exe','native_gate_fixture_code.h','native-gate-fixture-source.json','native-gate-fixture-results.jsonl',
    'survey-15be80.txt','survey-29a000.txt','survey-43f160.txt','survey-16c640.txt','survey-161020.txt','survey-16c160.txt')]
manifest=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
report={
    'schema':'san14.lockstep-followup.pair-branches.v1','created':datetime.now().astimezone().isoformat(),
    'result':'NORMAL_BATCH_FLOW_RECORDED_PENDING_BRANCH_REPRODUCED_IN_ISOLATED_FIXTURE_ORIGINAL_A_UNRESOLVED',
    'real_game_summary':summary,'real_game_analysis':analysis,'end_comparisons':ends,
    'additional_restoration':{'all_nonpair_fields_equal':True,'pair_identity_order_equal':True,'decoded_pair_fields_equal':True,
        'raw_pair_records_equal':not unmapped,'unmapped_byte_differences':unmapped,
        'note':'Differences confined in this comparison to side-record offsets +2,+3,+9; construction writes adjacent typed fields, suggesting padding. Not proven unused everywhere and not silently excluded from full equality.'},
    'restoration':{k:closeout[k] for k in ('result','date','player','sampled_records','comparison','debugger_attached','original_strategy_update_restored','save34_sha256','backup_sha256','restored_diagnostics','rng_state_rewritten')},
    'isolated_native_fixture':{
        'source':read(ROOT/'native-gate-fixture-source.json'),'cases':fixtures,
        'proven':'With identical stubbed available-pair inputs, setting pending_94=1 while effect_count=0 selects a native branch that clears the flag, performs presentation cleanup, returns zero, and never calls pair rebuild or batch processing. The next call processes normally.',
        'not_proven':'That original A entered with pending_94=1, that a real load leaves it set, or that all battle results are recreated. Native external dependencies are replaced by local counted stubs.',
        'game_access':False,
    },
    'infrastructure_fixtures':read(ROOT/'battle-branch-fixtures.json'),
    'original_a_root_cause_proven':False,
    'next_step':'Observe all writes to pending_94 across native load and return-to-planning boundaries, together with the first combat gate. Do not clear it blindly; avoid more normal turns without evidence of a changed candidate input.',
    'manifest':manifest,
}
destination=OUT/'交战分支追查第四轮证据.json'
destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert read(destination)==report
print(json.dumps({'path':str(destination),'actual_batches':len(summary),'native_fixture_cases':len(fixtures),'unmapped_pair_records':len(unmapped),'debugger_attached':closeout['debugger_attached']},ensure_ascii=True))
