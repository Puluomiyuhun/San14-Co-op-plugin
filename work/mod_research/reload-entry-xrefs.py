"""Offline candidate references for native in-session reload control flow."""
import json
import re
import struct
import sys
sys.argv = sys.argv[:1]
import disasm_chained as d

image = d.image
targets = {0x508B40, 0x2EE4A0, 0x425750, 0x412410, 0x4DA390, 0x4AA200, 0x3DFB40}
globals_ = {0x201EC08, 0x201ECD0, 0x201ECD4, 0x201ECD8, 0x201ECE0, 0x2025320}
labels = {}
for at in (0x4AA597, 0x4AA3B6, 0x465B4C, 0x465B69, 0x465B81, 0x465BA5, 0x4DA39C):
    ins = next(d.decoder.disasm(image[at:at+15], at))
    op = ins.operands[1]
    assert ins.mnemonic == 'lea' and op.mem.base == d.capstone.x86.X86_REG_RIP
    target = ins.address + ins.size + op.mem.disp
    labels[hex(at)] = {'rva': hex(target), 'value': image[target:image.index(0,target)].decode('ascii')}
    globals_.add(target)
refs = []
md = d.capstone.Cs(d.capstone.CS_ARCH_X86, d.capstone.CS_MODE_64)
for a,z,u in d.entries:
    if a >= 0x123BACF:
        continue
    for address,size,mnemonic,operands in md.disasm_lite(image[a:z],a):
        reason = None
        if mnemonic in ('call','jmp') and operands.startswith('0x') and int(operands,0) in targets:
            reason = 'direct_target'
        if '[rip ' in operands:
            match = re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]', operands)
            if match:
                target = address+size+int(match[2],0)*(1 if match[1]=='+' else -1)
                if target in globals_:
                    reason = f'global_or_label:{target:#x}'
        if re.search(r'\+ 0x3ec\]',operands):
            reason = 'offset_candidate_untyped_3ec'
        if reason:
            refs.append({'rva':hex(address),'function':hex(d.primary((a,z,u))[0]),'instruction':f'{mnemonic} {operands}','reason':reason})
out = {'game_access':False,'labels':labels,'references':refs,'scope':'Unwind-bounded linear candidate scan; 0x3ec offsets are untyped; jump tables may decode as data; no complete control-flow proof.'}
(d.ROOT/'reload-entry-xrefs.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
