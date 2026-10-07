"""Arm write watches from a verified checkpoint34 planning screen."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from lockstep_baseline import sample, BattleObserver
from analyze_lockstep import baseline_difference
from battle_branch_inputs import capture_branch_inputs
from finalize_lockstep_capture import diagnostics
from test_submit_probe import wait_json
from run_reward_execution_pilot import CHECKPOINT
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--seconds',type=int,default=600);args=p.parse_args()
assert args.name.replace('-','').isalnum() and 2<=args.seconds<=900
fixtures=json.loads((ROOT/'pending-watch-fixtures.json').read_text())
assert len(fixtures)==3 and all(x['result']=='PASS' for x in fixtures)
run=ROOT/'lockstep-traces'/args.name
assert not run.exists(),'Refusing to overwrite experiment'
reader=BattleObserver()
try:
    before=sample(reader)
    expected=json.loads((ROOT/'lockstep-traces/run-a/before.json').read_text(encoding='utf-8'))
    comparison=baseline_difference(expected,before)
    assert not comparison['sampled_record_changes_excluding_known_runtime_pointer']
    assert all(comparison[k] for k in ('focused_state_equal','person_task_sample_equal'))
    assert before['focused']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
    diag=diagnostics(reader);aux=capture_branch_inputs(reader)
    assert diag==diagnostics(reader) and before==sample(reader) and aux==capture_branch_inputs(reader)
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    code_points=(0x3AA3E0,0x3F9344,0x16C640,0x16C6A7,0x166BAF)
    for rva in code_points:
        assert reader.memory.read(reader.memory.base+rva,32)==image[rva:rva+32],f'Code mismatch {rva:x}'
    assert reader.pointer(reader.memory.base+0x12CC4A8+0x28)==reader.memory.base+0x3F9B00
    assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest()=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    run.mkdir()
    for name,data in [('before.json',before),('baseline-check.json',comparison),('before-diagnostics.json',diag),('before-branch-inputs.json',aux)]:
        (run/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    binary=ROOT/'observe_pending_writes.exe';log=run/'trace.jsonl'
    points=(0x1A24D84,0x1A38AB8,0x3AA3E0,0x3F9344)
    metadata={'created':datetime.now().astimezone().isoformat(),'pid':reader.pid,'base':hex(reader.memory.base),
        'exe_sha256':reader.sha256,'observer_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
        'duration_seconds':args.seconds,'trace':str(log),'rvas':[hex(x) for x in points],
        'method':'Two four-byte hardware WRITE breakpoints (pending94/effects98), RNG setter/load marker and combat gate execution markers. Raw thread/register/stack observations. No game code/data writes.',
        'stop':'After Aug12 subday12 gate or 3000 observations or timeout/cancel; native game continues after detach.',
        'limitations':['Debugging affects timing.','Only partial world sampled.','previous_observed is the last sampled value, not an atomic before-store value.','No load residue cause is assumed.'],
        'references':['https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/ba--break-on-access-',
                      'https://cdrdv2-public.intel.com/858456/253669-088-sdm-vol-3b.pdf']}
    with (run/'stdout.log').open('wb') as out,(run/'stderr.log').open('wb') as err:
        proc=subprocess.Popen([str(binary),str(reader.pid),hex(reader.memory.base),*[hex(x) for x in points],str(args.seconds),str(log)],
            stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    metadata['observer_pid']=proc.pid
    (run/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    try:wait_json(log,'armed')
    except Exception:
        Path(str(log)+'.stop').write_text('stop');proc.wait(timeout=15);raise
    print(json.dumps({'armed':True,'observer_pid':proc.pid,'run':str(run),'duration_seconds':args.seconds,'baseline':diag}))
finally:reader.close()
