"""Fixed archive-only keyboard query audit; no device/game/process helpers."""
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'python_deps'))
import capstone

IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
image = (HERE/'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest() == IMAGE_SHA
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
cs.detail = True

def dis(at, size):
    return [{'rva': hex(i.address), 'bytes': i.bytes.hex(), 'instruction': i.mnemonic+' '+i.op_str}
            for i in cs.disasm(image[at:at+size], at)]

def exact(at, text):
    row = dis(at, 15)[0]
    assert row['instruction'] == text, row
    return row

specs = [('Release', 0x3A2CB0, 0x3A2CC8), ('Press', 0x3A2CD0, 0x3A2CE8),
         ('Repeat', 0x3A2CF0, 0x3A2D13), ('Modifier11', 0x3A2D60, 0x3A2D71),
         ('ModifierMasked', 0x3A2D80, 0x3A2DA0), ('Modifier22', 0x3A2DA0, 0x3A2DB1)]
leaves = []
header = '#pragma once\n#include <array>\n#include <cstdint>\nnamespace checkpoint_native_input_keyboard {\n'
for name, begin, end in specs:
    code = image[begin:end]
    ins = list(cs.disasm(code, begin))
    assert sum(i.size for i in ins) == len(code) and ins[-1].mnemonic == 'ret'
    for i in ins:
        assert i.mnemonic not in ('call', 'push', 'pop')
        for op in i.operands:
            if op.type == capstone.x86.X86_OP_MEM:
                assert op.mem.base != capstone.x86.X86_REG_RIP
                assert not (op.access & capstone.CS_AC_WRITE), (name, i.mnemonic, i.op_str)
        if i.group(capstone.CS_GRP_JUMP):
            assert len(i.operands) == 1 and i.operands[0].type == capstone.x86.X86_OP_IMM
            assert begin <= i.operands[0].imm < end
    leaves.append(dict(name=name, rva=hex(begin), end_exclusive=hex(end), bytes=code.hex(),
                       sha256=hashlib.sha256(code).hexdigest(), instructions=dis(begin,len(code)),
                       no_calls_no_writes_no_rip=True))
    header += f'inline constexpr std::array<std::uint8_t, {len(code)}> k{name} = {{'+','.join(f'0x{x:02x}' for x in code)+'};\n'
header += '}\n'

# Verify actual CALL instructions by disassembling their enclosing .pdata
# function from its native entry; a byte E8 occurrence alone is not a call.
pdata = (HERE/'runtime-pdata.bin').read_bytes()
assert hashlib.sha256(pdata).hexdigest() == '74e018f15ec009af5fd0e0d91ce981b82d7d970150b3dce5861f17d11eea2e9f'
assert len(pdata) % 12 == 0
functions = [struct.unpack_from('<III',pdata,p) for p in range(0,len(pdata),12)
             if struct.unpack_from('<I',pdata,p)[0]]
starts = [f[0] for f in functions]
assert starts == sorted(starts)
targets = {x[1] for x in specs}
callers = []
at = -1
while True:
    at = image.find(b'\xe8',at+1)
    if at < 0 or at+5 > len(image): break
    target = at+5+struct.unpack_from('<i',image,at+1)[0]
    if target not in targets: continue
    index = bisect_right(starts,at)-1
    if index < 0: continue
    begin,end,_ = functions[index]
    if not begin <= at < end: continue
    ins = list(cs.disasm(image[begin:end],begin))
    for j,i in enumerate(ins):
        if i.address == at and i.mnemonic == 'call' and i.op_str == hex(target):
            callers.append(dict(target=hex(target), caller=hex(at), function=hex(begin),
                context=[dict(rva=hex(x.address),instruction=x.mnemonic+' '+x.op_str,bytes=x.bytes.hex())
                         for x in ins[max(0,j-5):j+3]]))
            break

anchors = [exact(0x3F9EF2,'call 0x292220'),exact(0x3F9EF7,'mov rcx, rax'),
    exact(0x3F9EFA,'call 0x3a2da0'),exact(0x3F9EFF,'test al, al'),
    exact(0x3A3923,'test dword ptr [rax + 0x50], r8d'),
    exact(0x3A2E0B,'cmp eax, 0xff'),exact(0x3A2E12,'cmp byte ptr [rax + r9 + 0x158], 0'),
    exact(0x3A2E4F,'test dword ptr [r9 + 0x50], edx')]
assert any(x['caller']=='0x3f9efa' for x in callers)
report = dict(schema='san14.native-input-keyboard-audit.v1', image_sha256=IMAGE_SHA,
    pdata_sha256=hashlib.sha256(pdata).hexdigest(),
    leaves=leaves, callers=callers, anchors=anchors, game_accessed=False,
    input_hold_proven=False, native_installer_present=False,
    abi='RCX normal cache; EDX key/mask when used; R8D repeat policy/all-bits flag when used. All six return AL. Upper RAX is unspecified semantic data, captured and passed through opaquely by the bridge.',
    supported_queries='Fixed modifier 11/22; generic masks 11/22/44/88 with flag 0 or 1; key edges/repeat codes 1..FF and the four observed repeat codes 101..104.',
    uncovered=['3A3810 and 3A2DC0 contain inline raw keyboard reads, not calls to these leaves',
        'Key index zero/no-event and unknown masks/special codes intentionally refused',
        'Earlier pending menu latch, providers/messages/other direct reads, physical release, native fence and installation unproved'])
(HERE/'checkpoint_native_input_keyboard_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(HERE/'checkpoint_native_input_keyboard_archived.h').write_text(header,encoding='utf-8')
print(json.dumps(dict(leaves=len(leaves),direct_callers=len(callers),anchors=len(anchors))))
