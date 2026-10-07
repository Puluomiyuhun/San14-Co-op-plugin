"""Version-checked, bounded native call/return observation. No game data writes."""
import argparse,hashlib,json,subprocess
from datetime import datetime
from pathlib import Path
from lockstep_baseline import BattleObserver,sample
from analyze_lockstep import baseline_difference
from capture_sync_boundary import capture as boundary_capture
from test_submit_probe import wait_json
from run_reward_execution_pilot import CHECKPOINT
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--seconds',type=int,default=600);a=p.parse_args()
assert a.name.replace('-','').isalnum() and 2<=a.seconds<=900
folder=ROOT/'lockstep-traces'/a.name;assert not folder.exists()
binary=ROOT/'observe_rng_pairs.exe'
validation=json.loads((ROOT/'rng-pair-observer-validation.json').read_text())
assert validation['result']=='PASS' and validation['observer_sha256']==hashlib.sha256(binary.read_bytes()).hexdigest()
r=BattleObserver()
try:
    assert r.sha256=='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
    before=sample(r);boundary=boundary_capture(r)
    assert boundary['candidate_idle'],'Known candidate boundary not idle; no attachment'
    original=json.loads((ROOT/'lockstep-traces'/'run-a'/'before.json').read_text(encoding='utf-8'))
    comparison=baseline_difference(original,before)
    assert not comparison['sampled_record_changes_excluding_known_runtime_pointer']
    assert comparison['focused_state_equal'] and comparison['person_task_sample_equal']
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    fingerprints=[]
    for start,end in [(0x3aa3f0,0x3aa458),(0x3aa7c0,0x3aa818),(0x1ab6f4,0x1ab6f9),
                      (0x2d9243,0x2d9248),(0x2d9261,0x2d9266),(0x3b3774,0x3b3779)]:
        data=r.memory.read(r.memory.base+start,end-start);assert data==image[start:end]
        fingerprints.append({'start_rva':hex(start),'length':end-start,'sha256':hashlib.sha256(data).hexdigest()})
    assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest()=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    assert before==sample(r),'Game changed during preflight'
    folder.mkdir()
    for filename,data in [('before.json',before),('boundary-before.json',boundary),('comparison-with-original-a.json',comparison)]:
        (folder/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log=folder/'trace.jsonl'
    meta={'created':datetime.now().astimezone().isoformat(),'pid':r.pid,'base':hex(r.memory.base),'duration_seconds':a.seconds,
          'game_exe_sha256':r.sha256,'observer_sha256':validation['observer_sha256'],'instruction_fingerprints':fingerprints,
          'baseline_rng':before['random_inputs'],'mode':'NATIVE_OBSERVATION_ONLY_NO_DLL_OR_GAME_PATCH',
          'stop':'600-second default timeout, explicit .stop file, or 12000 events. Date alone does not stop capture; include end-of-turn reports.',
          'limits':['Debugger pauses and changes scheduling. No conclusion that a future DLL wrapper preserves timing.',
                    'Only two helper entries and the known global seed address are instrumented.',
                    'Entry/return global seed snapshots may span other-thread writes; post-store registers and call IDs retained.',
                    'Candidate idle and 783 sampled records do not certify full-world equality or a synchronization barrier.']}
    with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
        proc=subprocess.Popen([str(binary),str(r.pid),hex(r.memory.base),hex(r.memory.base+0x3aa7c0),hex(r.memory.base+0x3aa3f0),hex(r.memory.base+0x18eb8b0),str(a.seconds),str(log)],
                              stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    meta['observer_pid']=proc.pid;(folder/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try:wait_json(log,'armed')
    except Exception:
        Path(str(log)+'.stop').write_text('startup failed; detach');proc.wait(timeout=15);raise
    print(json.dumps({'armed':True,'observer_pid':proc.pid,'run':str(folder),'seconds':a.seconds,'baseline_rng':meta['baseline_rng']},ensure_ascii=True))
finally:r.close()
