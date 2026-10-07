"""Offline reference candidates for changed city fields; no game access.

Offset matches alone do not prove a city receiver. Unwind-aligned linear
decoding is not exhaustive (indirect and bulk accesses may be absent).
"""
import hashlib
import json
import re
import sys
sys.argv=sys.argv[:1]
import disasm_chained as d

def main():
    md=d.capstone.Cs(d.capstone.CS_ARCH_X86,d.capstone.CS_MODE_64)
    detail=d.capstone.Cs(d.capstone.CS_ARCH_X86,d.capstone.CS_MODE_64);detail.detail=True
    rows=[]
    for a,z,u in d.entries:
        if a>=0x123bacf:continue
        for at,size,mnemonic,operands in md.disasm_lite(d.image[a:z],a):
            if not re.search(r'\+ 0xa[04]\]',operands):continue
            ins=next(detail.disasm(d.image[at:at+size],at))
            memory=[{'operand':n,'offset':op.mem.disp,'width':op.size,'access':op.access,
                     'base':ins.reg_name(op.mem.base)} for n,op in enumerate(ins.operands)
                    if op.type==d.capstone.x86.X86_OP_MEM and op.mem.disp in (0xA0,0xA4)]
            rows.append({'rva':hex(at),'primary_rva':hex(d.primary((a,z,u))[0]),
                         'instruction':mnemonic+' '+operands,'memory':memory})
    result={'schema':'san14.city-startup-field-candidates.v1','game_access':False,
            'image_sha256':hashlib.sha256(d.image).hexdigest(),'references':rows,'scope':__doc__.strip()}
    (d.ROOT/'city-startup-field-candidates.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    nearby=[r for r in rows if 0x200000<=int(r['primary_rva'],16)<0x240000]
    print(json.dumps({'total_candidates':len(rows),'near_city_methods':nearby},indent=2))

if __name__=='__main__':main()
