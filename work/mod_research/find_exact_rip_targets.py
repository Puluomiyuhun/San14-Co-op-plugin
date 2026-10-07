"""Offline RIP references, including 32-bit instructions and trailing immediates.
Boundaries are checked inside unwind fragments; leaf functions remain outside coverage.
"""
import struct,sys,json
from bisect import bisect_right
args=sys.argv[1:];sys.argv=sys.argv[:1]
import disasm_chained as d
targets={int(a,0) for a in args}; hits=set()
# A RIP displacement may be followed by no immediate, imm8 or imm32.
for pos in range(0x1000,min(len(d.image)-8,0x123bb00)):
    v=struct.unpack_from('<i',d.image,pos)[0]
    if not any(pos+4+extra+v in targets for extra in (0,1,4)):continue
    k=bisect_right(d.starts,pos)-1
    if k>=0 and pos<d.entries[k][1]:hits.add(d.entries[k])
out=[]
for e in sorted(hits):
    for ins in d.decoder.disasm(d.image[e[0]:e[1]],e[0]):
        for op in ins.operands:
            if op.type==d.capstone.x86.X86_OP_MEM and op.mem.base==d.capstone.x86.X86_REG_RIP:
                target=ins.address+ins.size+op.mem.disp
                if target in targets:out.append({'at':hex(ins.address),'root':hex(d.primary(e)[0]),
                    'target':hex(target),'instruction':ins.mnemonic+' '+ins.op_str})
path=d.ROOT/('rip-targets-'+'-'.join(f'{t:x}' for t in sorted(targets))+'.json')
path.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
