"""Read-only, build-specific inventory of lists used to construct combat pairs.

Preserve iteration order. Do not infer that these lists are absent from saves.
No native function calls, debugger attachment or game writes.
"""
import argparse,json,struct
from pathlib import Path
from lockstep_baseline import BattleObserver,sample
from domestic_reader import DomesticDecoder
from reward_eligibility import pool_values
ROOT=Path(__file__).resolve().parent

def capture_combat_lists(reader):
    d=DomesticDecoder(reader);base=d.memory.base;root=d.root
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    for start,end in ((0x210d40,0x210e85),(0x16233f,0x1623ea),(0x16296a,0x1629a3)):
        if d.read(base+start,end-start)!=image[start:end]:raise RuntimeError('Native predicate fingerprint mismatch')
    first=d.ptr(root+0x7DF60)
    def army_id(ptr):
        d.require_type(ptr,'CArmyUnitData')
        identity=(ptr-first)//0x200
        if not 0<=identity<=500 or first+identity*0x200!=ptr or d.ptr(root+0x7DF60+identity*8)!=ptr:
            raise RuntimeError('Army list/table identity mismatch')
        return identity
    def generic_object(ptr):
        if not ptr:return None
        d.check_pointer(ptr)
        if first<=ptr<first+501*0x200 and (ptr-first)%0x200==0:
            raw=d.read(ptr+0x10,0x58)
            return {'type':'CArmyUnitData','id':army_id(ptr),'valid':bool(raw[0] and int.from_bytes(raw[2:4],'little')),'record_10_68_hex':raw.hex()}
        # Retain unknown objects without claiming support for their validity predicate.
        vt=d.uint(ptr,8)
        return {'type':'UNRESOLVED','address':hex(ptr),'vtable_rva':hex(vt-base),'head_00_20_hex':d.read(ptr,0x20).hex()}
    pointer_lists={}
    for offset,vt,typ,limit in ((0x58,0x123E200,'CArmyUnitData',501),(0x68,0x123E200,'CArmyUnitData',501),
                               (0x88,0x123F3C8,'CCityData',52),(0x98,0x123F3D8,'CGateData',11)):
        addresses=pool_values(d,root+offset,vt,0x201D3A0,0x14000,limit,8)
        identities=[]
        for address in addresses:
            d.require_type(address,typ)
            identities.append(army_id(address) if typ=='CArmyUnitData' else d.uint(address+0x10,2))
        if len(set(identities))!=len(identities):raise RuntimeError('Duplicate object in input list')
        pointer_lists[hex(offset)]={'type':typ,'count':len(addresses),'ordered_ids':identities}
    list_addr=root+0x138;pool=base+0x1FC9760
    if d.uint(list_addr,8)!=base+0x12AA618:raise RuntimeError('SAnnihilate list type mismatch')
    if not d.uint(pool+8,8) or d.uint(pool+0x40)!=0x40:raise RuntimeError('SAnnihilate pool mismatch')
    handle=d.ptr(list_addr+8,nullable=True);records=[]
    if handle:
        slot=d.uint(handle)
        if slot>=0x40:raise RuntimeError('Invalid SAnnihilate list handle')
        heads=d.ptr(pool+0x10);tails=d.ptr(pool+0x18);counts=d.ptr(pool+0x28)
        count=d.uint(counts+slot*8,8)
        if count>128:raise RuntimeError('SAnnihilate count exceeds bounded capacity')
        node=d.ptr(heads+slot*8,nullable=True);seen=set();last=0
        while node:
            if node in seen or len(records)>=count:raise RuntimeError('SAnnihilate cycle/count mismatch')
            seen.add(node);raw=d.read(node,0x40)
            if int.from_bytes(raw[0x38:0x40],'little')!=last:raise RuntimeError('SAnnihilate reverse link mismatch')
            members=[generic_object(int.from_bytes(raw[i:i+8],'little')) for i in (0,8,16)]
            records.append({'index':len(records),'members_00_08_10':members,'unresolved_18_30_hex':raw[0x18:0x30].hex()})
            last=node;node=int.from_bytes(raw[0x30:0x38],'little')
            if node:d.check_pointer(node)
        if len(records)!=count or d.uint(tails+slot*8,8)!=last:raise RuntimeError('SAnnihilate count/tail mismatch')
    active=[]
    for identity in range(1,501):
        raw=d.read(first+identity*0x200+0x10,0x58)
        if raw[0] and int.from_bytes(raw[2:4],'little'):active.append(identity)
    return {'schema':'san14.combat-list-inputs.v1','date':reader.snapshot()['date'],'pointer_lists':pointer_lists,
        'annihilate_list':{'root_offset':'0x138','native_type':'tlib::list<SAnnihilate>','count':len(records),'records':records},
        'valid_army_ids_from_records':active,
        'active_list_matches_valid_records_as_set':set(pointer_lists['0x58']['ordered_ids'])==set(active),
        'scope':'Only identified input lists, order, and selected record fields. No game calls. Not a full world or complete eligibility predicate.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');args=p.parse_args();assert args.name.replace('-','').isalnum()
    reader=BattleObserver()
    try:
        before=sample(reader);result=capture_combat_lists(reader)
        assert result==capture_combat_lists(reader) and before==sample(reader),'Game changed during read-only capture'
        path=ROOT/'lockstep-traces'/(args.name+'.json');assert not path.exists()
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True))
    finally:reader.close()
