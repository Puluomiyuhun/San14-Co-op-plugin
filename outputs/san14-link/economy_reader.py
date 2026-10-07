"""Build-locked, read-only extended economic sample; never calls game code.

Adds the native ordered area list, all 501 area slots, center ownership and
full records of assigned officers to the previous city-level investigation.
Raw records may contain runtime fields; no exclusions or world-ready verdict
are derived from this module. Items, ranks and policy-effect dependencies
remain outside this sample.
"""
import json
from pathlib import Path
import struct
from domestic_reader import DomesticDecoder
from game_reader import GameReader
from reward_eligibility import pool_values

AREA_TABLE=0x6C860
AREA_COUNT=501
AREA_STRIDE=0x98
PLANNING=['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']

def city_area_order(order,areas):
    """Mirror the observed iterator filter: city IDs 1..51 and area+35 equal."""
    if len(order)!=len(set(order)) or any(type(i) is not int or not 0<=i<AREA_COUNT or i not in areas for i in order):
        raise ValueError('Native area list contains duplicate/unknown members')
    result={str(city):[] for city in range(1,52)}
    for i in order:
        city=areas[i]['city_id']
        if type(city) is not int or not 0<=city<=51:raise ValueError('Invalid area city ID')
        if city:result[str(city)].append(i)
    return result

def capture_economy(reader):
    snapshot=reader.snapshot()
    if snapshot['state_stack']!=PLANNING:raise RuntimeError('Economy sample requires the idle planning map')
    d=DomesticDecoder(reader);base=d.memory.base
    # Anchors identify the table and ownership/iterator fields, not full formulas.
    anchors={0x28DBAC:'0fb64135',0x28DCFD:'410fb77668',
             0x2F6070:'488b02',0x2F6073:'0fb64835',0x2F6079:'413bc8'}
    # The exact instruction bytes are validated by the static profile instead
    # of assuming all compile/build variants share an object layout.
    for at,hx in anchors.items():
        actual=d.read(base+at,len(bytes.fromhex(hx)))
        if actual!=bytes.fromhex(hx):raise RuntimeError(f'Economic code anchor mismatch at {at:#x}')
    table=d.read(d.root+AREA_TABLE,AREA_COUNT*8);pointers=list(struct.unpack('<501Q',table))
    first=pointers[0]
    if any(p!=first+i*AREA_STRIDE for i,p in enumerate(pointers)):raise RuntimeError('Area storage/table mismatch')
    address_to_id={p:i for i,p in enumerate(pointers)}
    listed=pool_values(d,d.root+0xA8,0x123F418,0x201D3A0,0x14000,501,8)
    if any(p not in address_to_id for p in listed):raise RuntimeError('Area list points outside object table')
    order=[address_to_id[p] for p in listed]
    areas={};records={};centers={};people={}
    for i,p in enumerate(pointers):
        d.require_type(p,'CAreaData');raw=d.read(p+0x10,0x88)
        u16=lambda offset:struct.unpack_from('<H',raw,offset-0x10)[0]
        center=u16(0x3A);city=raw[0x25];person=u16(0x36)
        if not 0<=center<48400 or city>51 or person>6000:raise RuntimeError('Area relationship outside supported bounds')
        if center not in centers:
            hp=d.ptr(d.root+0xDFE0+center*8);d.require_type(hp,'CHexData')
            hx=d.read(hp+0x10,0x10)
            if hx[4]>51:raise RuntimeError('Invalid center owner')
            centers[center]={'force_id':hx[4],'raw_10_20':hx.hex()}
        areas[i]={'id':i,'name':raw[:10].decode('utf-16-le').split('\0')[0],
                  'city_id':city,'assigned_officer_id':person,'center_hex_id':center,
                  'center_force_id':centers[center]['force_id'],
                  'input_fields_raw':{hex(o):u16(o) for o in (0x3C,0x3E,0x44,0x46,0x52,0x68,0x76)},
                  'byte_inputs_raw':{hex(o):raw[o-0x10] for o in (0x38,0x54,0x6D)},
                  'derived_4a_50_raw':list(struct.unpack_from('<4H',raw,0x3A))}
        records[f'area:{i}']=raw.hex()
        if person not in people:
            pp=d.ptr(d.root+0x148+person*8);d.require_type(pp,'CPersonData')
            data=d.read(pp+0x10,0x1F0)
            # Include +198 injury and +1F8 encoded cap, both outside the old
            # person sample. Keep raw bytes; don't guess decoded query results.
            people[person]={'table_id':person,'raw_10_200':data.hex()}
    city_order=city_area_order(order,areas)
    cities={};forces={};districts={}
    for i in range(52):
        cp=d.ptr(d.root+0xDAA8+i*8);d.require_type(cp,'CCityData');raw=d.read(cp+0x10,0x158)
        did=raw[0x20]
        if did>51:raise RuntimeError('Invalid city district')
        if did not in districts:
            dp=d.ptr(d.root+0xDE40+did*8);d.require_type(dp,'CDistrictData');districts[did]=d.read(dp+0x10,0x18).hex()
        fid=bytes.fromhex(districts[did])[0]
        if fid>51:raise RuntimeError('Invalid city force')
        fp=d.ptr(d.root+0xDCA0+i*8);d.require_type(fp,'CForceData');forces[i]=d.read(fp+0x10,0x1C0).hex()
        cities[i]={'id':i,'name':raw[2:10].decode('utf-16-le').split('\0')[0],
                   'force_id':fid,'district_id':did,'gold_food_garrison':list(struct.unpack_from('<3I',raw,0x24)),
                   'derived_a0_a4':list(struct.unpack_from('<2i',raw,0x90)),'raw_10_168':raw.hex()}
    # Repeat every recorded read, including pool links and table slots.
    d.verify_stable()
    if snapshot!=reader.snapshot():raise RuntimeError('Planning state changed during economic capture')
    return {'schema':'san14.extended-economy-sample.v1','snapshot':snapshot,
            'areas':areas,'area_records':records,'native_area_order':order,'city_area_order':city_order,
            'center_hexes':centers,'assigned_officers':people,'cities':cities,'forces_raw':forces,'districts_raw':districts,
            'no_game_functions_called':True,'no_game_writes':True,'complete_economy_inputs':False,
            'missing_dependencies':['Effective officer stat query: item/rank/force-rank and encoded caps',
                                    'Active trait and policy-effect tables and their full lookup dependencies',
                                    'Authoritative shared settings and date-dependent forecast inputs',
                                    'All external command, task and settlement side effects'],
            'scope':__doc__.strip()}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    reader=GameReader()
    try:
        value=capture_economy(reader);args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'result':'READ_ONLY_EXTENDED_ECONOMY_SAMPLE','areas':len(value['areas']),
                          'native_area_order':len(value['native_area_order']),'assigned_officers':len(value['assigned_officers']),
                          'center_hexes':len(value['center_hexes']),'complete_economy_inputs':False},ensure_ascii=False))
    finally:reader.close()
