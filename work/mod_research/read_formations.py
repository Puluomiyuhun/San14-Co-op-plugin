from pathlib import Path
import sys, struct
sys.path.insert(0,str(Path('outputs/san14-link').resolve()))
from game_reader import GameReader,DATA_POINTER_RVA
sys.stdout.reconfigure(encoding='utf-8')
r=GameReader()
try:
    m=r.memory
    root=r.pointer(m.base+DATA_POINTER_RVA)
    for i in (0,1,2,3,4,5,6,7,11):
        p=r.pointer(root+0x76b58+i*8)
        v=r.pointer(p); loc=r.pointer(v-8)
        td=struct.unpack('<I',m.read(loc+12,4))[0]
        name=m.read(m.base+td+16,100).split(b'\0')[0].decode('ascii')
        raw=m.read(p,0xb0)
        print(i,name,raw[0x10:0x50].hex(),repr(raw[0x10:0x50].decode('utf-16le',errors='replace')))
        Path(f'work/mod_research/formation-{i}.bin').write_bytes(raw)
finally:r.close()
