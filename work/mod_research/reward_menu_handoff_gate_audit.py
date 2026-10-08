"""Explicit private archive only: bounded menu call/teardown source evidence."""
import hashlib
from pathlib import Path
import struct
import sys

ARCHIVE_SHA256 = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
GAME_SHA256 = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
RANGES = ((0x67A930,0x67A9C1),(0x667B10,0x667B98),(0x60B000,0x60B065))


def inspect(archive_root):
    root = Path(archive_root).resolve()
    image_path = root / 'game-runtime-image.bin'
    data = image_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != ARCHIVE_SHA256:
        raise ValueError('Unsupported explicit offline archive')
    sys.path.insert(0,str(root / 'python_deps'))
    import capstone
    decoder = capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
    ranges = RANGES + ((0x674980,0x674A20),(0x626050,0x6264B2),(0x665CD0,0x665CD6))
    instructions = {i.address:(i.mnemonic,i.op_str) for a,b in ranges for i in decoder.disasm(data[a:b],a)}
    checks=[]
    def check(name,condition):
        checks.append(dict(case=name,passed=bool(condition),kind='bounded_archive_static'))
        if not condition:
            raise AssertionError(name)
    base=struct.unpack_from('<Q',data,0x1331078+5*8)[0]-0x67A930
    for slot,rva in ((0,0x6115A0),(1,0x674980),(2,0x667B10),(3,0x665CD0),(4,0x665CD0),(5,0x67A930)):
        check('reward_vtable_slot_'+str(slot),struct.unpack_from('<Q',data,0x1331078+slot*8)[0]==base+rva)
    expected = {
        0x67A993:('call','0x626050'),0x67A998:('test','eax, eax'),0x67A99A:('je','0x67a9bb'),
        0x67A9A9:('jmp','0x10a60'),0x67A9B6:('jmp','0x68f760'),
        0x626275:('call','0x1d6da0'),0x62627F:('call','0x2f2bb0'),0x626284:('test','eax, eax'),
        0x6749B8:('mov','qword ptr [rbx + 0x478], rcx'),
        0x667B20:('mov','rcx, qword ptr [rcx + 0x478]'),0x667B27:('mov','eax, dword ptr [rcx + 0x168]'),
        0x667B2D:('mov','dword ptr [rdi + 8], eax'),0x667B33:('call','qword ptr [rax + 0x40]'),
        0x667B43:('call','qword ptr [rax + 0x28]'),0x667B55:('mov','edx, 1'),
        0x667B5A:('call','qword ptr [rax]'),0x667B5C:('mov','qword ptr [rdi + 0x478], 0'),
        0x667B84:('call','qword ptr [rax + 0x10]'),0x667B91:('ret',''),
        0x60B01C:('add','rcx, 0x480'),0x60B02D:('call','0x1fed80'),
        0x665CD0:('mov','eax, 1'),0x665CD5:('ret','')}
    for address,wanted in expected.items():
        check('instruction_'+format(address,'x'),instructions[address]==wanted)
    pdata=(root/'runtime-pdata.bin').read_bytes()
    functions={(a,b) for a,b,_ in struct.iter_unpack('<III',pdata)}
    for a,b in RANGES:
        check('bounded_function_'+format(a,'x'),(a,b) in functions)
    anchors=[]
    for name,address,length in (('confirm_call',0x67A993,5),('confirm_return',0x67A998,4),
                               ('layout_create_publish',0x6749B8,7),('layout_release',0x667B5A,2),
                               ('layout_null_publish',0x667B5C,11),('selection_destruct_call',0x60B02D,5)):
        anchors.append(dict(name=name,rva=address,bytes=data[address:address+length].hex()))
    sections=[data[a:b] for a,b in RANGES]
    result=dict(schema='san14.reward-menu-handoff-gate-audit.v1',checks=checks,anchors=anchors,
        archive_sha256=digest,pdata_sha256=hashlib.sha256(pdata).hexdigest(),game_sha256=GAME_SHA256,
        sections=[dict(rva=a,size=b-a,sha256=hashlib.sha256(code).hexdigest()) for (a,b),code in zip(RANGES,sections)],
        lifetime_evidence='Reward vtable slot 2 destroys its layout then publishes null; base destructor releases selection list.',
        cancellation_mapping='Unresolved. No observed input or dispatcher path to this lifecycle method.',
        full_menu_lifetime_lease=False,production_permit=False,game_access=False)
    return result,b''.join(sections),image_path
