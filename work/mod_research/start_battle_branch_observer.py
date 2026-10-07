"""Start the narrow read-only observer from the verified checkpoint34 baseline."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from lockstep_baseline import sample, BattleObserver
from analyze_lockstep import baseline_difference
from finalize_lockstep_capture import diagnostics
from battle_branch_inputs import capture_branch_inputs
from test_submit_probe import wait_json
from run_reward_execution_pilot import CHECKPOINT

ROOT = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('name')
p.add_argument('--seconds', type=int, default=600)
args = p.parse_args()
assert args.name.replace('-', '').isalnum() and 2 <= args.seconds <= 900
fixtures = json.loads((ROOT/'battle-branch-fixtures.json').read_text())
assert len(fixtures) == 3 and all(x['result']=='PASS' for x in fixtures)
run = ROOT/'lockstep-traces'/args.name
assert not run.exists(), 'Refusing to overwrite experiment'
reader = BattleObserver()
try:
    before = sample(reader)
    expected = json.loads((ROOT/'lockstep-traces/run-a/before.json').read_text(encoding='utf-8'))
    comparison = baseline_difference(expected, before)
    assert not comparison['sampled_record_changes_excluding_known_runtime_pointer']
    assert all(comparison[k] for k in ('focused_state_equal','person_task_sample_equal'))
    assert before['focused']['state_stack'] == ['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
    diag = diagnostics(reader)
    assert diag == diagnostics(reader) and before == sample(reader)
    image = (ROOT/'game-runtime-image.bin').read_bytes()
    # RNG mismatch is preserved as evidence; this experiment diagnoses branches, not a matched-start repeatability trial.
    points = (0x3F9344,0x16C685,0x15C045,0x15C0B0)
    for rva in points:
        assert reader.memory.read(reader.memory.base+rva,32) == image[rva:rva+32], f'Code mismatch {rva:x}'
    assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest() == 'afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    branch_inputs = capture_branch_inputs(reader)
    assert branch_inputs == capture_branch_inputs(reader) and before == sample(reader)
    run.mkdir()
    for filename, data in (('before.json',before),('baseline-check.json',comparison),('before-diagnostics.json',diag),('before-branch-inputs.json',branch_inputs)):
        (run/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    binary = ROOT/'observe_battle_branches.exe'
    log = run/'trace.jsonl'
    metadata = {'created':datetime.now().astimezone().isoformat(),'pid':reader.pid,'base':hex(reader.memory.base),
        'exe_sha256':reader.sha256,'observer_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
        'duration_seconds':args.seconds,'trace':str(log),'rvas':[hex(x) for x in points],
        'method':'Hardware execution breakpoints at combat gate, pair rebuild return, per-pair eligibility and phase dispatch. No game code/data writes.',
        'stop':'After day12 subday12 gate, 3000 events, or timeout/cancel; native game continues after detach',
        'limitations':'Debugger affects wall-clock timing; only partial world data sampled.'}
    with (run/'stdout.log').open('wb') as out, (run/'stderr.log').open('wb') as err:
        proc = subprocess.Popen([str(binary),str(reader.pid),hex(reader.memory.base),'0x3f9344',str(args.seconds),str(log)],
            stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    metadata['observer_pid']=proc.pid
    (run/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    wait_json(log,'armed')
    print(json.dumps({'armed':True,'observer_pid':proc.pid,'run':str(run),'duration_seconds':args.seconds,'baseline':diag}))
finally:
    reader.close()
