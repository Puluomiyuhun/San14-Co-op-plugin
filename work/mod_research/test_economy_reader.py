"""Replay real reads and reject corrupt or moving economic samples offline."""
import hashlib
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs/san14-link'))
from economy_reader import capture_economy,city_area_order
from game_reader import GameReader

class Memory:
    def __init__(self,source):
        self.base=source['base'];self.image_size=source['image_size'];self.rows={};self.second_read=None;self.seen=0
        for address,size,hx in source['reads']:
            b=bytes.fromhex(hx);assert len(b)==size
            for i,value in enumerate(b):
                at=address+i
                if at in self.rows:assert self.rows[at]==value,'Recorded overlap differs'
                self.rows[at]=value
    def read(self,address,size):
        if self.second_read==(address,size):
            self.seen+=1
            if self.seen==2:self.rows[address+0x3A]^=1
        try:return bytes(self.rows[address+i] for i in range(size))
        except KeyError as e:raise RuntimeError('Read outside captured fixture') from e
    def write_fixture(self,address,fmt,*values):
        for i,b in enumerate(struct.pack(fmt,*values)):self.rows[address+i]=b
    def close(self):pass

def main():
    path=ROOT/'economy-reader-memory-fixture.json';source=json.loads(path.read_text(encoding='utf-8'));cases=[]
    def reader():
        r=object.__new__(GameReader);r.pid=source['pid'];r.sha256=source['sha256'];r.memory=Memory(source);return r
    original=reader();expected=source['expected_sample']
    actual=capture_economy(original)
    assert json.loads(json.dumps(actual))==expected
    cases.append({'case':'real_read_transcript_exact_replay','result':'PASS'})
    root=original.pointer(original.memory.base+0x1FCA1E0);area=original.pointer(root+0x6C860+8)
    def reject(name,mutator):
        r=reader();mutator(r)
        try:capture_economy(r)
        except (RuntimeError,ValueError):cases.append({'case':name,'result':'PASS'})
        else:raise AssertionError(f'{name} was accepted')
    reject('wrong_code_fingerprint',lambda r:r.memory.write_fixture(r.memory.base+0x28DBAC,'B',0))
    reject('area_table_stride_mismatch',lambda r:r.memory.write_fixture(root+0x6C860+8,'Q',area+8))
    reject('wrong_area_type',lambda r:r.memory.write_fixture(area,'Q',r.pointer(root+0xDAA8+8)))
    reject('invalid_area_city',lambda r:r.memory.write_fixture(area+0x35,'B',52))
    reject('invalid_center_hex',lambda r:r.memory.write_fixture(area+0x3A,'H',48400))
    reject('invalid_assigned_officer',lambda r:r.memory.write_fixture(area+0x36,'H',6001))
    reject('wrong_pool_capacity',lambda r:r.memory.write_fixture(r.memory.base+0x201D3E0,'I',1))
    reject('area_changed_before_verification',lambda r:setattr(r.memory,'second_read',(area+0x10,0x88)))
    areas={int(k):v for k,v in expected['areas'].items()};order=expected['native_area_order']
    for name,seq in [('duplicate_list_member',order+[order[0]]),('unknown_list_member',order+[501])]:
        try:city_area_order(seq,areas)
        except ValueError:cases.append({'case':name,'result':'PASS'})
        else:raise AssertionError(name)
    for city,ids in expected['city_area_order'].items():
        assert ids==[i for i in order if areas[i]['city_id']==int(city)]
    assert all(len(bytes.fromhex(p['raw_10_200']))==0x1F0 for p in expected['assigned_officers'].values())
    assert actual['complete_economy_inputs'] is False and actual['missing_dependencies']
    cases.append({'case':'native_order_and_extended_person_coverage','result':'PASS'})
    report={'schema':'san14.economy-reader-tests.v1','result':'PASS','cases':cases,'game_access':False,
            'fixture_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'reader_sha256':hashlib.sha256((ROOT.parents[1]/'outputs/san14-link/economy_reader.py').read_bytes()).hexdigest(),
            'scope':'Exact replay of a real stable read transcript plus corrupt and changing sample rejection. No game calculation or write.'}
    (ROOT/'economy-reader-tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':'PASS','cases':len(cases),'game_access':False}))

if __name__=='__main__':main()
