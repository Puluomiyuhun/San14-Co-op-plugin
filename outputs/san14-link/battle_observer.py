"""Read-only focused before/after checks; not a full world synchronization format."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from game_reader import GameReader, DATA_POINTER_RVA
from sortie_reader import text_name


class BattleObserver(GameReader):
    def capture(self, city_id=19, officer_id=666):
        if not 1 <= city_id <= 51 or not 1 <= officer_id < 6000:
            raise RuntimeError("Unsupported city or officer id")
        m=self.memory
        before=self.snapshot()
        root=self.pointer(m.base+DATA_POINTER_RVA)
        self.require_type(root,"CSan14Data")
        city=self.pointer(root+0xDAA8+city_id*8)
        self.require_type(city,"CCityData")
        city_data=m.read(city+0x10,0x58)
        if struct.unpack_from('<H',city_data)[0]!=city_id:
            raise RuntimeError("City table mismatch")
        person=self.pointer(root+0x148+officer_id*8)
        self.require_type(person,"CPersonData")
        person_data=m.read(person+0x10,0x188)
        if struct.unpack_from('<H',person_data)[0]!=officer_id:
            raise RuntimeError("Officer table mismatch")
        district_id=person_data[0x118-0x10]
        if not 1 <= district_id <= 51:
            raise RuntimeError("Officer is not in a supported district")
        district=self.pointer(root+0xDE40+district_id*8)
        self.require_type(district,"CDistrictData")
        district_data=m.read(district+0x10,0x18)
        table=m.read(root+0x7DF60,501*8)
        addresses=struct.unpack('<501Q',table)
        first=addresses[0]
        if first<0x10000 or any(p!=first+i*0x200 for i,p in enumerate(addresses)):
            raise RuntimeError("Unsupported army unit table layout")
        # The game derives an army id by (object - first) >> 9.
        self.require_type(first,"CArmyUnitData")
        raw=m.read(first,501*0x200)
        vtable=raw[:8]
        units=[]
        for i in range(1,501):
            row=raw[i*0x200:(i+1)*0x200]
            if row[:8]!=vtable:
                raise RuntimeError("Army unit type mismatch")
            leader=struct.unpack_from('<H',row,0x12)[0]
            # Same validity predicate as game method 0x211420.
            if not row[0x10] or not leader:continue
            units.append({'id':i,'officer_id':leader,
                          'soldiers':struct.unpack_from('<H',row,0x16)[0],
                          'formation_id':row[0x1B],'naval_formation_id':row[0x1C],
                          'tactic_ids':list(row[0x1D:0x20]),
                          'order_code':row[0x37],'destination_type':row[0x38],
                          'destination_id':struct.unpack_from('<H',row,0x3A)[0]})
        # Sample consistency only. The process is never paused by this reader.
        if (before!=self.snapshot() or root!=self.pointer(m.base+DATA_POINTER_RVA)
                or city_data!=m.read(city+0x10,0x58)
                or person_data!=m.read(person+0x10,0x188)
                or district_data!=m.read(district+0x10,0x18)
                or table!=m.read(root+0x7DF60,501*8)
                or raw!=m.read(first,501*0x200)):
            raise RuntimeError("State changed during sampling; retry while paused at a planning screen")
        critical={'date':before['date'],'player':before['player'],
                  'city':{'id':city_id,'name':text_name(city_data[2:10]),
                          'garrison':struct.unpack_from('<I',city_data,0x3C-0x10)[0],
                          'record_10_68_hex':city_data.hex()},
                  'officer':{'id':officer_id,'name':text_name(person_data[2:20])+text_name(person_data[20:38]),
                             'status_110_198_hex':person_data[0x100:].hex()},
                  'district':{'id':district_id,'force_id':district_data[0],
                              'action_points':district_data[4],
                              'record_10_28_hex':district_data.hex()},
                  'officer_units':[u for u in units if u['officer_id']==officer_id]}
        encoded=json.dumps(critical,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        return {'schema':'san14.focused-state.v1','mode':'read-only-live-game',
                'exe_sha256':self.sha256,'critical_state':critical,
                'critical_state_sha256':hashlib.sha256(encoded).hexdigest(),
                'all_active_units':units,'state_stack':before['state_stack'],
                'scope':'Selected city/officer/district and active army records; not the complete world'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--city',type=int,default=19)
    parser.add_argument('--officer',type=int,default=666)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    reader=None
    try:
        reader=BattleObserver()
        result=reader.capture(args.city,args.officer)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        state=result['critical_state']
        print(json.dumps({'date':state['date'],'city':state['city']['name'],
                          'garrison':state['city']['garrison'],'officer':state['officer']['name'],
                          'action_points':state['district']['action_points'],
                          'officer_units':state['officer_units'],
                          'active_unit_count':len(result['all_active_units']),
                          'critical_state_sha256':result['critical_state_sha256']},ensure_ascii=False,indent=2))
    finally:
        if reader:reader.close()


if __name__=='__main__':main()
