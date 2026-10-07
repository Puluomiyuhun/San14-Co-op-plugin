from pathlib import Path
import sys, struct, json
sys.path.insert(0,str(Path('outputs/san14-link').resolve()))
from game_reader import GameReader,DATA_POINTER_RVA
sys.stdout.reconfigure(encoding='utf-8')
r=GameReader()
try:
    m=r.memory
    print(json.dumps(r.snapshot(),ensure_ascii=False))
    root=r.pointer(m.base+DATA_POINTER_RVA)
    rows=[]
    for i in (0,7,18,157,200):
        p=r.pointer(root+0x76c00+i*8)
        r.require_type(p,'CTacticsData')
        raw=m.read(p,0x88)
        print(i,hex(p),raw[0x10:0x40].hex(),repr(raw[0x10:0x40].decode('utf-16le',errors='replace')))
        Path(f'work/mod_research/tactics-{i}.bin').write_bytes(raw)
        rows.append({'id':i,'bytes':raw.hex()})
    Path('work/mod_research/tactics-live.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
finally:r.close()
