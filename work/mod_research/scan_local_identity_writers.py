"""Bounded offline candidate scan; these are not all writes to world+3A."""
import json
import re
import sys
sys.argv=sys.argv[:1]
import disasm_chained as d
md=d.capstone.Cs(d.capstone.CS_ARCH_X86,d.capstone.CS_MODE_64)
rows=[]
for a,z,u in d.entries:
    if a>=0x123BACF:continue
    for address,size,mnemonic,operands in md.disasm_lite(d.image[a:z],a):
        if mnemonic in ('mov','and','or','xor','inc','dec','xchg') and re.match(r'byte ptr \[[^\]]+ \+ 0x3a\](?:,|$)',operands):
            rows.append({'at':hex(address),'function':hex(d.primary((a,z,u))[0]),'instruction':mnemonic+' '+operands})
result={'candidates':rows,'scope':'Byte stores at offset +3A in unwind-described captured code; many may target other object types. Not proof of world ownership, indirect/bulk-write coverage or safe entry points.'}
(d.ROOT/'local-identity-writer-candidates.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
