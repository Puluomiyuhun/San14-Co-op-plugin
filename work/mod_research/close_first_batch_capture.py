"""Save a stable planning endpoint and verify narrow observer cleanup, read-only."""
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from lockstep_baseline import sample, BattleObserver
from battle_branch_inputs import capture_branch_inputs
from run_reward_execution_pilot import CHECKPOINT
from analyze_first_batch import analyze

ROOT=Path(__file__).resolve().parent
name=sys.argv[1]
assert name.replace('-','').isalnum()
folder=ROOT/'lockstep-traces'/name
assert not (folder/'closeout.json').exists()
trace=[json.loads(x) for x in (folder/'trace.jsonl').read_text().splitlines()]
analysis=analyze(trace)
assert analysis['status']=='COMPLETE',analysis
assert not (folder/'stderr.log').read_text()
reader=BattleObserver()
try:
    end=sample(reader)
    assert end['focused']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
    date=end['focused']['critical_state']['date']
    assert (date['year'],date['month'],date['day'])==(203,8,21)
    branch=capture_branch_inputs(reader)
    assert end==sample(reader) and branch==capture_branch_inputs(reader)
    k=reader.memory.k
    k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)]
    k.CheckRemoteDebuggerPresent.restype=W.BOOL
    debugged=W.BOOL()
    assert k.CheckRemoteDebuggerPresent(reader.memory.handle,C.byref(debugged))
    assert not debugged.value
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    points=(0x3F9344,0x3F935F,0x16C640,0x16C685,0x16AC60,0x15C045)
    assert all(reader.memory.read(reader.memory.base+rva,32)==image[rva:rva+32] for rva in points)
    assert reader.pointer(reader.memory.base+0x12CC4A8+0x28)==reader.memory.base+0x3F9B00
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(CHECKPOINT)==sha(ROOT.parent/'mod_test/replay-checkpoint-34/svdexSC34.s14')=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    close={'created':datetime.now().astimezone().isoformat(),'pid':reader.pid,'date':date,
           'state_stack':end['focused']['state_stack'],'debugger_attached':False,
           'original_code_points':list(map(hex,points)),'original_strategy_update_restored':True,
           'sampled_records':len(end['records']),'random_inputs':end['random_inputs'],
           'save34_sha256':sha(CHECKPOINT),'backup_sha256':sha(ROOT.parent/'mod_test/replay-checkpoint-34/svdexSC34.s14'),
           'trace_tail':trace[-1],'classification':analysis['branch'],
           'scope':'Stable sampled endpoint after early recorder exit, not a full-turn trace or complete-world proof.'}
    for filename,data in [('end.json',end),('end-branch-inputs.json',branch),('closeout.json',close)]:
        with (folder/filename).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(json.dumps(close,ensure_ascii=True))
finally:
    reader.close()
