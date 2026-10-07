"""Copy the two native percentage-selection tails into an isolated fixture.

Upstream economic input calculation and city writes are deliberately excluded.
Settings object plumbing and the region-to-force lookup have explicit stubs;
the original player predicate, player lookup and force ID accessor are copied.
Nothing produced here is installed into SAN14.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone

RANGES=[('component0',0x28DDFE,0x28DF03,0x40),('component1',0x28DA37,0x28DB37,0x1040),
        ('is_player',0x2110B0,0x211109,0x2000),('player_force',0x2F21E0,0x2F220A,0x3000),
        ('force_id',0x20B610,0x20B63A,0x4000)]
EXTERNAL={0x20A470:0x8000,0x39C260:0x8020,0x74ABC0:0x8040,0x398520:0x8060,
          0x39C7D0:0x8080,0x58E520:0x80A0}
HOOK=0x80C0

def main():
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
    offsets={a:off for _,a,_,off in RANGES};patches=[];data={};meta=[];returns=[]
    header='// Generated isolated native arithmetic tails, not a live adapter.\n'
    for name,a,z,off in RANGES:
        code=image[a:z];instructions=list(md.disasm(code,a));assert sum(i.size for i in instructions)==len(code)
        bounds={i.address for i in instructions}|{z};refs=[]
        for ins in instructions:
            if ins.mnemonic=='call' or ins.mnemonic.startswith('j'):
                op=ins.operands[0]
                if op.type==capstone.x86.X86_OP_IMM:
                    target=op.imm
                    if a<=target<=z:assert target in bounds
                    else:
                        assert ins.mnemonic in ('call','jmp') and ins.size==5 and target in offsets|EXTERNAL,(name,hex(target))
                        dest=offsets.get(target,EXTERNAL.get(target))
                        if target==0x2110B0:
                            dest=HOOK;returns.append((off+ins.address-a+ins.size,ins.address+ins.size))
                        patches.append((off+ins.address-a+ins.imm_offset,off+ins.address-a+ins.size,dest))
                        refs.append({'rva':hex(ins.address),'target':hex(target),'stubbed':target in EXTERNAL})
                else:assert name=='is_player' and ins.op_str=='qword ptr [rdx + 0x60]'
            for op in ins.operands:
                if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
                    rva=ins.address+ins.size+op.mem.disp;dest=data.setdefault(rva,0xA000+len(data)*0x10)
                    assert ins.disp_size==4
                    patches.append((off+ins.address-a+ins.disp_offset,off+ins.address-a+ins.size,dest))
        header+=f'constexpr unsigned fn_{name}=0x{off:X};\nstatic const unsigned char bytes_{name}[]={{'+','.join(map(str,code))+'};\n'
        meta.append({'name':name,'start_rva':hex(a),'end_rva':hex(z),'offset':off,
                     'sha256':hashlib.sha256(code).hexdigest(),'references':refs})
    assert {rva for _,rva in returns}=={0x28DE76,0x28DAAA}
    header+='struct Block {const unsigned char* bytes; unsigned size,offset;};\nstatic const Block blocks[]={'
    header+=','.join('{bytes_%s,sizeof bytes_%s,fn_%s}'%(n,n,n) for n,_,_,_ in RANGES)+'};\n'
    header+='struct Patch {unsigned at,next,target;};\nstatic const Patch patches[]={'+','.join('{%d,%d,%d}'%p for p in patches)+'};\n'
    header+='struct Slot {unsigned rva,offset; unsigned char bytes[8];};\nstatic const Slot slots[]={'
    header+=','.join('{%d,%d,{%s}}'%(r,o,','.join(map(str,image[r:r+8]))) for r,o in data.items())+'};\n'
    header+='struct Caller {unsigned offset,rva;};\nstatic const Caller callers[]={'+','.join('{%d,%d}'%x for x in returns)+'};\n'
    # Source tables are independent evidence for the arithmetic oracle.
    # Derive table addresses from decoded RIP-relative operands.
    rate_sites=[[0x28DE60,0x28DE58,0x28DE50,0x28DE48,0x28DEC1,0x28DECC],
                [0x28DA94,0x28DA8C,0x28DA84,0x28DA7C,0x28DAF5,0x28DB00]]
    rate_rvas=[]
    for sites in rate_sites:
        group=[]
        for at in sites:
            ins=next(md.disasm(image[at:at+15],at));op=ins.operands[-1]
            assert op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP
            rva=ins.address+ins.size+op.mem.disp;assert rva in data;group.append(rva)
        rate_rvas.append(group)
    rates=[[struct.unpack_from('<i',image,rva)[0] for rva in group] for group in rate_rvas]
    header+='static const int originalRates[2][6]={'+','.join('{'+','.join(map(str,g))+'}' for g in rates)+'};\n'
    (ROOT/'economy_selector_fixture_code.h').write_text(header,encoding='utf-8')
    report={'schema':'san14.economy-selector-native-source.v1','blocks':meta,'relocations':len(patches),
            'rates':rates,'rate_rvas':[[hex(v) for v in group] for group in rate_rvas],
            'caller_returns':[hex(r) for _,r in returns],
            'external_stubs':{hex(k):v for k,v in EXTERNAL.items()},'scope':__doc__.strip(),
            'full_city_delta_replay':False,'game_access':False}
    (ROOT/'economy-selector-native-source.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'blocks':len(meta),'rates':rates,'caller_returns':report['caller_returns'],'game_access':False}))

if __name__=='__main__':main()
