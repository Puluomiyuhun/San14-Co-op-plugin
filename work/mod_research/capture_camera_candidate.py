"""Read the F720 singleton and linked view object; no native calls or writes."""
import argparse,ctypes as C,json,struct
from ctypes import wintypes as W
from pathlib import Path
from lockstep_baseline import BattleObserver,sample
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('name');args=p.parse_args();assert args.name.replace('-','').isalnum()
out=ROOT/'lockstep-traces'/(args.name+'.json');assert not out.exists()
r=BattleObserver()
try:
    before=sample(r);m=r.memory;base=m.base
    def typename(address):
        try:
            vt=r.pointer(address);col=r.pointer(vt-8)
            if not (base<=vt<base+m.image_size and base<=col<base+m.image_size-24):return None
            sig,_,_,td,_,self_rva=struct.unpack('<6I',m.read(col,24))
            if sig!=1 or self_rva!=col-base or td>=m.image_size-160:return None
            return m.read(base+td+16,128).split(b'\0')[0].decode('ascii')
        except (OSError,RuntimeError,UnicodeError):return None
    address=base+0x19e7690;raw=m.read(address,0x290);linked=struct.unpack_from('<Q',raw,0x280)[0]
    record={'singleton_rva':'0x19e7690','singleton_type':typename(address),'singleton_hex':raw.hex(),
        'fields_230_234':struct.unpack_from('<ii',raw,0x230),'linked_address':hex(linked),
        'linked_type':typename(linked) if linked else None,'linked_hex':m.read(linked,0xb0).hex() if linked else None}
    k=m.k;k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)];k.CheckRemoteDebuggerPresent.restype=W.BOOL
    attached=W.BOOL();assert k.CheckRemoteDebuggerPresent(m.handle,C.byref(attached)) and not attached.value
    after=sample(r)
    assert before==after,'Gameplay sample changed during camera read'
    record.update({'date':before['focused']['critical_state']['date'],'player':before['focused']['critical_state']['player'],
        'global_rng':before['random_inputs']['global_18eb8b0'],'gameplay_sample_unchanged':True,'debugger_attached':False,
        'scope':'Current post-capture view candidate only, NOT the camera used throughout any earlier run. Field meanings require code/controlled-view validation.'})
    out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if not k.endswith('_hex')},ensure_ascii=True))
finally:r.close()
