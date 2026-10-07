"""Audit and publish the native-load trace without publishing raw process stacks."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from analyze_combat_gates import next_rng
from analyze_lockstep import baseline_difference

ROOT=Path(__file__).resolve().parent
TRACES=ROOT/'lockstep-traces'
RUN=TRACES/'load-rng-run-e'
OUT=ROOT.parents[1]/'outputs/san14-link'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
rows=[json.loads(s) for s in (RUN/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
assert rows[-1]=={'event':'detached','captured':True,'registers_restored':True}
assert not any(r['event'].startswith('error') for r in rows)
events=[r for r in rows if r['event'] in ('rng_set','rng_update')]
assert [r['event'] for r in events]==['rng_set']+['rng_update']*6
before,after=read(RUN/'before.json'),read(RUN/'after.json')
previous=before['random_inputs']['global_18eb8b0']
for e in events:
    assert e['before']==previous, 'Unexplained state transition'
    if e['event']=='rng_update':assert next_rng(e['before'])==e['after']
    previous=e['after']
assert previous==after['random_inputs']['global_18eb8b0']
assert events[0]['caller_rva']==0x2f9a72
assert events[0]['after']==4136155758
assert events[-2]['after']==3900088880 and events[-1]['after']==1138287528
comparison=baseline_difference(before,after)
assert not comparison['sampled_record_changes_excluding_known_runtime_pointer']
assert all(comparison[k] for k in ('focused_state_equal','person_task_sample_equal','random_inputs_equal'))
closeout=read(TRACES/'load-rng-e-closeout.json')
assert closeout['result']=='SAMPLED_GAMEPLAY_RESTORED_RNG_DIFFERS'
assert not closeout['debugger_attached'] and closeout['original_strategy_update_restored']
assert closeout['save34_sha256']==closeout['backup_sha256']
stacks={r['seq']:r['unwind'] for r in read(RUN/'unwound-stacks.json')}
messages=read(RUN/'message-resources.json')
message_ids={r['seq']:next((f['observed_message_id'] for f in r['selected'] if 'observed_message_id' in f),None) for r in messages['frames']}
assert [message_ids[i] for i in range(2,8)]==[0x5024,0x502b,0x5024,0x502b,0xc506,0xc506]
timeline=[]
for e in events:
    item={k:v for k,v in e.items() if k not in ('stack_hex','registers','rbx_diagnostic','tick_ms')}
    item['writer_rva']=hex(item['writer_rva']);item['caller_rva']=hex(item['caller_rva'])
    item['ms_after_seed_restore']=e['tick_ms']-events[0]['tick_ms']
    item['message_id']=hex(message_ids[e['seq']]) if message_ids[e['seq']] is not None else None
    item['call_stack_rvas']=[f['pc_rva'] for f in stacks[e['seq']]['frames']]
    item['unwind_stop']=stacks[e['seq']]['stopped']
    if e['seq']==1:item['observed_scope']='Native world deserialization / CLoadState'
    elif e['seq']<=5:item['observed_scope']='CReportActionDlg message generation'
    elif e['seq']==6:item['observed_scope']='CPersonLineManager message 0xC506, nested positional sound/voice variation path'
    else:item['observed_scope']='Same CPersonLineManager message 0xC506, random message expression'
    timeline.append(item)
manifest=[]
paths=[RUN/n for n in ('metadata.json','trace.jsonl','before.json','after.json','before-diagnostics.json','after-diagnostics.json','unwound-stacks.json','message-resources.json')]
paths += [TRACES/'load-rng-e-closeout.json']
paths += [ROOT/n for n in ('observe_load_rng.cpp','observe_load_rng.exe','start_load_rng_observer.py','load-rng-fixtures.json',
                          'unwind_rng_stack.py','test_unwind_rng_stack.py','inspect_load_rng_messages.py',
                          'message-manager-types.json','load-rng-owner-types.json','disasm-2f9a6d.txt','survey-2d4040.txt',
                          'survey-2dcce0.txt','survey-1ab630.txt','survey-1aca10.txt','survey-5ddd40.txt','survey-5dd650.txt')]
for p in paths:
    manifest.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
report={
    'schema':'san14.lockstep-followup.native-load-rng.v1',
    'created':datetime.now().astimezone().isoformat(),
    'result':'POST_LOAD_RNG_CONSUMPTION_LOCALIZED_ORIGINAL_BATTLE_FORK_UNRESOLVED',
    'event_counts':dict(Counter(r['event'] for r in rows)),
    'native_restored_seed':events[0]['after'],
    'previous_planning_baseline':3900088880,
    'current_planning_state':events[-1]['after'],
    'timeline':timeline,
    'chain_checks':{'all_transitions_accounted_for_at_observed_points':True,'all_six_updates_match_algorithm':True,
                    'final_sample_matches_last_observed_write':True},
    'message_identity_evidence':{
        'CMessageManager':'RTTI recorded at RNG breakpoint for five expression calls; static vtable 0x12A7CC8.',
        'message_ids':'Recovered EBX in 0x2D4040 frame; independently checked normalization in prolog and immediate IDs at two report call sites.',
        'report_owner':'Recovered live object pointer identified AFTER capture as CReportActionDlg; callsites 0x5DE3EA and 0x5DD7C5.',
        'person_line_owner':'Recovered singleton pointer base+0x1A38EC8 identified AFTER capture as CPersonLineManager; path 0x1ACA10 -> 0x1AB630 -> 0x1A1C10.',
        'not_proven':'Exact visible line at each RNG call. Post-capture reusable text buffers are not historical message snapshots.',
        'unwind_scope':'Version 1 x64 ordinary frames; decoded call sites checked. No general epilog support. First two report stacks exceed captured window; relevant report frames are within it.',
        'unwind_reference':'https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170',
    },
    'same_load_trial_before_after':comparison,
    'restoration_vs_original_baseline':{k:closeout[k] for k in ('result','date','player','sampled_records','comparison','debugger_attached',
        'original_strategy_update_restored','save34_sha256','backup_sha256','restored_diagnostics','rng_state_rewritten')},
    'infrastructure_fixtures':read(ROOT/'load-rng-fixtures.json'),
    'original_a_root_cause_proven':False,
    'limits':[
        'One instrumented native load in one process, no date advance; no uninstrumented control or second client.',
        'Only known global RNG setter and three writers monitored. No complete RNG inventory or full world capture.',
        'Debugger changes wall-clock scheduling; this trace does not retrospectively identify every earlier run\'s call sequence.',
        'Some draws run on different worker threads. No data race or missing atomic update demonstrated by this trace.',
        'UI/text/voice-related calls use the shared state; this does not prove every call below CMessageManager is presentation-only.',
        'Previous A battle divergence preceded the first observed RNG divergence; current finding is not a proven explanation for A.',
    ],
    'design_implications':[
        'Checkpoint synchronization needs a defined post-load initialization barrier and pending-job accounting.',
        'RNG-domain isolation should be scoped to verified presentation callers, not the entire global RNG or message manager.',
        'With multiple worker threads, save-global-state/restore-on-return is unsafe unless concurrent consumers are excluded; prefer isolated state and explicit execution context.',
        'Retain per-step battle-pair and tactic-event checks; end-of-turn equality cannot certify the animated battle sequence.',
    ],
    'manifest':manifest,
}
destination=OUT/'读档随机偏移定位第三轮证据.json'
destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert read(destination)==report
print(json.dumps({'path':str(destination),'events':len(events),'seed':report['native_restored_seed'],
                  'final_rng':report['current_planning_state'],'records':closeout['sampled_records'],
                  'debugger_attached':closeout['debugger_attached']},ensure_ascii=True))
