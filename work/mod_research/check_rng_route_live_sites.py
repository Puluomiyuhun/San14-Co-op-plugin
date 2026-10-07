"""Read-only verification that the four candidate instructions remain original."""
import ctypes as C,ctypes.wintypes as W,json
from pathlib import Path
from lockstep_baseline import BattleObserver,sample
ROOT=Path(__file__).resolve().parent
audit=json.loads((ROOT/'rng-route-site-audit-m.json').read_text())
r=BattleObserver()
try:
    before=sample(r);sites=[]
    for site in audit['sites']:
        data=r.memory.read(r.memory.base+int(site['rva'],16),5)
        assert data.hex()==site['bytes'],f"Candidate site changed: {site['rva']}"
        sites.append({'rva':site['rva'],'bytes':data.hex(),'original':True})
    k=r.memory.k;k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)]
    k.CheckRemoteDebuggerPresent.restype=W.BOOL;debugger=W.BOOL()
    assert k.CheckRemoteDebuggerPresent(r.memory.handle,C.byref(debugger))
    assert not debugger.value
    assert before==sample(r)
    result={'pid':r.pid,'sites':sites,'debugger_attached':bool(debugger.value),
            'date':before['focused']['critical_state']['date'],
            'random_inputs':before['random_inputs'],'sampled_records':len(before['records']),
            'read_only':True,'sample_stable':True,'scope':'Four instruction sites and known sample fields only; not a full-module integrity scan.'}
    (ROOT/'rng-route-live-pristine-m.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:r.close()
