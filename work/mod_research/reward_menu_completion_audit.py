"""Explicit archived source for reward success-tail -> untagged pop consumption."""
import hashlib
from pathlib import Path
import struct
import sys

IMAGE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
RANGES=((0x67A99C,0x67A9AE),(0x10A60,0x10AEA),(0x50A7BA,0x50B3B6),
        (0x667B10,0x667B98),(0x60B000,0x60B065),(0x6115A0,0x6115D4),(0x665CD0,0x665CD6))
POINTS=(
    ('queue_publish_before',0x10ADC,5,'RCX=2*old queue count, RAX=queue storage; xmm0 is {1,0}'),
    ('queue_publish_after',0x10AE4,4,'RDI=manager; [manager+30] has been incremented; menu identity absent'),
    ('pop_select_current_top',0x50A9D2,5,'R12=current formal top, R15=manager, RDI=copied 16-byte request'),
    ('pop_finalize_before',0x50B1B5,3,'RCX=R12=current top; vtable+10; thread and bound menu must agree'),
    ('pop_count_decrement_after',0x50B1FF,5,'R15 manager; layout may already be freed; never dereference freed UI'),
    ('pop_resume_return',0x50B21F,4,'formal stack count decremented; same underlying User expected'),
    ('pop_allocator_return',0x50B26A,5,'R12 may already be freed; use previously retained identity only'),
)


def inspect(root):
    root=Path(root).resolve();path=root/'game-runtime-image.bin';image=path.read_bytes()
    if hashlib.sha256(image).hexdigest()!=IMAGE_SHA:raise ValueError('Unsupported explicit archive')
    sys.path.insert(0,str(root/'python_deps'))
    import capstone
    dis=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
    ops={i.address:(i.mnemonic,i.op_str) for a,b in RANGES for i in dis.disasm(image[a:b],a)}
    checks=[]
    expected={0x67A99C:('call','0xf690'),0x67A9A9:('jmp','0x10a60'),
        0x10A69:('mov','dword ptr [rsp + 0x30], 1'),0x10A73:('mov','qword ptr [rsp + 0x38], rcx'),
        0x10ADC:('movups','xmmword ptr [rax + rcx*8], xmm0'),0x10AE0:('inc','qword ptr [rdi + 0x30]'),
        0x50A986:('mov','qword ptr [r15 + 0x40], rbx'),0x50A98A:('mov','qword ptr [r15 + 0x30], rbx'),
        0x50A9C8:('mov','r12, qword ptr [rax + rcx*8 - 8]'),0x50A9E4:('je','0x50b18a'),
        0x50B1A5:('call','qword ptr [rax + 0x20]'),0x50B1B5:('call','qword ptr [rax + 0x10]'),
        0x50B1FB:('mov','qword ptr [r15 + 0x10], rax'),0x50B21C:('call','qword ptr [rax + 0x18]'),
        0x50B25C:('call','qword ptr [rax]'),0x50B267:('call','qword ptr [rax + 0x58]'),
        0x667B5C:('mov','qword ptr [rdi + 0x478], 0'),0x60B02D:('call','0x1fed80'),
        0x6115AF:('call','0x60b000'),0x665CD5:('ret','')}
    for a,op in expected.items():
        if ops.get(a)!=op:raise AssertionError(hex(a))
        checks.append(dict(case='native_instruction_'+format(a,'x'),passed=True,kind='archive_static'))
    origin=struct.unpack_from('<Q',image,0x1331078+5*8)[0]-0x67A930
    for off,rva in ((0,0x6115A0),(0x10,0x667B10),(0x18,0x665CD0),(0x20,0x665CD0)):
        if struct.unpack_from('<Q',image,0x1331078+off)[0]!=origin+rva:raise AssertionError('reward virtual map')
        checks.append(dict(case='virtual_slot_'+str(off),passed=True,kind='archive_static'))
    sections=[image[a:b] for a,b in RANGES]
    result=dict(schema='san14.reward-menu-completion-source.v1',checks=checks,
        image_sha256=IMAGE_SHA,pdata_sha256=hashlib.sha256((root/'runtime-pdata.bin').read_bytes()).hexdigest(),
        sections=[dict(rva=a,size=b-a,sha256=hashlib.sha256(raw).hexdigest()) for (a,b),raw in zip(RANGES,sections)],
        points=[dict(event=n,rva=a,bytes=image[a:a+size].hex(),fields=fields) for n,a,size,fields in POINTS],
        queue_carries_menu_identity=False,consumer_selects_current_top=True,production_permit=False,
        scope='Success continuation and native type1 dispatch, not an authority-approved close implementation')
    return result,b''.join(sections),path
