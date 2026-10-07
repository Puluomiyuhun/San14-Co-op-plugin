"""Publish bounded I2 findings, retaining negative results and missing evidence."""
from collections import Counter
from datetime import datetime
import hashlib, json
from pathlib import Path
from analyze_lockstep import rows

ROOT = Path(__file__).resolve().parent
TRACES = ROOT / 'lockstep-traces'
RUN = TRACES / 'stage-path-run-i2'
OUT = ROOT.parents[1] / 'outputs/san14-link'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
data = rows(RUN/'trace.jsonl')
stages = [r for r in data if r['event']=='stage']
analysis = read(RUN/'stage-path-analysis.json')
comparison = read(RUN/'stage-comparisons.json')
ends = read(RUN/'end-comparisons.json')
next_cell = read(RUN/'next-cell-analysis.json')
worker = read(ROOT/'movement-worker-static-evidence.json')
closeout = read(TRACES/'stage-path-i2-final-closeout.json')
fixtures = read(ROOT/'stage-path-validation.json')
metadata = read(RUN/'metadata.json')
assert analysis['cleanly_detached'] and not analysis['errors']
assert len(stages)==187 and analysis['stage_sequence_matches_prefix'] and not analysis['gate_mismatches']
assert len(analysis['windows'])==6
assert [w['classification'] for w in analysis['windows']]==['TIME_GATE_FALSE']*5+['BATTLE_PHASES_EXECUTED']
window = analysis['windows'][-1]
assert window['built_pair_count']==17 and window['phase_entries']==112 and window['pending_at_stage']==0
assert comparison['run-b']['armies']==[178,179] and comparison['run-b']['cities']==[]
assert all(comparison['run-b'][key]==[] for key in ('date','stage','world_inputs'))
assert len(comparison['run-b']['global_rng'])==187
assert worker['worker_label']['ascii']=='UpdateNextHexIDThread'
assert fixtures['result']=='PASS' and fixtures['observer_sha256']==metadata['observer_sha256']
assert not closeout['debugger_attached'] and closeout['original_strategy_update_restored']
assert closeout['save34_sha256']==closeout['backup_sha256']
assert closeout['comparison']['random_inputs_b']['global_18eb8b0']==3823646826
assert next_cell['rng_target_indices']=={'3900088880':[5], '1138287528':[6], '3823646826':[4]}
for name, value in ends.items():
    if name!='after-run-a.json':
        assert not value['sampled_record_changes_excluding_known_runtime_pointer'], name
        assert value['focused_state_equal'] and value['person_task_sample_equal'], name
assert len(ends['after-run-a.json']['sampled_record_changes_excluding_known_runtime_pointer'])==25

near = next_cell['army_17_nearby']
for name in ('run-b','stage-path-run-i2'):
    selected = [r for r in near[name] if 177<=r['index']<=180]
    assert all(r['actual_cell_2a']==24023 and r['soldiers']==11000 for r in selected)
assert [r['next_cell_48'] for r in near['run-b'] if 177<=r['index']<=180]==[24023,24023,24023,23804]
assert [r['next_cell_48'] for r in near['stage-path-run-i2'] if 177<=r['index']<=180]==[24023,23804,23804,23804]
assert stages[167]['budget_elapsed_ms']==17
assert stages[167]['frame_start_ms']!=stages[168]['frame_start_ms']
assert all(r['subday']==10 and r['rbp']==1 for r in stages[167:169])

expired = rows(TRACES/'stage-path-run-i/trace.jsonl')
assert not any(r.get('event')=='stage' for r in expired)
assert expired[-1]['event']=='detached' and expired[-1]['registers_restored'] and not expired[-1]['captured']

compact_windows = [{k:v for k,v in w.items() if k not in ('phase_sequences','state_changes_to_next_stage')}
                   for w in analysis['windows']]
summary_ends = {name:{'differing_sampled_records':len(v['sampled_record_changes_excluding_known_runtime_pointer']),
    'focused_state_equal':v['focused_state_equal'],'person_task_sample_equal':v['person_task_sample_equal'],
    'random_inputs_equal':v['random_inputs_equal']} for name,v in ends.items()}
manifest_paths = [RUN/n for n in ('metadata.json','trace.jsonl','before.json','stage-path-analysis.json',
    'stage-comparisons.json','end-comparisons.json','transient-differences.json','next-cell-analysis.json')]
manifest_paths += [TRACES/n for n in ('after-stage-path-i2.json','restored-stage-path-i2.json',
    'stage-path-i2-final-closeout.json','old-stage-transition-audit.json','stage-path-run-i/trace.jsonl')]
manifest_paths += [ROOT/n for n in ('observe_stage_path.cpp','observe_stage_path.exe','stage-path-validation.json',
    'stage_path_payload_fixture.cpp','analyze_next_cell_transient.py','inspect_movement_worker.py',
    'movement-worker-static-evidence.json','survey-16cb30.txt','survey-16c1a0.txt','survey-2cd3e0.txt',
    'survey-2a9be0.txt','survey-3f8e10.txt','survey-833cb0.txt','survey-83a070.txt','survey-834d10.txt')]
manifest=[{'path':str(p.relative_to(ROOT)), 'bytes':p.stat().st_size,
    'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in manifest_paths]

report = {'schema':'san14.lockstep-followup.stage-path-and-next-cell.v1',
    'created':datetime.now().astimezone().isoformat(),
    'result':'NORMAL_FIRST_BATCH_TRANSIENT_NEXT_CELL_TIMING_DIFFERENCE_STATIC_WORKER_PATH_FOUND',
    'metadata':metadata, 'event_counts':dict(Counter(r['event'] for r in data)),
    'capture':{k:v for k,v in analysis.items() if k!='windows'},'windows':compact_windows,
    'expired_run_i':{'no_stage_events':True,'cleanly_detached':True,'captured':False},
    'native_frame_boundary':{'stage_12':{k:stages[167][k] for k in ('stage','subday','rbp','frame_start_ms','budget_elapsed_ms')},
        'stage_13':{k:stages[168][k] for k in ('stage','subday','rbp','frame_start_ms','budget_elapsed_ms')},
        'distinct_timer_start_values':len({r['frame_start_ms'] for r in stages}),
        'scope':'Native timer-budget yield does not itself increment or discard the remaining dispatch stage. Does not prove zero debugger interference.'},
    'stage_comparison':{n:{k:{'different_samples':len(v),'first_difference':v[0] if v else None} for k,v in d.items()} for n,d in comparison.items()},
    'end_comparison':summary_ends, 'next_cell':next_cell, 'movement_worker':worker,
    'fixtures':fixtures,
    'restoration':{k:closeout[k] for k in ('date','player','sampled_records','comparison','result','debugger_attached',
        'original_strategy_update_restored','save34_sha256','backup_sha256','restored_diagnostics','rng_state_rewritten')},
    'original_a_root_cause_proven':False,'actual_i2_next_cell_writer_observed':False,
    'complete_world_determinism_proven':False,'two_client_test_performed':False,
    'limits':['I2 did not begin with the same monitored global RNG as B.',
        'Only 187 stage entries captured; end-state equality is not complete battle/animation sequence equality.',
        'No army+48 watchpoint or worker_90 timeline in I2. The static named worker is a candidate producer, not an observed cause.',
        'A did not record actual subday, cached gate, builder result or pending lists. No later normal run can retroactively recover them.',
        'Debugger changes timing; measured handler time excludes OS debug delivery/resume overhead.',
        'No synchronizing patch, worker barrier, RNG isolation or replay correction installed.'],
    'next_bounded_probe':{'purpose':'Identify army+48 producer, completion boundary, and whether movement can consume an unfinished result.',
        'candidate_observations':['Data write watchpoint at validated army17+48 with PC/thread/old/new value and bounded stack',
            'Native callback 16C2C0 entry and return', 'Actual movement consumption at 2A9D94',
            'World date/subday, strategy stage, manager worker_90 and pending_94 at each hit'],
        'interpretation':'Different completion times alone do not disprove determinism if a proper barrier precedes every logical consumer.',
        'status':'Design only; no new recorder armed and no replay requested this turn.'},
    'manifest':manifest}
destination=OUT/'推演调度与移动状态追查第七轮证据.json'
with destination.open('x',encoding='utf-8') as f:f.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert read(destination)==report
print(json.dumps({'evidence':str(destination),'stage_samples':len(stages),'pairs':17,'phases':112,
    'transient_army':17,'worker_name':worker['worker_label']['ascii'],'checks':'PASS'},ensure_ascii=True))
