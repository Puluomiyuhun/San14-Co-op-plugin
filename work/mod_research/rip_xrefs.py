from pathlib import Path
import sys,struct,re,json
sys.path.insert(0,str(Path('work/mod_research/python_deps').resolve()))
import capstone
root=Path('work/mod_research')
b=(root/'game-runtime-image.bin').read_bytes()
pdata=(root/'runtime-pdata.bin').read_bytes()
entries=[struct.unpack_from('<III',pdata,i) for i in range(0,len(pdata)-11,12)]
targets={int(arg,0) for arg in sys.argv[1:]}
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
rows=[]
for hit in re.finditer(rb'[\x48-\x4f][\x8d\x8b\x89][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',b[0x1000:19118286]):
    i=hit.start()+0x1000
    target=i+7+struct.unpack_from('<i',b,i+3)[0]
    if target not in targets:continue
    match=next(((a,z) for a,z,u in entries if a<=i<z),None)
    rows.append({'rva':i,'target':target,'unwind_range':match})
    text='; '.join(f'{ins.address:#x} {ins.mnemonic} {ins.op_str}' for ins in md.disasm(b[i:i+48],i))
    print(hex(i), 'RANGE', [hex(x) for x in match] if match else None,text)
(root/'last-rip-xrefs.json').write_text(json.dumps(rows,indent=2))
