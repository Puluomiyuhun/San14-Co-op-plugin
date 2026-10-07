from pathlib import Path
import sys,struct,json
sys.path.insert(0,str(Path('outputs/san14-link').resolve()))
sys.path.insert(0,str(Path('work/mod_research/python_deps').resolve()))
from readonly_probe import Memory,find_game_pid
import capstone
root=Path('work/mod_research')
b=(root/'game-runtime-image.bin').read_bytes()
if not (root/'runtime-pdata.bin').exists():
    m=Memory(find_game_pid())
    try:
        s=next(s for s in m.sections if s['name']=='.pdata')
        (root/'runtime-pdata.bin').write_bytes(m.read(m.base+s['rva'],s['size']))
    finally:m.close()
pdata=(root/'runtime-pdata.bin').read_bytes()
entries=[struct.unpack_from('<III',pdata,i) for i in range(0,len(pdata)-11,12)]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
for arg in sys.argv[1:]:
    parts=arg.split(':')
    rva=int(parts[0],0)
    match=(rva,int(parts[1],0)) if len(parts)==2 else next(((a,z) for a,z,u in entries if a<=rva<z),None)
    if not match:match=(rva,rva+128)
    a,z=match
    lines=[f'Code range / unwind fragment {a:#x}..{z:#x}; target {rva:#x}']
    for ins in md.disasm(b[a:z],a):lines.append(f'{ins.address:#x}: {ins.mnemonic} {ins.op_str}')
    dest=root/f'disasm-{rva:x}.txt';dest.write_text('\n'.join(lines),encoding='utf-8')
    print(dest,'start',hex(a),'size',z-a,'instructions',len(lines)-1)
