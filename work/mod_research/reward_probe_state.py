"""Read-only reward preflight and comparison. Basic checks are not full legality."""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs'/'san14-link'))
from domestic_reader import DomesticDecoder,PERSON_LIST_VTABLE_RVA
from sortie_reader import text_name

IDS=[166,496,769]

def capture_reward_state(reader):
    before=reader.snapshot()
    d=DomesticDecoder(reader)
    base=reader.memory.base
    # CSan14Data's own person list, reached by the native iterator at 0x211D30.
    # Do not enumerate all possible person-table slots or hardcode a pool slot.
    address=d.root+0xF8
    if d.uint(address,8)!=base+PERSON_LIST_VTABLE_RVA:
        raise RuntimeError('Global person-list vtable mismatch')
    handle=d.ptr(address+8)
    slot=d.uint(handle)
    capacity=d.uint(base+0x201D3E0)
    if not d.uint(base+0x201D3A8,8) or not 0<=slot<min(capacity,0x14000):
        raise RuntimeError('Global person-list pool unavailable')
    heads=d.ptr(base+0x201D3B0);counts=d.ptr(base+0x201D3C8)
    count=d.uint(counts+slot*8,8)
    if not 1<=count<=6000:
        raise RuntimeError('Global person-list count invalid')
    node=d.ptr(heads+slot*8,nullable=True)
    nodes=set();people={};digest=hashlib.sha256()
    while node:
        if node in nodes or len(nodes)>=count:
            raise RuntimeError('Global person-list cycle/count mismatch')
        nodes.add(node)
        person,next_node=struct.unpack('<QQ',d.read(node,16))
        d.require_type(person,'CPersonData')
        data=d.read(person+0x10,0x188)
        identity=int.from_bytes(data[:2],'little')
        if not 1<=identity<6000 or identity in people or d.ptr(d.root+0x148+identity*8)!=person:
            raise RuntimeError('Global person-list identity mismatch')
        people[identity]={'id':identity,'name':text_name(data[2:20])+text_name(data[20:38]),
                          'district_id':data[0x108],'location_id':int.from_bytes(data[0x10A:0x10C],'little'),
                          'rank_raw':data[0x10E],'loyalty':data[0x110],
                          'flags':int.from_bytes(data[0x186:0x188],'little'),
                          'record_sha256':hashlib.sha256(data).hexdigest()}
        digest.update(data)
        if next_node:d.check_pointer(next_node)
        node=next_node
    if len(people)!=count:
        raise RuntimeError('Global person-list truncated')
    city=d.city_at(d.ptr(d.root+0xDAA8+19*8))
    district=d.district(11)
    ruler=d.person_at(d.ptr(d.root+0x148+district['leader_id']*8))
    candidates=[]
    for identity in IDS:
        person=people[identity]
        owner=d.district(person['district_id'])
        row=dict(person)
        row['basic_checks']={
            'same_force':owner['force_id']==district['force_id'],
            'same_district':person['district_id']==district['id'],
            'rank_not_one':person['rank_raw']!=1,
            'loyalty_below_100':person['loyalty']<100,
            'rewarded_bit_clear':not(person['flags']&2),
        }
        row['basic_checks_passed']=all(row['basic_checks'].values())
        row['native_eligibility_verified']=False
        candidates.append(row)
    if before!=reader.snapshot():raise RuntimeError('Game date/player changed during reward sampling')
    d.verify_stable()
    return {'schema':'san14.reward-container-state.v1','date':before['date'],'player':before['player'],
            'global_person_count':count,'global_person_records_sha256':digest.hexdigest(),
            'global_person_ids':list(people),'city':city,'district':district,'ruler':ruler,'candidates':candidates,
            'funding_location_matches':ruler['location_id']==city['foothold_id'],
            'enough_gold_for_batch':city['gold']>=len(IDS)*100,
            'enough_actions_for_batch':district['action_points']>=1,
            'full_reward_legality_verified':False,
            'scope':'All persons in the global valid-person list, records +0x10..+0x198; city and district fields; no RNG/full-world proof'}

if __name__=='__main__':
    from battle_observer import BattleObserver
    reader=BattleObserver()
    try:
        state=capture_reward_state(reader)
        (ROOT/'reward-preflight-readonly.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in state.items() if k!='global_person_ids'},ensure_ascii=True,indent=2))
    finally:reader.close()
