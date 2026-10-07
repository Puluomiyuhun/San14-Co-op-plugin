"""After user reaches planning: save native end state, detach, verify and analyze."""
import ctypes as C,ctypes.wintypes as W,json,sys
from pathlib import Path
from datetime import datetime
from lockstep_baseline import BattleObserver,sample
from test_submit_probe import wait_json
from analyze_lockstep import baseline_difference
from analyze_rng_pairs import analyze
from unwind_rng_stack import Unwinder
ROOT=Path(__file__).resolve().parent
name=sys.argv[1];assert name.replace('-','').isalnum()
folder=ROOT/'lockstep-traces'/name;assert not (folder/'closeout.json').exists()
meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
r=BattleObserver()
try:
    end=sample(r)
    assert end['focused']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],'User must finish reports and return to planning first'
    date=end['focused']['critical_state']['date']
    assert (date['year'],date['month'],date['day'])==(203,8,21),'Expected one turn from saved Aug11 state'
    assert end==sample(r),'End state still changing'
    with (folder/'end-before-detach.json').open('x',encoding='utf-8') as f:json.dump(end,f,ensure_ascii=False,indent=2)
    log=folder/'trace.jsonl';Path(str(log)+'.stop').write_text('User reached stable planning; finish native observation.')
    rows=wait_json(log,'detached',deadline=15)
    assert rows[-1]['registers_restored']
    after=sample(r);assert after==sample(r),'Post-detach state still changing'
    with (folder/'end.json').open('x',encoding='utf-8') as f:json.dump(after,f,ensure_ascii=False,indent=2)
    k=r.memory.k;k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)];k.CheckRemoteDebuggerPresent.restype=W.BOOL
    debugged=W.BOOL();assert k.CheckRemoteDebuggerPresent(r.memory.handle,C.byref(debugged));assert not debugged.value
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    for address,size in [(0x1ab6f4,5),(0x2d9243,5),(0x2d9261,5),(0x3b3774,5),(0x3aa7c0,88),(0x3aa3f0,104)]:
        assert r.memory.read(r.memory.base+address,size)==image[address:address+size]
    result={'created':datetime.now().astimezone().isoformat(),'debugger_attached':False,'original_code_checked':True,
            'sample_unchanged_while_detaching':end==after,'sampled_records':len(after['records']),
            'date':date,'random_inputs':after['random_inputs'],'observer_detach':rows[-1],
            'scope':'Partial gameplay snapshot, unchanged candidate/helper code, debugger cleanup. Native observation only.'}
    u=Unwinder(image,(ROOT/'runtime-pdata.bin').read_bytes(),int(meta['base'],16))
    analysis=analyze(rows,int(meta['base'],16),u)
    for filename,data in [('closeout.json',result),('paired-analysis.json',analysis)]:
        with (folder/filename).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(json.dumps({'closeout':result,'analysis':{k:v for k,v in analysis.items() if k not in ('calls','writes_outside_paired_helpers','scope')}},ensure_ascii=True))
finally:r.close()
