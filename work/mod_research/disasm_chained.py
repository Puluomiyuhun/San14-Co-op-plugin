"""Offline disassembly grouped by x64 chained unwind metadata.

Ordinary .pdata entries may describe only a short fragment. This groups entries
by their primary unwind record, without treating adjacent functions as one.
It does not resolve indirect calls or certify command execution safety.
"""
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path
import json
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'python_deps'))
import capstone

image = (ROOT / 'game-runtime-image.bin').read_bytes()
pdata = (ROOT / 'runtime-pdata.bin').read_bytes()
entries = sorted(set(entry for entry in struct.iter_unpack('<III', pdata)
                     if 0x1000 <= entry[0] < entry[1] <= len(image)))
starts = [entry[0] for entry in entries]


def triple(offset):
    if not 0 <= offset <= len(image) - 12:
        raise ValueError('Unwind record is outside the captured image')
    return struct.unpack_from('<III', image, offset)


@lru_cache(None)
def primary(entry, path=()):
    if entry in path or len(path) >= 32:
        raise ValueError('Cyclic or excessive chained unwind metadata')
    a, z, unwind = entry
    if not 0x1000 <= a < z <= len(image):
        raise ValueError('Invalid runtime function bounds')
    if unwind & 1:
        return primary(triple(unwind & ~1), path + (entry,))
    if not 0 <= unwind <= len(image) - 4:
        raise ValueError('Invalid unwind info pointer')
    version_flags, _, count, _ = struct.unpack_from('<4B', image, unwind)
    version, flags = version_flags & 7, version_flags >> 3
    if version not in (1, 2):
        raise ValueError(f'Unsupported unwind version {version}')
    if flags & 4:
        if flags & 3:
            raise ValueError('Conflicting unwind flags')
        tail = unwind + 4 + ((count + 1) & ~1) * 2
        return primary(triple(tail), path + (entry,))
    return entry


groups = {}
failures = []
for entry in entries:
    try:
        groups.setdefault(primary(entry), []).append(entry)
    except ValueError as error:
        failures.append({'entry': [hex(value) for value in entry], 'error': str(error)})

decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
decoder.detail = True
for argument in sys.argv[1:]:
    address = int(argument, 0)
    index = bisect_right(starts, address) - 1
    if index < 0 or not address < entries[index][1]:
        raise ValueError(f'No unwind fragment contains {address:#x}')
    root = primary(entries[index])
    fragments = sorted(set(groups[root] + [root]))
    lines = [f'Primary {root[0]:#x}; target {address:#x}; fragments {len(fragments)}',
             'Grouped by unwind metadata; indirect control flow remains unresolved.',
             'Linear decoding can include embedded data/jump tables; inspect control flow before using a reference.']
    references = []
    count = 0
    for a, z, _ in fragments:
        lines.append(f'\nFragment {a:#x}..{z:#x}')
        end = a
        for instruction in decoder.disasm(image[a:z], a):
            if instruction.address != end:
                raise ValueError('Disassembly skipped bytes')
            end += instruction.size
            count += 1
            lines.append(f'{instruction.address:#x}: {instruction.mnemonic} {instruction.op_str}')
            if (instruction.mnemonic in ('call', 'jmp') and len(instruction.operands) == 1
                    and instruction.operands[0].type == capstone.x86.X86_OP_IMM):
                references.append({'at_rva': hex(instruction.address),
                                   'operation': instruction.mnemonic,
                                   'target_rva': hex(instruction.operands[0].imm)})
        if end != z:
            raise ValueError(f'Undecoded bytes at {end:#x}..{z:#x}')
    destination = ROOT / f'full-{root[0]:x}.txt'
    destination.write_text('\n'.join(lines), encoding='utf-8')
    (ROOT / f'full-{root[0]:x}.json').write_text(json.dumps({
        'primary_rva': hex(root[0]), 'fragments': [[hex(a), hex(z)] for a, z, _ in fragments],
        'instructions': count, 'direct_references': references,
        'unresolved_unwind_entries_in_image': failures,
        'scope': 'Static unwind group; linear decoding may include embedded data, not a complete semantic call graph',
    }, indent=2), encoding='utf-8')
    print(destination.name, 'fragments', len(fragments), 'instructions', count,
          'unresolved-image-entries', len(failures))
