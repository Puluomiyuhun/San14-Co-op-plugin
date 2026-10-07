"""Start a bounded, read-only first-day trace with diagnostic branch coverage."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from datetime import datetime
from lockstep_baseline import BattleObserver,sample
from analyze_lockstep import baseline_difference
from finalize_lockstep_capture import diagnostics
from combat_list_inputs import capture_combat_lists
from test_submit_probe import wait_json
from run_reward_execution_pilot import CHECKPOINT
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--seconds',type=int,default=600);args=p.parse_args()
assert args.name.replace('-','').isalnum() and 2<=args.seconds<=900
run=ROOT/'lockstep-traces'/args.name;assert not run.exists(),'Refusing to overwrite experiment'
binary=ROOT/'observe_stage_path.exe';sha=hashlib.sha256(binary.read_bytes()).hexdigest()
validation=json.loads((ROOT/'stage-path-validation.json').read_text())
assert validation['result']=='PASS' and validation['observer_sha256']==sha
reader=BattleObserver()
try:
    before=sample(reader);expected=json.loads((ROOT/'lockstep-traces/combat-inputs-final-h.json').read_text(encoding='utf-8'))
    comparison=baseline_difference(expected,before)
    assert not comparison['sampled_record_changes_excluding_known_runtime_pointer']
    assert all(comparison[k] for k in ('focused_state_equal','person_task_sample_equal'))
    assert before['focused']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
    diag=diagnostics(reader);lists=capture_combat_lists(reader)
    assert before==sample(reader) and diag==diagnostics(reader) and lists==capture_combat_lists(reader)
    image=(ROOT/'game-runtime-image.bin').read_bytes();points=(0x3F9219,0x16C640,0x16C685,0x15C0B0)
    for rva in points:assert reader.memory.read(reader.memory.base+rva,32)==image[rva:rva+32],f'Code mismatch {rva:x}'
    assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest()=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    run.mkdir()
    for name,data in [('before.json',before),('baseline-check.json',comparison),('before-diagnostics.json',diag),('before-combat-lists.json',lists)]:
        (run/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    log=run/'trace.jsonl'
    metadata={'created':datetime.now().astimezone().isoformat(),'pid':reader.pid,'base':hex(reader.memory.base),
        'game_exe_sha256':reader.sha256,'observer_sha256':sha,'rvas':[hex(r) for r in points],
        'duration_seconds':args.seconds,'trace':str(log),'baseline_global_rng':before['random_inputs']['global_18eb8b0'],
        'scope':'Old full per-stage army/city sampling plus actual subday, cached gate, timer budget, pending flags, generated pairs and phase entries; no game code/data writes or calls.',
        'stop':'First observed stage with day 11 subday >=12 or later date; timeout/cancel also detach. Native game continues.',
        'timing_limit':'Added breakpoint hits and reads change instrumentation cost; this is not an identical-timing replay of A or proof of zero interference.'}
    with (run/'stdout.log').open('wb') as out,(run/'stderr.log').open('wb') as err:
        proc=subprocess.Popen([str(binary),str(reader.pid),hex(reader.memory.base),'0x3f9219',str(args.seconds),str(log)],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    metadata['observer_pid']=proc.pid
    (run/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    wait_json(log,'armed')
    print(json.dumps({'armed':True,'observer_pid':proc.pid,'run':str(run),'seconds':args.seconds,'baseline':diag},ensure_ascii=True))
finally:reader.close()
