"""Relocate the full group getter and its audited transitive query code."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'python_deps'))
import capstone
BLOCKS = [
    ('district', 0x209C80, 0x209CFD, 0x000),
    ('begin', 0x2029D0, 0x202A7C, 0x100),
    ('end', 0x202C00, 0x202C7C, 0x200),
    ('member', 0x2F63E0, 0x2F6419, 0x300),
    ('excluded', 0x210D40, 0x210E85, 0x400),
    ('valid', 0x2F2BB0, 0x2F2BD4, 0x600),
    ('person_valid', 0x2119F0, 0x211A2D, 0x700),
    ('army_valid', 0x211420, 0x211448, 0x800),
    ('army_force', 0x20A810, 0x20A89B, 0x900),
    ('district_valid', 0x211610, 0x211659, 0xA00),
]


def main():
    image = (ROOT / 'game-runtime-image.bin').read_bytes()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    internal = {a: off for _, a, _, off in BLOCKS}
    relocations, metadata = [], []
    header = '// Copied native query bodies. No game process access and no query stubs.\n'
    for name, a, z, off in BLOCKS:
        code = image[a:z]
        insns = list(md.disasm(code, a))
        assert sum(ins.size for ins in insns) == len(code)
        boundaries = {ins.address for ins in insns}
        refs = []
        for ins in insns:
            if ins.mnemonic == 'call' or ins.mnemonic.startswith('j'):
                operand = ins.operands[0]
                if operand.type == capstone.x86.X86_OP_IMM:
                    target = operand.imm
                    if a <= target < z:
                        assert target in boundaries
                    else:
                        assert ins.mnemonic in ('call', 'jmp') and ins.size == 5 and target in internal, (name, hex(target))
                        relocations.append((off + ins.address - a + 1, off + ins.address - a + 5, internal[target]))
                        refs.append(hex(target))
                else:
                    assert ins.mnemonic == 'call' and operand.mem.disp in (8, 0x18)
                    refs.append('validated iterator/validity virtual call')
            for operand in ins.operands:
                if operand.type == capstone.x86.X86_OP_MEM and operand.mem.base == capstone.x86.X86_REG_RIP:
                    target = ins.address + ins.size + operand.mem.disp
                    if target == 0x1FCA1E0:
                        dest = 0x2000
                    elif target == 0x129FC00:
                        dest = 0x2100
                    elif 0x201D3A0 <= target < 0x201D3F0:
                        dest = 0x2200 + target - 0x201D3A0
                    elif 0x1FC9760 <= target < 0x1FC97B0:
                        dest = 0x2280 + target - 0x1FC9760
                    else:
                        raise ValueError(f'Unknown native data reference {target:#x}')
                    assert ins.disp_size == 4
                    relocations.append((off + ins.address - a + ins.disp_offset, off + ins.address - a + ins.size, dest))
        header += f'static const unsigned char code_{name}[]={{' + ','.join(map(str, code)) + '};\n'
        metadata.append({'name': name, 'rva': hex(a), 'end': hex(z), 'sha256': hashlib.sha256(code).hexdigest(), 'references': refs})
    header += 'struct NativeBlock {const unsigned char* bytes; unsigned size,offset;};\nstatic const NativeBlock nativeBlocks[]={'
    header += ','.join('{code_%s,sizeof code_%s,%d}' % (n,n,o) for n,_,_,o in BLOCKS) + '};\n'
    header += 'struct Patch {unsigned at,next,target;};\nstatic const Patch patches[]={' + ','.join('{%d,%d,%d}' % p for p in relocations) + '};\n'
    (ROOT / 'troops_fixture_code.h').write_text(header, encoding='utf-8')
    (ROOT / 'troops-fixture-source.json').write_text(json.dumps({'blocks': metadata, 'relocations': len(relocations),
        'query_stubs': 0, 'game_process_access': False, 'native_queries_run_in': 'isolated fixture process'}, indent=2), encoding='utf-8')
    print(json.dumps({'blocks': len(BLOCKS), 'relocations': len(relocations), 'query_stubs': 0}))


if __name__ == '__main__':
    main()
