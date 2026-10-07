"""Version-pinned read-only writer/worker/consumer probe, save34 baseline only."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from datetime import datetime
from lockstep_baseline import BattleObserver,sample
from analyze_lockstep import baseline_difference
from finalize_lockstep_capture import diagnostics
from test_submit_probe import wait_json
from run_reward_execution_pilot import CHECKPOINT
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--seconds',type=int,default=600);args=p.parse_args()
assert args.name.replace('-','').isalnum() and 2<=args.seconds<=900
run=ROOT/'lockstep-traces'/args.name;assert not run.exists(),'Refusing to overwrite capture'
binary=ROOT/'observe_next_cell.exe';sha=hashlib.sha256(binary.read_bytes()).hexdigest()
validation=json.loads((ROOT/'next-cell-validation.json').read_text(encoding='utf-8'))
assert validation['result']=='PASS' and validation['observer_sha256']==sha
reader=BattleObserver()
try:
    before=sample(reader);expected=json.loads((ROOT/'lockstep-traces/restored-stage-path-i2.json').read_text(encoding='utf-8'))
    comparison=baseline_difference(expected,before)
    assert not comparison['sampled_record_changes_excluding_known_runtime_pointer']
    assert all(comparison[k] for k in ('focused_state_equal','person_task_sample_equal'))
    assert before['focused']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
    diag=diagnostics(reader);assert before==sample(reader) and diag==diagnostics(reader)
    base=reader.memory.base;root=reader.pointer(base+0x1fca1e0);unit=reader.pointer(root+0x7df60+17*8)
    reader.require_type(unit,'CArmyUnitData')
    points=(0x16c2c0,0x16c2b7,0x2a9d94)
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    for at in points:assert reader.memory.read(base+at,32)==image[at:at+32],f'Code mismatch {at:x}'
    assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest()=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    run.mkdir()
    for name,data in [('before.json',before),('baseline-check.json',comparison),('before-diagnostics.json',diag)]:
        (run/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    log=run/'trace.jsonl'
    metadata={'created':datetime.now().astimezone().isoformat(),'pid':reader.pid,'base':hex(base),
        'game_exe_sha256':reader.sha256,'observer_sha256':sha,'watch_address':hex(unit+0x48),'watch_size':2,
        'marker_rvas':[hex(r) for r in points],'duration_seconds':args.seconds,
        'baseline_global_rng':before['random_inputs']['global_18eb8b0'],
        'scope':'Read-only hardware watch on army17 next-cell; worker callback entry/return; movement consumption. Debugger affects scheduling.',
        'stop':'After army17 consumption on Aug12, else Aug13 at a marker, 1500 recorded events, cancellation or timeout. Game continues natively.'}
    with (run/'stdout.log').open('wb') as out,(run/'stderr.log').open('wb') as err:
        proc=subprocess.Popen([str(binary),str(reader.pid),hex(base),hex(unit+0x48),*[hex(r) for r in points],str(args.seconds),str(log)],
            stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    metadata['observer_pid']=proc.pid
    (run/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    wait_json(log,'armed')
    print(json.dumps({'armed':True,'observer_pid':proc.pid,'run':str(run),'seconds':args.seconds,'baseline':diag},ensure_ascii=True))
finally:reader.close()
