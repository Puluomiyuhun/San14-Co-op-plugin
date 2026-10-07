"""Find RIP-relative references including inlined 32-bit RNG accesses."""
import json,re,struct
from bisect import bisect_right
import disasm_chained as d
target=0x18EB8B0
found=[]
for match in re.finditer(rb'[\x8b\x89\x03\x01\x33\x31\x39\x3b\x81\xc7][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',d.image[0x1000:0x123BACF]):
    at=match.start()+0x1000
    displacement=struct.unpack_from('<i',d.image,at+2)[0]
    size=10 if d.image[at] in (0x81,0xc7) else 6
    if at+size+displacement!=target:continue
    idx=bisect_right(d.starts,at)-1
    fragment=d.entries[idx] if idx>=0 and at<d.entries[idx][1] else None
    # Decode the enclosing fragment to validate a real instruction boundary.
    candidates=list(d.decoder.disasm(d.image[fragment[0]:fragment[1]],fragment[0])) if fragment else list(d.decoder.disasm(d.image[at:at+size],at))
    ins=next((i for i in candidates if i.address<=at<i.address+i.size and
        any(o.type==d.capstone.x86.X86_OP_MEM and o.mem.base==d.capstone.x86.X86_REG_RIP and i.address+i.size+o.mem.disp==target for o in i.operands)),None)
    if ins is None:continue
    row={'rva':hex(ins.address),'instruction':ins.mnemonic+' '+ins.op_str,
         'primary':hex(d.primary(fragment)[0]) if fragment else None,'unwind_fragment_validated':bool(fragment)}
    if row not in found:found.append(row)
(d.ROOT/'rng-global-accesses.json').write_text(json.dumps(found,indent=2),encoding='utf-8')
print(json.dumps(found,indent=2))
