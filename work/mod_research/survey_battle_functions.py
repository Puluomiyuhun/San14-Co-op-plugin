"""Offline unwind-group survey. Explicitly retain undecodable/data gaps.

Linear references are candidates only, not proof of reachability. No game access.
"""
from pathlib import Path
import sys,json
arguments=sys.argv[1:]
sys.argv=sys.argv[:1]
import disasm_chained as d
from bisect import bisect_right
for argument in arguments:
    address=int(argument,0)
    index=bisect_right(d.starts,address)-1
    if index<0 or address>=d.entries[index][1]:
        print(hex(address),'no unwind group');continue
    root=d.primary(d.entries[index]);fragments=sorted(set(d.groups[root]+[root]))
    lines=[f'Primary {root[0]:#x}; requested {address:#x}',
           'OFFLINE LINEAR SURVEY: embedded data may decode as instructions; not a complete semantic graph.']
    references=[];gaps=[]
    for a,z,_ in fragments:
        lines.append(f'\nFragment {a:#x}..{z:#x}');end=a
        for ins in d.decoder.disasm(d.image[a:z],a):
            end=ins.address+ins.size
            lines.append(f'{ins.address:#x}: {ins.mnemonic} {ins.op_str}')
            if ins.mnemonic in ('call','jmp') and len(ins.operands)==1 and ins.operands[0].type==d.capstone.x86.X86_OP_IMM:
                references.append({'at':ins.address,'op':ins.mnemonic,'target':ins.operands[0].imm})
        if end!=z:
            gaps.append([end,z]);lines.append(f'UNDECODED/DATA {end:#x}..{z:#x}: '+d.image[end:z].hex())
    (d.ROOT/f'survey-{root[0]:x}.txt').write_text('\n'.join(lines),encoding='utf-8')
    (d.ROOT/f'survey-{root[0]:x}.json').write_text(json.dumps({
        'primary':root[0],'fragments':[[a,z] for a,z,_ in fragments],'gaps':gaps,'references':references},indent=2))
    print(hex(root[0]),'fragments',len(fragments),'refs',len(references),'undecoded',gaps)
