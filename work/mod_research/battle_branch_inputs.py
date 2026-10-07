"""Additional read-only inputs for the native battle gate and pair filter.

Keep raw field names when their complete gameplay meaning is not established.
This does not replace the broader partial-world checkpoint or prove completeness.
"""
import json
from pathlib import Path
import struct
from lockstep_baseline import BattleObserver, sample
from finalize_lockstep_capture import diagnostics

ROOT=Path(__file__).resolve().parent

def capture_branch_inputs(r):
    m=r.memory
    root=r.pointer(m.base+0x1fca1e0)
    world=r.pointer(root+0x85130)
    r.require_type(world,'CWorldData')
    u32=lambda a:int.from_bytes(m.read(a,4),'little')
    u64=lambda a:int.from_bytes(m.read(a,8),'little')
    forces=[]
    for identity in range(52):
        addr=r.pointer(root+0xdca0+identity*8)
        r.require_type(addr,'CForceData')
        forces.append({'id':identity,'field_12':m.read(addr+0x12,1)[0],
                       'field_ea_11d_hex':m.read(addr+0xea,52).hex(),
                       'field_194':m.read(addr+0x194,1)[0]})
    filt=u64(m.base+0x201ec70)
    pairroot=m.base+0x1a38840
    count=u64(pairroot+0xc0);node=u64(pairroot+0xa0)
    assert count<=2048
    pairs=[];seen=set()
    while node:
        assert node not in seen and len(seen)<2048, 'Invalid or cyclic pair list'
        seen.add(node)
        raw=m.read(node,0x38);side=u64(node)
        assert side
        a=m.read(side,0x20);b=raw[8:0x28]
        def decode(blob):
            return {'id':int.from_bytes(blob[:2],'little'),'type':int.from_bytes(blob[4:8],'little'),
                    'field_08':blob[8],'field_0a':int.from_bytes(blob[10:12],'little'),
                    'field_0c':int.from_bytes(blob[12:16],'little'),'force':int.from_bytes(blob[16:20],'little'),
                    'field_14':blob[20],'record_00_18_hex':blob[:24].hex()}
        pairs.append({'index':len(pairs),'a':decode(a),'b':decode(b)})
        node=int.from_bytes(raw[0x30:0x38],'little')
    assert len(pairs)==count, 'Pair list changed or unexpected layout'
    return {'schema':'san14.battle-branch-inputs.v1','date':list(m.read(world+0x34,5)),
            'diagnostics':diagnostics(r),'world_field_165c':m.read(world+0x165c,1)[0],
            'special_filter_present':bool(filt),'special_filter_enabled':u32(filt) if filt else None,
            'forces':forces,'pairs':pairs,
            'scope':'Additional fields directly read by 0x29A000, plus current pair identities and gate diagnostics. Not complete combat inputs.'}

if __name__=='__main__':
    r=BattleObserver()
    try:
        before=sample(r);result=capture_branch_inputs(r)
        assert result==capture_branch_inputs(r) and before==sample(r)
        target=ROOT/'lockstep-traces/branch-current-before.json'
        assert not target.exists(),'Refusing to overwrite evidence'
        target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'pair_count':len(result['pairs']),'pairs':[[(x[k]['type'],x[k]['id'],x[k]['force']) for k in ('a','b')] for x in result['pairs']],
                          'special_filter_enabled':result['special_filter_enabled'],'world_field_165c':result['world_field_165c']},ensure_ascii=True))
    finally:r.close()
