"""Read-only post-duplicate check before asking for native checkpoint recovery."""
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime
import hashlib
import json
from pathlib import Path
from run_second_force_reward import capture,CHECKPOINT,ROOT
from battle_observer import BattleObserver

load=lambda p:json.loads(p.read_text(encoding='utf-8'))
net=load(ROOT/'second-force-network-live-latest.json');run=Path(net['directory'])
native=Path(net['effect']['directory']);before=load(native/'before.json');after=load(native/'after.json')
receipts=load(run/'receipts.json')
assert [r['status'] for r in receipts]==['REJECTED','COMPLETED','COMPLETED','REJECTED']
assert receipts[2]=={**receipts[1],'duplicate':True}
journal=[json.loads(x) for x in (run/'journal.jsonl').read_text(encoding='utf-8').splitlines()]
assert [r['state'] for r in journal]==['IN_PROGRESS','COMPLETED']
r=BattleObserver()
try:
    now=capture(r);assert now==capture(r)==after,'State after duplicate differs from verified single execution'
    assert len(now['records'])==783
    root=r.pointer(r.memory.base+0x1FCA1E0)
    ai=r.pointer(r.memory.base+0x1A1F6C0);r.require_type(ai,'CAIManager')
    ai_status={'global_gate':int.from_bytes(r.memory.read(ai+0x30,4),'little'),
               'per_force_entry_count':int.from_bytes(r.memory.read(ai+0x68,8),'little')}
    assert r.pointer(r.memory.base+0x12CC4A8+0x28)==r.memory.base+0x3F9B00
    k=r.memory.k;k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)];k.CheckRemoteDebuggerPresent.restype=W.BOOL
    attached=W.BOOL();assert k.CheckRemoteDebuggerPresent(r.memory.handle,C.byref(attached)) and not attached.value
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    assert r.memory.read(r.memory.base+0x1D6DA0,0x2B9)==image[0x1D6DA0:0x1D7059]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(CHECKPOINT)==sha(ROOT.parent/'mod_test/replay-checkpoint-34/svdexSC34.s14')=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    result={'result':'PASS','created':datetime.now().astimezone().isoformat(),'record_count':len(now['records']),
            'duplicate_did_not_reapply':True,'current_player':now['focused']['critical_state']['player'],
            'date':now['focused']['critical_state']['date'],'host_city19_unchanged':before['records']['city:19']==now['records']['city:19'],
            'host_district11_unchanged':before['records']['district:11']==now['records']['district:11'],
            'known_global_rng_unchanged':before['global_rng']==now['global_rng'],'known_world_rng_fields_unchanged':before['world_rng_fields_hex']==now['world_rng_fields_hex'],
            'global_rng_before':before['global_rng'],'global_rng_after':now['global_rng'],
            'ai_status':ai_status,'human_faction_ai_exclusion_implemented':False,
            'debugger_attached':False,'original_strategy_update_restored':True,'reward_handler_bytes_unchanged':True,
            'save34_sha256':sha(CHECKPOINT),'native_restore_pending':True}
    for name,data in [('post-duplicate.json',now),('post-duplicate-check.json',result)]:
        with (run/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=True))
finally:r.close()
