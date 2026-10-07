"""Relocate audited native outer AI wrappers into an isolated local fixture."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'python_deps'))
import capstone
image = (ROOT / 'game-runtime-image.bin').read_bytes()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
md.detail = True
blocks = [
    ('army', 0xc6580, 0xc65e3, 0x000),
    ('district', 0xc65f0, 0xc6653, 0x100),
    ('force', 0xc6660, 0xc669c, 0x200),
    ('group', 0xc66a0, 0xc6703, 0x300),
    ('player_main', 0x2f21a0, 0x2f21d2, 0x400),
    ('player_force', 0x2f21e0, 0x2f220a, 0x500),
    ('is_player', 0x2110b0, 0x211109, 0x600),
    ('option_bit', 0x2f5ae0, 0x2f5afb, 0x700),
    ('district_id', 0x20b580, 0x20b5aa, 0x800),
    ('army_district', 0x209ab0, 0x209b03, 0x900),
]
internal = {a: offset for _, a, _, offset in blocks}
stubs = {0x20c110: 0x1000, 0x2f2bb0: 0x1020, 0x209c80: 0x1040,
         0xa8cf0: 0x1060, 0xa8e50: 0x1080, 0xa9160: 0x10a0, 0xa9220: 0x10c0}
patches, meta = [], []
header = '// Generated from captured native bytes. Local fixture only.\n'
for name, a, z, offset in blocks:
    code = image[a:z]
    instructions = list(md.disasm(code, a))
    assert sum(i.size for i in instructions) == len(code)
    boundaries = {i.address for i in instructions}
    refs = []
    for ins in instructions:
        if ins.mnemonic == 'call' or ins.mnemonic.startswith('j'):
            op = ins.operands[0]
            if op.type == capstone.x86.X86_OP_IMM:
                target = op.imm
                if a <= target < z:
                    assert target in boundaries
                else:
                    assert ins.mnemonic in ('call', 'jmp') and ins.size == 5
                    assert target in internal or target in stubs, (name, hex(target))
                    dest = internal[target] if target in internal else stubs[target]
                    patches.append((offset + ins.address - a + 1, offset + ins.address - a + 5, dest))
                    refs.append({'at': hex(ins.address), 'target': hex(target), 'stub': target in stubs})
            else:
                assert name == 'is_player' and ins.mnemonic == 'call' and op.mem.disp == 0x60
                refs.append({'at': hex(ins.address), 'target': 'stub force-id virtual method'})
        for op in ins.operands:
            if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                target = ins.address + ins.size + op.mem.disp
                assert target == 0x1fca1e0 and ins.disp_size == 4
                patches.append((offset + ins.address - a + ins.disp_offset, offset + ins.address - a + ins.size, 0x2000))
    header += 'static const unsigned char code_' + name + '[]={' + ','.join(map(str, code)) + '};\n'
    meta.append({'name': name, 'rva': hex(a), 'end': hex(z), 'local_offset': offset,
                 'sha256': hashlib.sha256(code).hexdigest(), 'references': refs})
header += 'struct NativeBlock {const unsigned char* bytes; unsigned size,offset;};\n'
header += 'static const NativeBlock nativeBlocks[]={' + ','.join(
    '{code_%s,sizeof code_%s,%d}' % (name, name, offset) for name, _, _, offset in blocks) + '};\n'
header += 'struct Patch {unsigned at,next,target;};\nstatic const Patch patches[]={' + ','.join(
    '{%d,%d,%d}' % p for p in patches) + '};\n'
(ROOT / 'human_ai_fixture_code.h').write_text(header, encoding='utf-8')
(ROOT / 'human-ai-fixture-source.json').write_text(json.dumps({
    'native_blocks': meta, 'stubs': {hex(k): hex(v) for k, v in stubs.items()},
    'game_access': False,
    'scope': 'Native outer dispatch wrappers and six native accessors; AI bodies, main-district list lookup, person validity and group lookup are controlled stubs. No simulation or injection.'
}, indent=2), encoding='utf-8')
print(json.dumps({'native_blocks': len(blocks), 'relocations': len(patches), 'game_access': False}))
