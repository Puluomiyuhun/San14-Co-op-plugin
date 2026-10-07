"""Archive-only action lookup ABI and dependency inventory."""
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'python_deps'))
import capstone
IMAGE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
PDATA_SHA='74e018f15ec009af5fd0e0d91ce981b82d7d970150b3dce5861f17d11eea2e9f'
image=(HERE/'game-runtime-image.bin').read_bytes();pdata=(HERE/'runtime-pdata.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()==IMAGE_SHA and hashlib.sha256(pdata).hexdigest()==PDATA_SHA
cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);cs.detail=True
def rows(at,end):
    return [dict(rva=hex(i.address),bytes=i.bytes.hex(),instruction=i.mnemonic+' '+i.op_str)
            for i in cs.disasm(image[at:end],at)]
def exact(at,text):
    row=rows(at,at+15)[0];assert row['instruction']==text,row;return row
regions=[];header='#pragma once\n#include <array>\n#include <cstdint>\nnamespace checkpoint_native_input_action {\n'
for name,lo,hi in [('Action',0x3A2DC0,0x3A2E80),('Singleton',0x292220,0x2922A1)]:
    code=image[lo:hi];ins=list(cs.disasm(code,lo));assert sum(i.size for i in ins)==len(code)
    assert ins[-1].mnemonic=='ret'
    if name=='Action':
        assert [(i.address,i.op_str) for i in ins if i.mnemonic=='call']==[(0x3A2DCD,'0x292220')]
        for i in ins:
            for op in i.operands:
                if op.type==capstone.x86.X86_OP_MEM and op.access&capstone.CS_AC_WRITE:
                    assert op.mem.base==capstone.x86.X86_REG_RSP,(i.address,i.op_str)
    regions.append(dict(name=name,rva=hex(lo),end_exclusive=hex(hi),bytes=code.hex(),
        sha256=hashlib.sha256(code).hexdigest(),instructions=rows(lo,hi)))
    header+=f'inline constexpr std::array<std::uint8_t,{len(code)}> k{name} = {{'+','.join(f'0x{b:02x}' for b in code)+'};\n'
source_instructions={'MapPointer':0x3A2DDC,'Active':0x3A2DD2,'TlsIndex':0x29222F,
                     'InitGuard':0x29224A,'Normal':0x292294}
rip_sources={}
for name,at in source_instructions.items():
    instruction=next(cs.disasm(image[at:at+15],at))
    operands=[op for op in instruction.operands if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP]
    assert len(operands)==1
    resolved=at+instruction.size+operands[0].mem.disp
    rip_sources[name]=hex(resolved)
    header+=f'inline constexpr std::uint32_t kArchived{name}Rva={resolved:#x};\n'
assert rip_sources==dict(MapPointer='0x1fd1678',Active='0x1905654',TlsIndex='0x203abc0',InitGuard='0x1fca118',Normal='0x1fca0a0')
header+='}\n'
functions=[struct.unpack_from('<III',pdata,i) for i in range(0,len(pdata),12) if struct.unpack_from('<I',pdata,i)[0]]
starts=[f[0] for f in functions];assert starts==sorted(starts)
callers=[];at=-1
while True:
    at=image.find(b'\xe8',at+1)
    if at<0 or at+5>len(image):break
    if at+5+struct.unpack_from('<i',image,at+1)[0]!=0x3A2DC0:continue
    index=bisect_right(starts,at)-1
    if index<0:continue
    lo,hi,_=functions[index]
    if not lo<=at<hi:continue
    instructions=list(cs.disasm(image[lo:hi],lo))
    for j,i in enumerate(instructions):
        if i.address==at and i.mnemonic=='call' and i.op_str=='0x3a2dc0':
            callers.append(dict(caller=hex(at),function=hex(lo),context=[dict(rva=hex(x.address),instruction=x.mnemonic+' '+x.op_str)
                           for x in instructions[max(0,j-5):j+3]]));break
anchors=[exact(0x3A2DCA,'movsxd rbx, ecx'),exact(0x3A2DCD,'call 0x292220'),
    exact(0x3A2DEC,'cmp ebx, 0x1e'),exact(0x3A2DF1,'lea rcx, [r8 + rbx*2]'),
    exact(0x3A2DF5,'movsxd rax, dword ptr [rdi + rcx*4 + 8]'),
    exact(0x3A2E12,'cmp byte ptr [rax + r9 + 0x158], 0'),
    exact(0x3A2E4F,'test dword ptr [r9 + 0x50], edx'),exact(0x3A2E70,'mov eax, 1'),
    exact(0x292235,'mov rax, qword ptr gs:[0x58]'),exact(0x292247,'mov eax, dword ptr [rdx + rcx]'),
    exact(0x292250,'jle 0x292294')]
report=dict(schema='san14.native-input-action-audit.v1',image_sha256=IMAGE_SHA,pdata_sha256=PDATA_SHA,
    regions=regions,anchors=anchors,callers=callers,rip_sources_derived_from_machine_code=rip_sources,
    abi='ECX unsigned validated action 0..30; original MOVSXD accepts signed register input but rejects outside range via JA. EAX is canonical 0 or 1.',
    sources=dict(mapping_pointer='base+1FD1678',mapping_extent='0x100; +8+action*8 and +12+action*8',
        normal_cache='base+1FCA0A0; +0 raw source pointer',raw='raw+50 modifiers; raw+158+key for 1..FF',
        active_gate='base+1905654 DWORD',tls_index='base+203ABC0 DWORD',tls_slots='current GS:[58]',
        tls_epoch='tls_slots[index]+10 DWORD',initialized_guard='base+1FCA118 DWORD'),
    side_effect_boundary='3A2DC0 writes only its stack; 292220 initialized branch reads TLS/guard and returns singleton address. Slow branch initializes the singleton and registers cleanup; it must be refused.',
    supported_mapping_codes='0 disabled, 1..FF physical keys, 101..104 => modifier masks 11/22/44/88',
    unproven=['Actual game owner exclusion/installation','Unhooked action/direct-key readers',
        '3A3810 is a cache-mutating conversion stage; it is not replaced or bypassed by this action bridge'],
    real_game_accessed=False,device_accessed=False,full_input_hold=False)
(HERE/'checkpoint_native_input_action_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(HERE/'checkpoint_native_input_action_archived.h').write_text(header,encoding='utf-8')
print(json.dumps(dict(action_bytes=len(bytes.fromhex(regions[0]['bytes'])),singleton_bytes=len(bytes.fromhex(regions[1]['bytes'])),direct_callers=len(callers))))
