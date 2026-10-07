"""Read selected list descriptors and pool headers without executing game code."""
import json,struct
from pathlib import Path
from lockstep_baseline import BattleObserver,sample
ROOT=Path(__file__).resolve().parent
def name(r,a):
    m=r.memory;vt=r.pointer(a);loc=r.pointer(vt-8)
    sig,_,_,desc,_,selfrva=struct.unpack('<6I',m.read(loc,24))
    assert sig==1 and selfrva==loc-m.base and desc<m.image_size-160
    return m.read(m.base+desc+16,128).split(b'\0')[0].decode('ascii')
r=BattleObserver()
try:
    before=sample(r);m=r.memory;root=r.pointer(m.base+0x1FCA1E0)
    out={'pid':r.pid,'base':hex(m.base),'date':before['focused']['critical_state']['date'],'lists':[],'pools':{}}
    for off in (0x58,0x68,0x88,0x98,0x138):
        raw=m.read(root+off,16);vt,handle=struct.unpack('<QQ',raw)
        out['lists'].append({'root_offset':hex(off),'type':name(r,root+off),'vtable_rva':hex(vt-m.base),'handle_address':hex(handle),
            'handle_slot':int.from_bytes(m.read(handle,4),'little') if handle else None})
    for off in (0x201D3A0,0x1FC9760):
        out['pools'][hex(off)]={'raw':m.read(m.base+off,0x48).hex(),
            'qwords':[hex(x) for x in struct.unpack('<9Q',m.read(m.base+off,0x48))]}
    assert sample(r)==before
    path=ROOT/'lockstep-traces/combat-list-inspection.json';assert not path.exists()
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=True))
finally:r.close()
