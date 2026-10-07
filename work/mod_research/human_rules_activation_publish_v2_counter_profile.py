"""Build-time fixed-binary RPM profile; never attached to any process.

Resolve only Snapshot's actual InterlockedCompareExchange64 load immediately
stored to the named Report::active offset. Emit exact machine bytes and target
RVA, not a runtime signature scanner. Whole DLL SHA is independently pinned.
"""
from pathlib import Path
import hashlib
import json
import sys
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P/'python_deps'))
import capstone as cs
import pefile


def generate(dll, header):
    dll, header = Path(dll), Path(header)
    pe = pefile.PE(str(dll))
    data = pe.get_memory_mapped_image()
    exports = {e.name.decode(): e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
    engine = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_64); engine.detail = True
    rows = []
    for export, report_offset in [('HumanAiRuntimeSnapshot', 136), ('HumanEconomySnapshot', 48)]:
        start = exports[export]
        first = list(engine.disasm(data[start:start+16], start))
        # Frozen AI export's null-check thunk branches to Snapshot implementation.
        if export == 'HumanAiRuntimeSnapshot':
            branches = [i for i in first if i.mnemonic == 'jne']
            assert len(branches) == 1
            start = branches[0].operands[0].imm
        instructions = []
        for i in engine.disasm(data[start:start+1024], start):
            instructions.append(i)
            if i.mnemonic == 'ret': break
        found = []
        for i, nxt in zip(instructions, instructions[1:]):
            if i.mnemonic != 'lock cmpxchg' or len(i.operands) != 2: continue
            operand = i.operands[0]
            if operand.type != cs.CS_OP_MEM or operand.mem.base != cs.x86.X86_REG_RIP or operand.size != 8: continue
            if nxt.mnemonic != 'mov' or len(nxt.operands) != 2: continue
            dst, src = nxt.operands
            if dst.type != cs.CS_OP_MEM or dst.mem.base != cs.x86.X86_REG_RDX or dst.mem.disp != report_offset or src.type != cs.CS_OP_REG or src.reg != cs.x86.X86_REG_RAX: continue
            found.append({'export': export, 'active_report_offset': report_offset, 'instruction_rva': i.address,
                          'value_rva': i.address+i.size+operand.mem.disp,
                          'bytes': (i.bytes+nxt.bytes).hex()})
        assert len(found) == 1, (export, found)
        rows.extend(found)
    text = '#pragma once\nstruct ActiveCounterAnchor {std::uint64_t instruction_rva,value_rva;unsigned size;unsigned char bytes[16];};\nconstexpr ActiveCounterAnchor ActiveCounters[]={\n'
    for r in rows:
        raw = bytes.fromhex(r['bytes']); assert len(raw) <= 16
        text += '{'+f"0x{r['instruction_rva']:x},0x{r['value_rva']:x},{len(raw)},"+'{'+','.join(hex(x) for x in raw)+'}},\n'
    text += '};\n'
    header.write_text(text)
    proof = {'dll_sha256': hashlib.sha256(dll.read_bytes()).hexdigest(), 'active_counters': rows}
    header.with_suffix('.json').write_text(json.dumps(proof, indent=2)+'\n')
    return proof


if __name__ == '__main__': generate(*sys.argv[1:])
