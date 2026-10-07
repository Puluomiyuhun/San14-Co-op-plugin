"""Offline evidence: proposal generation and scoped turn-end durability RNG."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
sys.path.insert(0, str(ROOT / 'python_deps'))
sys.path.insert(0, str(OUT))
import capstone
from proposal_state_reader import HANDLERS


def audit():
    image = (ROOT / 'game-runtime-image.bin').read_bytes()
    q = lambda a: struct.unpack_from('<Q', image, a)[0]
    base = q(0x12CC4A8 + 0x28) - 0x3F9B00

    def rtti(vtable):
        locator = q(vtable - 8) - base
        signature, _, _, descriptor, _, self_rva = struct.unpack_from('<6I', image, locator)
        assert signature == 1 and self_rva == locator
        end = image.index(0, descriptor + 16)
        return image[descriptor + 16:end].decode('ascii')

    types = {hex(v): rtti(v) for v in (0x12C9048, 0x123F448, 0x129FA98, 0x12A08C8,
                                      0x129FD10, 0x129FDF0)}
    assert types['0x12c9048'] == '.?AVCProposalFunc@@'
    assert types['0x129fa98'] == '.?AVCDistrictPersonIterator@@'
    handlers = []
    for kind, name in enumerate(HANDLERS):
        obj = q(0x1904420 + kind * 8) - base
        vt = q(obj) - base
        actual = rtti(vt)
        assert actual == f'.?AVCProposalHandler_{name}@@'
        handlers.append({'type_id': kind, 'name': name, 'rtti': actual,
                         'object_rva': hex(obj), 'vtable_rva': hex(vt),
                         'method_rvas': {hex(n): hex(q(vt + n) - base)
                                         for n in (0x18, 0x20, 0x28, 0x48, 0x50, 0x68)},
                         'parameter_index_fields_08_1c': list(struct.unpack_from('<5I', image, obj + 8))
                         if kind else None})
    stages = [{'stage_index': i, 'predicate_rva': hex(q(0x1904730 + i * 8) - base),
               'action_rva': hex(q(0x1904520 + i * 8) - base)} for i in range(66)]
    assert stages[1]['action_rva'] == '0x3d9790' and stages[39]['action_rva'] == '0x3dd840'
    wanted = {
        0x3f7353: 'call 0x3d1420', 0x3d142d: 'call 0x3cc530',
        0x3d1443: 'call 0x3cb950', 0x3cb9e8: 'call 0x3d1450',
        0x3d1480: 'call 0x2f21a0', 0x2f21a0: 'movzx eax, byte ptr [rcx + 0x3a]',
        0x2f21b2: 'mov rcx, qword ptr [rax + rcx*8 + 0xdca0]',
        0x2f21ba: 'jmp 0x20c110', 0x3d14a3: 'call 0x211f80',
        0x211fcb: 'call 0x211d30', 0x211d55: 'sub rcx, qword ptr [r9 + 0xde40]',
        0x3cc0b7: 'call 0x3aa7c0', 0x3cc26e: 'call 0x3c68b0',
        0x3cc310: 'call 0x3d0000', 0x3d0497: 'call qword ptr [rax + 0x18]',
        0x3c5764: 'mov dword ptr [r14 + 0x3c], ebx',
        0x3cc548: 'lea rsi, [rax + 0x7ef08]', 0x3cc54f: 'add rax, 0x7f000',
        0x206c0b: 'mov word ptr [rcx + 0x10], ax',
        0x206c0f: 'mov byte ptr [rcx + 0x12], al',
        0x206c12: 'mov word ptr [rcx + 0x14], ax',
        0x3dbf8f: 'cmp edi, 0x42', 0x3dbfd2: 'call rsi',
        0x3d979e: 'mov dword ptr [rbx + 0x14], eax',
        0x3d97d0: 'call 0x3aa3e0', 0x3d4f6d: 'mov ecx, dword ptr [rcx + 0x14]',
        0x3d4f72: 'je 0x3d4f7a', 0x3d4f74: 'call 0x3aa3e0',
        0x3f5f7e: 'mov rbx, qword ptr [rdi + 0x470]', 0x3f5f8d: 'call 0x3d4f60',
        0x3dd844: 'call 0x2ce910', 0x2ceb29: 'call 0x2b4fa0',
        0x2b50d2: 'call 0x285550', 0x2855dc: 'call 0x3aa7c0',
        0x2b5090: 'mov rbp, qword ptr [rax + rcx*8 + 0x6d808]',
        0x2b50f6: 'call 0x1d8230',
        0x3b9756: 'call 0x285550', 0x3b9760: 'call 0x20a330',
        0x3b97a7: 'call 0x21d430', 0x21d497: 'call 0x1d8230',
    }
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    anchors = []
    for address, expected in wanted.items():
        ins = next(md.disasm(image[address:address + 15], address))
        actual = f'{ins.mnemonic} {ins.op_str}'
        assert actual == expected, (hex(address), actual, expected)
        anchors.append({'rva': hex(address), 'instruction': actual, 'bytes': ins.bytes.hex()})
    trace = ROOT / 'lockstep-traces' / 'rng-pairs-live-n'
    analysis = json.loads((trace / 'paired-analysis.json').read_text(encoding='utf-8'))
    proposals, endurance = [], []
    direct_counts = Counter()
    for call in analysis['calls']:
        frames = call['unwind']['frames']
        direct = frames[1]['pc_rva'] if len(frames) > 1 else None
        if direct in ('0x3cc0bc', '0x3c68e7', '0x3c685a', '0x3c6980'):
            assert any(f['pc_rva'] == '0x3d1448' for f in frames)
            assert any(f['pc_rva'] == '0x3f7358' for f in frames)
            direct_counts[direct] += 1
            proposals.append({'call_id': call['call_id'], 'direct_caller': direct,
                              'frame_rvas': [f['pc_rva'] for f in frames[:8]]})
        if 140 <= call['call_id'] <= 144:
            assert [f['pc_rva'] for f in frames[:6]] == [
                '0x3aa7c0', '0x2855e1', '0x2b50d7', '0x2ceb2e', '0x3dd849', '0x3dbfd4']
            dispatch = frames[5]['nonvolatile']
            assert int(dispatch['rdi'], 16) == 39
            endurance.append({'call_id': call['call_id'], 'argument': call['argument'],
                              'result': call['actual_result'], 'stage_index': 39,
                              'scope_object_address': dispatch['rbx'],
                              'frame_rvas': [f['pc_rva'] for f in frames[:7]]})
    assert direct_counts == {'0x3cc0bc': 100, '0x3c68e7': 50, '0x3c685a': 60, '0x3c6980': 109}
    assert len(endurance) == 5 and len({r['scope_object_address'] for r in endurance}) == 1
    return {'scope': 'Offline RTTI, instruction/dataflow and prior native-call trace audit; '
                     'no execution of proposal handlers or evidence of original run-A root cause',
            'runtime_image_sha256': hashlib.sha256(image).hexdigest(),
            'paired_analysis_sha256': hashlib.sha256((trace / 'paired-analysis.json').read_bytes()).hexdigest(),
            'rtti_types': types, 'handlers': handlers, 'instruction_anchors': anchors,
            'turn_dispatch_stages': stages, 'proposal_draw_counts': dict(direct_counts),
            'proposal_calls': proposals, 'durability_calls': endurance,
            'limits': ['Historical proposal payloads and city-linked durability were not captured in run N.',
                       'Current restored-save records cannot substitute for historical end-turn data.',
                       'Only five observed draws in this scoped lifecycle; other scenarios may execute more.',
                       'Per-faction RNG separation and proposal replication are designs, not installed changes.']}


if __name__ == '__main__':
    result = audit()
    destination = ROOT / 'proposal-scope-audit.json'
    with destination.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'handlers': len(result['handlers']), 'anchors': len(result['instruction_anchors']),
                      'proposal_draws': result['proposal_draw_counts'],
                      'durability_calls': len(result['durability_calls'])}))
