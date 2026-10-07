"""Start one bounded camera-route observation from save34 planning; never writes game data."""
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
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--seconds',type=int,default=600);p.add_argument('--reference',required=True);args=p.parse_args()
assert args.reference.replace('-','').isalnum()
assert args.name.replace('-','').isalnum() and 2<=args.seconds<=900
run=ROOT/'lockstep-traces'/args.name;assert not run.exists()
binary=ROOT/'observe_camera_rng_watch.exe';sha=hashlib.sha256(binary.read_bytes()).hexdigest()
validation=json.loads((ROOT/'camera-rng-watch-validation.json').read_text())
assert validation['result']=='PASS' and validation['observer_sha256']==sha
r=BattleObserver()
try:
    before=sample(r);expected=json.loads((ROOT/'lockstep-traces'/(args.reference+'.json')).read_text(encoding='utf-8'))
    comparison=baseline_difference(expected,before)
    assert not comparison['sampled_record_changes_excluding_known_runtime_pointer']
    assert all(comparison[k] for k in ('focused_state_equal','person_task_sample_equal','random_inputs_equal'))
    assert before['focused']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
    diag=diagnostics(r);lists=capture_combat_lists(r)
    camera=r.memory.read(r.memory.base+0x19e7690,0x290).hex()
    assert before==sample(r) and diag==diagnostics(r) and lists==capture_combat_lists(r)
    image=(ROOT/'game-runtime-image.bin').read_bytes();points=(0x15b070,0x15b12f,0x3f9344)
    for v in points:assert r.memory.read(r.memory.base+v,32)==image[v:v+32],hex(v)
    assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest()=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    root=r.pointer(r.memory.base+0x1FCA1E0)
    tactic_table=[]
    for identity in range(201):
        address=r.pointer(root+0x76C00+identity*8);r.require_type(address,'CTacticsData')
        raw=r.memory.read(address,0x88)
        tactic_table.append({'id':identity,'address':hex(address),'name':raw[0x10:0x40].decode('utf-16le').split('\0')[0],'raw_hex':raw.hex()})
    assert before==sample(r),'Game changed while capturing tactics table'
    run.mkdir()
    (run/'tactics-table.json').write_text(json.dumps(tactic_table,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,data in [('before.json',before),('baseline-check.json',comparison),('before-diagnostics.json',diag),('before-combat-lists.json',lists)]:
        (run/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    meta={'created':datetime.now().astimezone().isoformat(),'pid':r.pid,'base':hex(r.memory.base),'game_exe_sha256':r.sha256,
        'observer_sha256':sha,'marker_rvas':[hex(v) for v in points],'rng_data_watch_rva':'0x18eb8b0','reference':args.reference,'duration_seconds':args.seconds,'camera_before_hex':camera,
        'baseline_global_rng':before['random_inputs']['global_18eb8b0'],
        'scope':'Tactic dispatch/scene predicate result, all writes to the watched global RNG state, combat gates, camera pose and partial army state. Hardware debugger changes scheduling. No game memory writes/calls.',
        'limits':'Only the known global RNG state is watched; other undiscovered generators remain outside scope. Prior observed value is not guaranteed atomic before-value for racing writers. A predicate pass does not certify scene allocation/completion. Combat samples do not cover every intervening damage or animation.',
        'stop':'Date reaches Aug21, 5000 captured events, cancellation or timeout; detaches and native game continues.'}
    log=run/'trace.jsonl'
    with (run/'stdout.log').open('wb') as stdout,(run/'stderr.log').open('wb') as stderr:
        proc=subprocess.Popen([str(binary),str(r.pid),hex(r.memory.base),'0x15b070',str(args.seconds),str(log)],stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    meta['observer_pid']=proc.pid;(run/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    wait_json(log,'armed');print(json.dumps({'armed':True,'observer_pid':proc.pid,'seconds':args.seconds,'run':str(run),'baseline_rng':meta['baseline_global_rng']},ensure_ascii=True))
finally:r.close()
