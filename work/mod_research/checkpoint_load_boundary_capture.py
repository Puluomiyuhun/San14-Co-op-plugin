"""One read-only SAN14 boundary sample; no input collection or game calls."""
from pathlib import Path
from datetime import datetime
import sys,struct,json
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P/'python_deps'),str(P.parent.parent/'outputs/san14-link')]
from battle_observer import BattleObserver
from checkpoint_load_mode_capture import snapshot
observer=BattleObserver()
try:
    data=snapshot(observer);mem=observer.memory;base=mem.base
    u64=lambda p:struct.unpack('<Q',mem.read(p,8))[0]
    u32=lambda p:struct.unpack('<I',mem.read(p,4))[0]
    manager=base+0x19E7310;stack=u64(manager+0x20);count=u64(manager+0x10)
    extra={'optional_service':hex(u64(base+0x1FC8488)),'keyboard':hex(u64(base+0x1FCA0A0)),'states':[]}
    for index in range(min(count,12)):
        state=u64(stack+index*8);vt=u64(state)
        extra['states'].append({'pointer':hex(state),'vtable_rva':hex(vt-base),'update_rva':hex(u64(vt+0x28)-base),'worker':hex(u64(state+0x50))})
    root=u64(base+0x1FCA1E0);world=u64(root+0x85130);game=u64(stack+16);panel=u64(game+0x480)
    extra['optional_branch']={'world_bc':struct.unpack('<b',mem.read(world+0xBC,1))[0], 'panel_1f4':u32(panel+0x1F4)}
    extra['native_pause']={'control':u32(base+0x1A38EC8+0x28),'cursor':u32(base+0x19E7510+0x13C),'coordinator_flags':u32(base+0x19E7690), 'callback_owner_present':[bool(u64(base+0x19E7690+offset)) for offset in (0x2E8,0x328,0x368)]}
    keyboard=u64(base+0x1FCA0A0)
    extra['keyboard_neutral']={'modifier_bytes_zero':not any(mem.read(keyboard+0x50,4)), 'buffer_count_zero':u32(keyboard+0x54)==0, 'held_keys_present':any(x&128 for x in mem.read(keyboard+0x158,256))}
    data['load_boundary_extra']=extra;data['game_writes']=0
finally:observer.close()
path=P/('checkpoint_load_boundary_snapshot_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
with path.open('x',encoding='utf8') as stream:json.dump(data,stream,ensure_ascii=False,indent=2)
print(json.dumps({'result':data['result'],'reasons':data['reasons'],'extra':extra,'path':str(path),'game_writes':0}))
