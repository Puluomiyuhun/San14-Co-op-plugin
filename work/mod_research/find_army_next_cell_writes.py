"""Locate word stores at +48, including leaf functions and disp8 encodings."""
import re,json
from bisect import bisect_right
import disasm_chained as d
from capstone.x86 import X86_OP_MEM,X86_REG_RSP,X86_REG_RBP
out=[];cache={}
for m in re.finditer(rb'\x66[\x40-\x4f]?\x89[\x40-\x7f]\x48',d.image[0x1000:0x510000]):
    at=m.start()+0x1000;i=bisect_right(d.starts,at)-1
    entry=d.entries[i] if i>=0 and at<d.entries[i][1] else None
    if entry:
        if entry not in cache:cache[entry]={x.address:x for x in d.decoder.disasm(d.image[entry[0]:entry[1]],entry[0])}
        ins=cache[entry].get(at)
    else:ins=next(d.decoder.disasm(d.image[at:at+15],at),None)
    if not ins or not ins.operands or ins.operands[0].type!=X86_OP_MEM:continue
    op=ins.operands[0]
    if op.mem.disp!=0x48 or op.mem.base in (X86_REG_RSP,X86_REG_RBP) or op.size!=2:continue
    out.append({'at':hex(at),'instruction':ins.mnemonic+' '+ins.op_str,
        'primary':hex(d.primary(entry)[0]) if entry else None,
        'validation':'unwind fragment instruction boundary' if entry else 'unverified leaf candidate'})
(d.ROOT/'army-next-cell-write-candidates.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
