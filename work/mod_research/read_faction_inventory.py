"""Read real faction/city ownership for next-stage authorization research.

This does not certify whether an officer can legally receive a game order.
"""
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs'/'san14-link'))
from game_reader import GameReader,DATA_POINTER_RVA
from sortie_reader import text_name

r=GameReader()
try:
    before=r.snapshot();root=r.pointer(r.memory.base+DATA_POINTER_RVA)
    reads=[]
    def read(address,length):
        data=r.memory.read(address,length);reads.append((address,data));return data
    def pointer(address):
        value=r.pointer(address);reads.append((address,struct.pack('<Q',value)));return value
    # Location alone does not certify availability: a deployed leader can still
    # retain a city location. Cross-reference the actual active army table.
    army_table=read(root+0x7DF60,501*8)
    army_addresses=struct.unpack('<501Q',army_table)
    first=army_addresses[0]
    if first<0x10000 or any(p!=first+i*0x200 for i,p in enumerate(army_addresses)):
        raise RuntimeError('Unsupported army unit table layout')
    r.require_type(first,'CArmyUnitData')
    armies=read(first,501*0x200)
    leader_units={}
    for unit_id in range(1,501):
        unit=armies[unit_id*0x200:(unit_id+1)*0x200]
        if unit[:8]!=armies[:8]:raise RuntimeError('Army unit type mismatch')
        leader=struct.unpack_from('<H',unit,0x12)[0]
        if not unit[0x10] or not leader:continue
        leader_units.setdefault(leader,[]).append({
            'id':unit_id,'soldiers':struct.unpack_from('<H',unit,0x16)[0],
            'order_code':unit[0x37],'destination_type':unit[0x38],
            'destination_id':struct.unpack_from('<H',unit,0x3A)[0]})
    def officer(identity):
        if not 1<=identity<6000:return None
        address=pointer(root+0x148+identity*8);r.require_type(address,'CPersonData')
        data=read(address+0x10,0x188)
        if struct.unpack_from('<H',data)[0]!=identity:raise RuntimeError('Officer identity mismatch')
        return {'id':identity,'name':text_name(data[2:20])+text_name(data[20:38]),
                'district_id':data[0x108],'location_id':struct.unpack_from('<H',data,0x10A)[0],
                'raw_flags_196':struct.unpack_from('<H',data,0x186)[0],
                'active_armies_led':leader_units.get(identity,[])}
    factions={}
    for city_id in range(1,52):
        address=pointer(root+0xDAA8+city_id*8);r.require_type(address,'CCityData')
        city=read(address+0x10,0x58)
        if struct.unpack_from('<H',city)[0]!=city_id:raise RuntimeError('City identity mismatch')
        district_id=city[0x20]
        if not 1<=district_id<=51:continue
        district=pointer(root+0xDE40+district_id*8);r.require_type(district,'CDistrictData')
        district_data=read(district+0x10,0x18);force_id=district_data[0]
        if not 1<=force_id<=51:continue
        if force_id not in factions:
            force=pointer(root+0xDCA0+force_id*8);r.require_type(force,'CForceData')
            ruler_id=struct.unpack('<H',read(force+0x10,2))[0]
            ruler=officer(ruler_id)
            factions[force_id]={'force_id':force_id,'ruler':ruler,'is_current_player':force_id==before['player']['force_id'],'cities':[]}
        governor_id=struct.unpack_from('<H',city,0x1E)[0]
        factions[force_id]['cities'].append({'id':city_id,'name':text_name(city[2:10]),
                                            'district_id':district_id,'district_action_points':district_data[4],
                                            'garrison':struct.unpack_from('<I',city,0x2C)[0],
                                            'foothold_id':struct.unpack_from('<H',city,0x3E)[0],
                                            'governor':officer(governor_id)})
    if r.snapshot()!=before or pointer(r.memory.base+DATA_POINTER_RVA)!=root or any(r.memory.read(a,len(data))!=data for a,data in reads):
        raise RuntimeError('Ownership changed while sampling; retry at a stable map')
    result={'mode':'read-only-faction-ownership-inventory','date':before['date'],'player':before['player'],
            'factions':list(factions.values()),
            'active_army_count':sum(len(units) for units in leader_units.values()),
            'command_eligibility_verified':False,
            'scope':'City/district/force membership and active armies led; location alone is not availability; no AI policy or player identity changes'}
    (ROOT/'faction-inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps([{'force_id':f['force_id'],'ruler':f['ruler']['name'] if f['ruler'] else None,
                       'current_player':f['is_current_player'],
                       'cities':[c['name'] for c in f['cities']]} for f in factions.values()],ensure_ascii=False,indent=2))
finally:r.close()
