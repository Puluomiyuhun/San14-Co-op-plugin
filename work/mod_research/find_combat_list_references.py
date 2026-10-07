"""Bounded offline reference candidates; only instruction-boundary-validated hits retained."""
import json,re,struct
from bisect import bisect_right
import disasm_chained as d
found=[];cache={}
def decoded(at):
    i=bisect_right(d.starts,at)-1
    if i<0 or at>=d.entries[i][1]:return None,None
    e=d.entries[i]
    if e not in cache:cache[e]=list(d.decoder.disasm(d.image[e[0]:e[1]],e[0]))
    return e,next((x for x in cache[e] if x.address<=at<x.address+x.size),None)
for m in re.finditer(rb'[\x8b\x89\x8d\x03\x01\x33\x31\x39\x3b\x81\xc7][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',d.image[0x1000:0x123bacf]):
    at=m.start()+0x1000;size=10 if d.image[at] in (0x81,0xc7) else 6
    target=at+size+struct.unpack_from('<i',d.image,at+2)[0]
    if not 0x1FC9760<=target<0x1FC97A8:continue
    e,ins=decoded(at)
    if not ins:continue
    if any(o.type==d.capstone.x86.X86_OP_MEM and o.mem.base==d.capstone.x86.X86_REG_RIP and ins.address+ins.size+o.mem.disp==target for o in ins.operands):
        found.append({'kind':'annihilate_pool','at':hex(ins.address),'target':hex(target),'root':hex(d.primary(e)[0]),'instruction':ins.mnemonic+' '+ins.op_str})
for m in re.finditer(rb'[\x48-\x4f][\x8d\x83][\x40-\xff]\x68',d.image[0x1000:0x510000]):
    at=m.start()+0x1000;e,ins=decoded(at)
    if not ins or ins.address!=at:continue
    if ins.mnemonic=='lea' and any(o.type==d.capstone.x86.X86_OP_MEM and o.mem.disp==0x68 and o.mem.base not in (d.capstone.x86.X86_REG_RSP,d.capstone.x86.X86_REG_RBP) for o in ins.operands):
        found.append({'kind':'offset68_lea','at':hex(ins.address),'root':hex(d.primary(e)[0]),'instruction':ins.mnemonic+' '+ins.op_str})
    elif ins.mnemonic=='add' and len(ins.operands)==2 and ins.operands[1].type==d.capstone.x86.X86_OP_IMM and ins.operands[1].imm==0x68 and ins.operands[0].reg not in (d.capstone.x86.X86_REG_RSP,d.capstone.x86.X86_REG_RBP):
        found.append({'kind':'offset68_add','at':hex(ins.address),'root':hex(d.primary(e)[0]),'instruction':ins.mnemonic+' '+ins.op_str})
unique={r['at']:r for r in found};out=list(unique.values())
(d.ROOT/'combat-list-references.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
