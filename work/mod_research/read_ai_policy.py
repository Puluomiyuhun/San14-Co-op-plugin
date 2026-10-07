from pathlib import Path
import sys,struct,json
sys.path.insert(0,str(Path('outputs/san14-link').resolve()))
from game_reader import GameReader,DATA_POINTER_RVA
sys.stdout.reconfigure(encoding='utf-8')
r=GameReader()
try:
    m=r.memory
    root=r.pointer(m.base+DATA_POINTER_RVA)
    manager=r.pointer(m.base+0x1a1f6c0)
    r.require_type(manager,'CAIManager')
    raw=m.read(manager,0xc0)
    Path('work/mod_research/ai-manager-policy.bin').write_bytes(raw)
    head,count=struct.unpack_from('<QQ',raw,0x60)
    print('MANAGER',hex(manager),'GLOBAL',struct.unpack_from('<I',raw,0x30)[0],'MAPHEAD',hex(head),'COUNT',count)
    assert count<=64
    header=m.read(head,0x30)
    nodes=[struct.unpack_from('<Q',header,8)[0]]
    visited=set();results=[]
    forces={r.pointer(root+0xdca0+i*8):i for i in range(52)}
    while nodes:
        p=nodes.pop()
        if p==head:continue
        assert p not in visited and len(visited)<64
        visited.add(p)
        data=m.read(p,0x30)
        assert data[0x19]==0
        left,_,right=struct.unpack_from('<QQQ',data)
        key=struct.unpack_from('<Q',data,0x20)[0]
        value=struct.unpack_from('<I',data,0x28)[0]
        r.require_type(key,'CForceData')
        force_id=forces[key]
        ruler_id=struct.unpack('<H',m.read(key+0x10,2))[0]
        person=r.pointer(root+0x148+ruler_id*8)
        record=m.read(person+0x10,38)
        name=record[2:20].decode('utf-16le').split('\0')[0]+record[20:38].decode('utf-16le').split('\0')[0]
        row={'force_id':force_id,'ruler_id':ruler_id,'ruler_name':name,'gate_value':value}
        results.append(row)
        nodes.extend((left,right))
    assert len(visited)==count
    assert m.read(manager,0xc0)==raw
    report={'global_gate':struct.unpack_from('<I',raw,0x30)[0],'per_force_entries':results,'default_if_absent':1,'applied_to_game':False}
    Path('work/mod_research/ai-policy-live.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
finally:r.close()
