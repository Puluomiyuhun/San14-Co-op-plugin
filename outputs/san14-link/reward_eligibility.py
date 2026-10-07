"""Read-only mirror of build-locked 0x1D4270 reward-person predicate.

This diagnoses eligibility, never submits rewards. UI scope, funding and order
phase are separate checks; predicate acceptance is not authority to execute.
Unknown task implementations fail closed instead of guessing their semantics.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from domestic_reader import DomesticDecoder, PERSON_LIST_VTABLE_RVA
from game_reader import GameReader
from sortie_reader import text_name

TASK_TYPES={
    0x129BB48:('CCmdActionMovePerson',0x1D4330,0x20BA50),
    0x129BC90:('CCmdActionReturn',0x1D4340,0x20BA50),
    0x129BF20:('CCmdActionSearch',0x1D4330,0x20BAA0),
    0x129C068:('CCmdActionDiplomacy',0x1D4330,0x20BAA0),
    0x129C2F8:('CCmdActionDisappear',0x1D4330,0x20BAA0),
    0x129C440:('CCmdActionCaravan',0x1D4330,0x20BAA0),
}

def date_serial(data):
    year,month,day=struct.unpack('<hbb',data)
    return (year*12+month)*30+day-31

def excluded_special_person(identity,location,force_id):
    special=any(start<=identity<=start+9 for start in (0x100F,0x1023,0x1037,0x104B,0x105F))
    return special and 1<=location<=61 and not 46<=force_id<=50

def predicate_reason(person):
    # Preserve native early-return order to make disagreements diagnosable.
    if not person['native_valid']:return 'invalid_person'
    if person['rank_raw']==1:return 'ruler_rank'
    if person['flags']&2:return 'already_rewarded'
    if person['loyalty']>=100:return 'loyalty_at_least_100'
    if excluded_special_person(person['id'],person['location_id'],person['force_id']):return 'special_person_rule'
    if person['task'] is not None and person['task']['elapsed_value']!=0:return 'task_elapsed_nonzero'
    if person['army'] is not None and person['army']['order_code']!=0:return 'army_order_nonzero'
    return None

def pool_values(d,address,vtable_rva,pool_rva,capacity,maximum,payload_width):
    if d.uint(address,8)!=d.memory.base+vtable_rva:raise RuntimeError('List implementation mismatch')
    handle=d.ptr(address+8,nullable=True)
    if not handle:return []
    pool=d.memory.base+pool_rva
    if not d.uint(pool+8,8) or d.uint(pool+0x40)!=capacity:raise RuntimeError('List pool mismatch')
    slot=d.uint(handle)
    if slot>=capacity:raise RuntimeError('List slot outside capacity')
    heads=d.ptr(pool+0x10);tails=d.ptr(pool+0x18);counts=d.ptr(pool+0x28)
    count=d.uint(counts+slot*8,8)
    if count>maximum:raise RuntimeError('List exceeds supported bound')
    node=d.ptr(heads+slot*8,nullable=True);last=0;seen=set();values=[]
    while node:
        if node in seen or len(values)>=count:raise RuntimeError('List cycle or count mismatch')
        seen.add(node)
        raw=d.read(node,24)
        value=int.from_bytes(raw[:payload_width],'little')
        next_node,previous=struct.unpack_from('<QQ',raw,8)
        if previous!=last:raise RuntimeError('List reverse link mismatch')
        values.append(value);last=node;node=next_node
        if node:d.check_pointer(node)
    if len(values)!=count or d.uint(tails+slot*8,8)!=last:raise RuntimeError('List length/tail mismatch')
    return values

def capture_eligibility(reader):
    snapshot=reader.snapshot();d=DomesticDecoder(reader);base=d.memory.base
    world=d.ptr(d.root+0x85130);now=date_serial(d.read(world+0x34,4))
    manager=d.ptr(d.root+0x85128)
    task_addresses=pool_values(d,manager+0x10,0x129BB28,0x201D3A0,0x14000,1024,8)
    tasks=[];first_tasks={};task_hash=hashlib.sha256()
    for address in task_addresses:
        d.check_pointer(address)
        vt=d.uint(address,8)-base
        if vt not in TASK_TYPES:raise RuntimeError(f'Unsupported task vtable {vt:#x}')
        name,valid_fn,elapsed_fn=TASK_TYPES[vt]
        d.require_type(address,name)
        if d.uint(base+vt+0x18,8)!=base+valid_fn or d.uint(base+vt+0xB0,8)!=base+elapsed_fn:
            raise RuntimeError('Task virtual method mismatch')
        data=d.read(address+0x58,0x10)
        valid=struct.unpack_from('<i',data)[0]!=-1
        elapsed=now-date_serial(data[8:12])
        if elapsed_fn==0x20BA50:elapsed=max(0,elapsed)
        ids=pool_values(d,address+0x18,0x123E210,0x19E1BF0,0x400,6000,4)
        if any(not 1<=i<6000 for i in ids) or len(ids)!=len(set(ids)):raise RuntimeError('Invalid task officer IDs')
        row={'type':name,'valid':valid,'officer_ids':ids,'elapsed_value':elapsed}
        tasks.append(row)
        task_hash.update(struct.pack('<I',vt)+data+struct.pack('<%dI'%len(ids),*ids))
        if valid:
            for identity in ids:first_tasks.setdefault(identity,row)
    person_addresses=pool_values(d,d.root+0xF8,PERSON_LIST_VTABLE_RVA,0x201D3A0,0x14000,6000,8)
    persons=[];seen=set();person_hash=hashlib.sha256();districts={};army_cache={}
    dummy=d.ptr(d.root+0x737C0);army_zero=d.ptr(d.root+0x7DF60)
    for address in person_addresses:
        d.require_type(address,'CPersonData')
        if d.uint(d.uint(address,8)+0x18,8)!=base+0x2119F0:raise RuntimeError('Person validity function mismatch')
        raw=d.read(address+0x10,0x188);identity=int.from_bytes(raw[:2],'little')
        if not 1<=identity<6000 or identity in seen or d.ptr(d.root+0x148+identity*8)!=address:
            raise RuntimeError('Person list/table identity mismatch')
        seen.add(identity);person_hash.update(raw)
        district_id=raw[0x108]
        if district_id not in districts:
            index=district_id if district_id<=51 else 0
            district=d.ptr(d.root+0xDE40+index*8);d.require_type(district,'CDistrictData')
            data=d.read(district+0x10,8)
            valid=index!=0 and data[0]!=0 and data[1]!=0 and int.from_bytes(data[2:4],'little')!=0
            districts[district_id]={'force_id':data[0] if valid and data[0]<=51 else 0,
                                    'valid':valid,'leader_id':int.from_bytes(data[2:4],'little'),
                                    'kind_raw':data[1],'action_points':data[4]}
        force=districts[district_id]['force_id']
        location=int.from_bytes(raw[0x10A:0x10C],'little');descriptor=int.from_bytes(raw[0x10C:0x10E],'little')
        army=None
        if 62<=descriptor<=561:
            unit_id=descriptor-61
            if unit_id not in army_cache:
                unit=d.ptr(d.root+0x7DF60+unit_id*8);d.require_type(unit,'CArmyUnitData')
                if unit!=army_zero+unit_id*0x200:raise RuntimeError('Army table layout mismatch')
                data=d.read(unit+0x10,0x28)
                army_cache[unit_id]={'id':unit_id,'valid':bool(data[0] and int.from_bytes(data[2:4],'little')),
                                     'officer_id':int.from_bytes(data[2:4],'little'),'order_code':data[0x27]}
            unit=army_cache[unit_id]
            if unit['valid'] and unit['officer_id']==identity:army=unit
        row={'id':identity,'name':text_name(raw[2:20])+text_name(raw[20:38]),'district_id':district_id,'force_id':force,
             'location_id':location,'location_descriptor_raw':descriptor,'rank_raw':raw[0x10E],
             'loyalty':raw[0x110],'flags':int.from_bytes(raw[0x186:0x188],'little'),
             'native_valid':((address-dummy)>>9)!=0 and (5001<=identity<=5100 or raw[0x10E]!=0),
             'task':first_tasks.get(identity),'army':army}
        row['rejection_reason']=predicate_reason(row)
        row['predicate_eligible']=row['rejection_reason'] is None
        persons.append(row)
    d.verify_stable()
    if snapshot!=reader.snapshot():raise RuntimeError('World or UI changed while sampling eligibility')
    own=[p for p in persons if p['force_id']==snapshot['player']['force_id'] and 1<=p['rank_raw']<=4]
    return {'schema':'san14.reward-eligibility.v1','mode':'read-only-external-predicate-mirror',
            'exe_sha256':reader.sha256,'date':snapshot['date'],'player':snapshot['player'],'persons':persons,
            'person_count':len(persons),'task_count':len(tasks),'tasks':tasks,
            'person_records_sha256':person_hash.hexdigest(),'task_fields_sha256':task_hash.hexdigest(),
            'own_force_person_count':len(own),'own_force_predicate_eligible_ids':[p['id'] for p in own if p['predicate_eligible']],
            'own_force_rejection_counts':dict(Counter(p['rejection_reason'] for p in own if p['rejection_reason'])),
            'native_predicate_correlated':False,'full_command_legality_verified':False,'replay_supported':False,
            'scope':'Person predicate only; UI scope/phase, funding, ownership authority and command execution are separate'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    reader=GameReader()
    try:
        result=capture_eligibility(reader)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k not in ('persons','tasks')},ensure_ascii=True,indent=2))
    finally:reader.close()

if __name__=='__main__':main()
