"""Relocate two native geometry routines into an isolated fixture, never the game."""
from pathlib import Path
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
b=(ROOT/'game-runtime-image.bin').read_bytes()
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
segments=[(0xfac0,0xfb57,0),(0x14f10,0x1500f,0x200),(0x161200,0x161209,0x600)]
buf=bytearray(4096);changes=[]
for start,end,dest in segments:
    code=b[start:end];insns=list(md.disasm(code,start))
    assert sum(i.size for i in insns)==len(code)
    buf[dest:dest+len(code)]=code
    for ins in insns:
        off=dest+ins.address-start
        if ins.mnemonic=='call':
            assert ins.op_str=='0x14f10' and ins.size==5
            struct.pack_into('<i',buf,off+1,0x200-(off+ins.size))
            changes.append({'rva':hex(ins.address),'kind':'call','destination_fixture_offset':'0x200'})
        for op in ins.operands:
            if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
                old=ins.address+ins.size+op.mem.disp
                new={0xfac4:0x400,0xfae5:0x410,0xfafc:0x420}[ins.address]
                width=op.size
                assert width in (4,16)
                buf[new:new+width]=b[old:old+width]
                struct.pack_into('<i',buf,off+ins.disp_offset,new-(off+ins.size))
                changes.append({'rva':hex(ins.address),'kind':'data','source_rva':hex(old),
                    'destination_fixture_offset':hex(new),'original_bytes':b[old:old+width].hex()})
        if ins.mnemonic.startswith('j'):
            assert start<=ins.operands[0].imm<end
assert len(changes)==4
assert struct.unpack_from('<f',buf,0x410)[0]==1.0
assert struct.unpack_from('<4I',buf,0x420)==(0x80000000,)*4
(ROOT/'visibility_fixture_code.h').write_text('static const unsigned char fixtureCode[] = {'+','.join(hex(x) for x in buf)+'};\n',encoding='ascii')
meta={'segments':[{'rva':hex(s),'end':hex(e),'fixture_offset':hex(o),'sha256':hashlib.sha256(b[s:e]).hexdigest()} for s,e,o in segments],
    'relocations':changes,'scope':'Native FAC0 projection predicate, its native matrix transform 14F10 and native integer-level predicate 161200. Only branch flag is a controlled fixture input. No game handles/calls, no complete battle simulation.'}
(ROOT/'visibility-fixture-source.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'segments':len(segments),'relocations':len(changes),'result':'PASS'}))
