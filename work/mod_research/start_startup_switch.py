"""Bounded checkpoint34 Zhang Lu -> Liu Bei load-time identity pilot.

Only --execute arms the one-shot Title selection write. No automatic game
loading/turn advance. The original save is never modified by this tool.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from run_second_force_reward import BattleObserver,capture,CHECKPOINT
from startup_identity_reader import capture_startup_context
from test_submit_probe import wait_json
ROOT=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
JOURNAL=ROOT/'startup-switch-live-once.json'
CHECKPOINT_SHA='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'

def no_debugger(reader):
    k=reader.memory.k;k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)];k.CheckRemoteDebuggerPresent.restype=W.BOOL
    attached=W.BOOL();assert k.CheckRemoteDebuggerPresent(reader.memory.handle,C.byref(attached)) and not attached.value

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--idle-check',action='store_true')
    parser.add_argument('--seconds',type=int,default=900)
    args=parser.parse_args();assert 2<=args.seconds<=900
    if args.idle_check:assert not args.execute and args.seconds<=5
    if args.execute:assert not JOURNAL.exists(),'A live handoff has already been reserved; no automatic retry'
    binary=ROOT/'startup_identity_switch.exe';binary_sha=sha(binary)
    fixture=load(ROOT/'startup-switch-fixture-tests.json');infra=load(ROOT/'startup-switch-lifecycle-tests.json')
    assert fixture['result']=='PASS' and len(fixture['cases'])==18 and fixture['binary_sha256']==binary_sha
    assert len(infra)==3 and all(r['result']=='PASS' for r in infra)
    if args.execute:
        idle=load(ROOT/'startup-switch-idle-check.json')
        assert idle['result']=='PASS' and idle['binary_sha256']==binary_sha
        assert load(ROOT/'startup-switch-analysis-tests.json')['result']=='PASS'
    profile=load(ROOT/'startup-switch-profile.json');image=(ROOT/'game-runtime-image.bin').read_bytes()
    assert profile['checkpoint_sample_stage']=='title_selection_boundary'
    assert sha(ROOT/'startup-load-boundary-baseline.json')==profile['checkpoint_sample_sha256']
    assert load(ROOT/'load-boundary-baseline-tests.json')['result']=='PASS'
    reader=BattleObserver()
    try:
        no_debugger(reader);before=capture(reader);ctx=capture_startup_context(reader)
        assert reader.sha256==profile['game_sha256']
        assert ctx['snapshot']['player']['force_id']==12 and ctx['snapshot']['player']['ruler_id']==666
        assert ctx['snapshot']['date']=={'year':203,'month':8,'day':11,'period':'中旬'}
        assert ctx['snapshot']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
        assert ctx['state_sample']['phase_raw']==2 and ctx['world_mode']==1
        assert sha(CHECKPOINT)==sha(ROOT.parent/'mod_test/replay-checkpoint-34/svdexSC34.s14')==CHECKPOINT_SHA
        for row in profile['code_ranges']:
            a,z=row['start_rva'],row['end_rva'];actual=reader.memory.read(reader.memory.base+a,z-a)
            assert actual==image[a:z] and hashlib.sha256(actual).hexdigest()==row['sha256']
        assert before==capture(reader) and ctx==capture_startup_context(reader),'Current checkpoint is changing'
        folder=ROOT/'startup-switch-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
        save(folder/'before.json',before);save(folder/'context-before.json',ctx)
        log=folder/'trace.jsonl'
        meta={'created':datetime.now().astimezone().isoformat(),'directory':str(folder),'pid':reader.pid,'base':hex(reader.memory.base),
              'game_sha256':reader.sha256,'checkpoint34_sha256':CHECKPOINT_SHA,'binary_sha256':binary_sha,
              'execute':args.execute,'duration_seconds':args.seconds,'trace':str(log),'attempt_journal':str(JOURNAL),
              'checkpoint_sample_stage':profile['checkpoint_sample_stage'],'checkpoint_sample_sha256':profile['checkpoint_sample_sha256'],
              'target_force':2,'target_ruler':952,'gameplay_enabled':False,
              'write_scope':('Exactly the Title selected force/ruler pointers (+4A0/+4A8), before native MOV RCX at 4DA3B2. No code/world/player-byte patch or extra native call.' if args.execute else 'Read-only process access; record all sample differences at the title boundary, no identity or game-data write.'),
              'recovery':'After collecting result, native load34 restores original player. Never automatically retry a reserved attempt.',
              'stop':('First target user update, rejection, timeout, or trace.jsonl.stop; no persistent adapter remains.' if args.execute else 'After the title-boundary sample check, rejection, timeout, or trace.jsonl.stop; normal Zhang Lu load continues.')}
        save(folder/'metadata.json',meta)
        with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
            proc=subprocess.Popen([str(binary),str(reader.pid),hex(reader.memory.base),'0x2ee64c',str(args.seconds),str(log),
                'execute' if args.execute else 'dry',str(JOURNAL)],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        meta['observer_pid']=proc.pid;save(folder/'metadata.json',meta)
        try:
            wait_json(log,'armed')
            if args.idle_check:
                proc.wait(timeout=10);rows=[json.loads(s) for s in log.read_text().splitlines()]
                assert proc.returncode==4 and rows[-1]=={'event':'detached','captured':False,'registers_restored':True}
                no_debugger(reader);assert before==capture(reader) and ctx==capture_startup_context(reader)
                assert not JOURNAL.exists() and sha(CHECKPOINT)==CHECKPOINT_SHA
                result={**meta,'result':'PASS','no_game_data_write':True}
                save(folder/'idle-result.json',result);save(ROOT/'startup-switch-idle-check.json',result)
            else:
                result={**meta,'result':'ARMED_AWAITING_USER_LOAD34' if args.execute else 'ARMED_READ_ONLY_CHECKPOINT_DIAGNOSTIC'};save(ROOT/'startup-switch-active.json',result)
            print(json.dumps(result,ensure_ascii=True,indent=2))
        except BaseException:
            if proc.poll() is None:
                Path(str(log)+'.stop').write_text('stop',encoding='ascii');proc.wait(timeout=10)
            raise
    finally:reader.close()

if __name__=='__main__':main()
