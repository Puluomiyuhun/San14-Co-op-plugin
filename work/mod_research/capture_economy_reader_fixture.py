"""Record a stable read transcript for offline sampler corruption checks."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs/san14-link'))
from economy_reader import capture_economy
from game_reader import GameReader

class RecordingMemory:
    def __init__(self,real):self.real=real;self.reads={}
    def __getattr__(self,key):return getattr(self.real,key)
    def read(self,address,size):
        value=self.real.read(address,size);key=(address,size)
        if key in self.reads and self.reads[key]!=value:raise RuntimeError('Memory changed during fixture recording')
        self.reads[key]=value;return value
    def close(self):self.real.close()

def main():
    reader=GameReader();memory=RecordingMemory(reader.memory);reader.memory=memory
    try:
        sample=capture_economy(reader)
        report={'schema':'san14.readonly-memory-transcript.v1','created':datetime.now().astimezone().isoformat(),
                'pid':reader.pid,'sha256':reader.sha256,'base':memory.base,'image_size':memory.image_size,
                'reads':[[address,size,data.hex()] for (address,size),data in sorted(memory.reads.items())],
                'expected_sample':sample,'game_writes':0}
        path=ROOT/'economy-reader-memory-fixture.json'
        path.write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
        print(json.dumps({'result':'RECORDED_STABLE_READ_TRANSCRIPT','unique_reads':len(memory.reads),
                          'total_read_bytes':sum(len(v) for v in memory.reads.values()),
                          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'game_writes':0}))
    finally:reader.close()

if __name__=='__main__':main()
