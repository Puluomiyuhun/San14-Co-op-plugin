"""Offline references for the native title identity handoff and force-ID cache.

Unwind-aligned linear decoding only. Offset matches do not identify the object;
indirect/bulk/leaf-code references are not exhaustively covered.
"""
from datetime import datetime
import json
import re
import struct
import sys
sys.argv=sys.argv[:1]
import disasm_chained as d


def main():
    image=d.image
    base=struct.unpack_from('<Q',image,0x12CC4A8+0x28)[0]-0x3F9B00
    md=d.capstone.Cs(d.capstone.CS_ARCH_X86,d.capstone.CS_MODE_64)
    detail=d.capstone.Cs(d.capstone.CS_ARCH_X86,d.capstone.CS_MODE_64)
    detail.detail=True
    title_name=image.index(b'.?AVCTitleState@@\0')
    descriptor=title_name-16
    tables=[]
    for hit in re.finditer(re.escape(struct.pack('<I',descriptor)),image):
        loc=hit.start()-12
        if loc<0 or struct.unpack_from('<I',image,loc)[0]!=1:
            continue
        if struct.unpack_from('<I',image,loc+20)[0]!=loc:
            continue
        for pointer in re.finditer(re.escape(struct.pack('<Q',base+loc)),image):
            vt=pointer.start()+8
            first=struct.unpack_from('<Q',image,vt)[0]-base
            if not 0x1000<=first<0x123bacf:
                continue
            methods={}
            for offset in range(0,0x80,8):
                dest=struct.unpack_from('<Q',image,vt+offset)[0]-base
                if not 0x1000<=dest<0x123bacf:
                    break
                methods[hex(offset)]=hex(dest)
            tables.append({'vtable_rva':hex(vt),'locator_rva':hex(loc),
                           'object_offset':struct.unpack_from('<I',image,loc+4)[0], 'methods':methods})
    cache, offsets, calls, gaps=[],[],[],[]
    targets={0x2FC850,0x4DA390,0x3F7B60,0x4BDD90,0x4BEE50}
    for a,z,u in d.entries:
        if a>=0x123bacf:
            continue
        end=a
        owner=hex(d.primary((a,z,u))[0])
        for address,size,mnemonic,operands in md.disasm_lite(image[a:z],a):
            end=address+size
            row={'rva':hex(address),'primary_rva':owner,'instruction':mnemonic+' '+operands}
            if '[rip ' in operands:
                match=re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]',operands)
                if match:
                    displacement=int(match[2],0)*(1 if match[1]=='+' else -1)
                    if end+displacement==0x1FCA518:
                        instruction=next(detail.disasm(image[address:end],address))
                        row['operand_access']=[op.access for op in instruction.operands]
                        cache.append(row)
            if re.search(r'\+ 0x4a[08]\]',operands):
                offsets.append(row)
            if mnemonic in ('call','jmp') and operands.startswith('0x') and int(operands,0) in targets:
                calls.append(row)
        if end!=z:
            gaps.append([hex(end),hex(z)])
    result={'schema':'san14.startup-continuation-audit.v1',
            'created':datetime.now().astimezone().isoformat(), 'game_access':False,
            'title_vtables':tables, 'cache_references':cache,
            'offset_4a0_4a8_candidates':offsets,'direct_calls':calls,'undecoded_ranges':gaps,
            'scope':__doc__.strip()}
    (d.ROOT/'startup-continuation-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('offset_4a0_4a8_candidates','undecoded_ranges')},indent=2))
    print('offset candidates',len(offsets),'undecoded ranges',len(gaps))


if __name__=='__main__':
    main()
