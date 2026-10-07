"""Faults are substituted into local read results; game memory is never written."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs'/'san14-link'))
from battle_observer import BattleObserver
from troops_reader import capture_model

class MemoryOverlay:
    def __init__(self, real, edits):
        self.real,self.edits,self.base=real,edits,real.base
    def read(self,address,size):
        raw=bytearray(self.real.read(address,size))
        for location,replacement in self.edits.items():
            first=max(location,address);last=min(location+len(replacement),address+size)
            if first<last:raw[first-address:last-address]=replacement[first-location:last-location]
        return bytes(raw)

class ReaderOverlay:
    def __init__(self,real,edits):self.real,self.memory=real,MemoryOverlay(real.memory,edits)
    def snapshot(self):return self.real.snapshot()
    def require_type(self,address,name):return self.real.require_type(address,name)

def main():
    reader=BattleObserver()
    try:
        rd=lambda a,w=8:int.from_bytes(reader.memory.read(a,w),'little')
        b=reader.memory.base;root=rd(b+0x1FCA1E0)
        group0=rd(root+0x7F000);handle=rd(root+0x60);slot=rd(handle,4)
        counts=rd(b+0x201D3C8);heads=rd(b+0x201D3B0);head=rd(heads+slot*8)
        tests=[('indirect_target',b+0x129FC08,b+0x2F63F0,8),
               ('group_table_identity',root+0x7F008,group0+0x80,8),
               ('pointer_pool_disabled',b+0x201D3A8,0,8),
               ('pointer_pool_count',counts+slot*8,502,8),
               ('pointer_list_cycle',head+8,head,8),
               ('relation_pool_capacity',b+0x1FC97A0,65,4)]
        results=[]
        for name,address,value,width in tests:
            try:capture_model(ReaderOverlay(reader,{address:value.to_bytes(width,'little')}))
            except RuntimeError as error:results.append({'case':name,'rejected':True,'reason':str(error)})
            else:raise AssertionError(f'Invalid input accepted: {name}')
        result={'result':'PASS','cases':results,'game_memory_writes':0,'faults_applied_only_to_local_read_copies':True}
        (ROOT/'troops-reader-guard-tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True))
    finally:reader.close()

if __name__=='__main__':main()
