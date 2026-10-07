"""Offline index of candidate domestic command routes; never opens the game.

Names suggest feature groups. A static call is not proof of legal arguments,
safe invocation, complete state effects, or working multiplayer support.
"""
from bisect import bisect_right
from pathlib import Path
import json
import re
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'python_deps'))
import capstone

image = (ROOT / 'game-runtime-image.bin').read_bytes()
pdata = (ROOT / 'runtime-pdata.bin').read_bytes()
fragments = sorted({(a, z) for a, z, _ in struct.iter_unpack('<III', pdata[:len(pdata)//12*12])
                    if 0x1000 <= a < z <= len(image)})
starts = [a for a, _ in fragments]
decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
decoder.detail = True
decoded = {}


def fragment_at(address):
    index = bisect_right(starts, address) - 1
    if index >= 0 and address < fragments[index][1]:
        return fragments[index]
    return None


def verified_branch(address, target):
    fragment = fragment_at(address)
    if fragment is None:
        return None
    if fragment not in decoded:
        a, z = fragment
        decoded[fragment] = {ins.address: ins for ins in decoder.disasm(image[a:z], a)}
    instruction = decoded[fragment].get(address)
    if (instruction is None or instruction.mnemonic not in ('call', 'jmp')
            or len(instruction.operands) != 1
            or instruction.operands[0].type != capstone.x86.X86_OP_IMM
            or instruction.operands[0].imm != target):
        return None
    return {'at_rva': hex(address), 'operation': instruction.mnemonic,
            'unwind_fragment': [hex(value) for value in fragment]}


# These candidates come from actual direct calls inside RTTI-identified AI
# command node methods. They have NOT been called by this research tool.
routes = [
    ('施政候选', 'CStrategyGovernmentState', 'CCommandExecutionGovernmentNode', 0x29730, [0x1D3500]),
    ('赏赐候选', 'CStrategyRewardState', 'CCommandExecutionPrizeNode', 0x2A440, [0x1D6DA0]),
    ('交易候选', 'CStrategyMerchantState', 'CCommandExecutionMerchantNode', 0x299F0, [0x1D5650]),
    ('移动候选', 'CStrategyMoveState', 'CCommandExecutionMoveNode', 0x2A280, [0x1D58A0]),
    ('登用候选', 'CStrategyEmployState', 'CCommandExecutionEmployNode', 0x29670, [0x1D27F0]),
    ('搜索候选', 'CStrategySearchState', 'CCommandExecutionSearchNode', 0x4C990, [0x1D48C0, 0x1D7060]),
]
targets = {target for *_, candidates in routes for target in candidates}
references = {target: [] for target in targets}
for hit in re.finditer(rb'[\xe8\xe9]', image[0x1000:0x123BAD0]):
    address = hit.start() + 0x1000
    target = address + 5 + struct.unpack_from('<i', image, address + 1)[0]
    if target in references:
        reference = verified_branch(address, target)
        if reference:
            references[target].append(reference)

types = {}
for name in ('domestic-types.json', 'domestic-extra-types.json'):
    types.update(json.loads((ROOT / name).read_text(encoding='utf-8')))
rows = []
for label, ui, ai, method, targets_for_route in routes:
    if method not in types[ai]['methods'][0]:
        raise RuntimeError(f'Candidate method does not belong to {ai}')
    for target in targets_for_route:
        if not any(int(row['unwind_fragment'][0], 16) == method for row in references[target]):
            raise RuntimeError(f'Missing verified originating call from {ai} to {target:#x}')
    rows.append({'label_inferred_from_class_names': label,
                 'ui_class': ui, 'ai_class': ai,
                 'ai_virtual_method_rva': hex(method),
                 'candidate_native_targets': [
                     {'rva': hex(target), 'verified_direct_references': references[target]}
                     for target in targets_for_route],
                 'parameters_verified': False, 'executed_in_game': False})

report = {
    'mode': 'offline-static-analysis', 'opened_game_process': False,
    'ui_input_performed': False, 'game_memory_modified': False,
    'indexed_class_count': len(types),
    'class_index': {name: {'type_descriptor_rva': hex(row['type_descriptor']),
                          'vtable_rvas': [hex(value) for value in row['tables']],
                          'reference_candidates': [hex(value) for value in row['xrefs']]}
                    for name, row in types.items()},
    'routes': rows,
    'limitations': [
        'Labels are inferred from names; they are not a complete menu-to-command mapping.',
        'Cross-references are instruction-aligned direct calls/jumps within unwind fragments.',
        'Unwind fragments may omit other parts of a function; indirect calls are not indexed.',
        'No candidate is authorized as an executable network command by this report.',
        'No domestic feature has passed a real game execution or synchronization test yet.',
    ],
}
(ROOT / 'domestic-route-survey.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({'indexed_classes': len(types), 'routes': [
    {'label': row['label_inferred_from_class_names'],
     'targets': [{'rva': target['rva'], 'reference_count': len(target['verified_direct_references'])}
                 for target in row['candidate_native_targets']]}
    for row in rows], 'game_input_or_write': False}, ensure_ascii=False, indent=2))
