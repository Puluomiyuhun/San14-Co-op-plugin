"""Offline anchors for loading one shared world with separate local identities."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'python_deps'))
import capstone

POINTS = (0x2EE64C, 0x508BC2, 0x2FC850, 0x3F69F0, 0x3F72C0, 0x3F9B00)


def main():
    image = (ROOT/'game-runtime-image.bin').read_bytes()
    q = lambda at: struct.unpack_from('<Q', image, at)[0]
    base = q(0x12CC4A8+0x28)-0x3F9B00
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    types = {}
    for name, vt, methods in [
        ('CPersonData', 0x12A00D0, {0x18: 0x2119F0}),
        ('CLoadState', 0x12DBD68, {0x18: 0x495150, 0x28: 0x4A85C0}),
        ('CStrategyState', 0x12CD400, {8: 0x3F69F0, 0x28: 0x3F9690}),
        ('CUserStrategyState', 0x12CC4A8, {8: 0x3F72C0, 0x28: 0x3F9B00}),
    ]:
        locator = q(vt-8)-base
        sig, _, _, descriptor, _, own = struct.unpack_from('<6I', image, locator)
        assert sig == 1 and own == locator
        assert image[descriptor+16:image.index(0, descriptor+16)].decode() == f'.?AV{name}@@'
        assert all(q(vt+offset)-base == target for offset, target in methods.items())
        types[name] = {'vtable_rva': hex(vt), 'methods': {hex(k): hex(v) for k, v in methods.items()}}
    wanted = {
        0x2EE647: 'call 0x2f76c0', 0x2EE64C: 'mov esi, eax',
        0x2EE69D: 'call 0x2f3410', 0x2EE6A5: 'call 0x2eae80',
        0x508B87: 'call 0x2ee4a0', 0x508BC8: 'test ebx, ebx',
        0x4DA2BE: 'lea rdx, [rip + 0x2e87b]',
        0x4F7064: 'call 0x834460', 0x4F7074: 'call 0x834bc0',
        0x3F6B0A: 'call 0x2110b0', 0x3F98F5: 'call 0x2110b0',
        0x3F9909: 'jne 0x3f9989', 0x3F9982: 'call 0x3e3a20',
        0x3F99C6: 'call 0x3e0a70',
        0x3F7353: 'call 0x3d1420', 0x3F73AA: 'mov qword ptr [rdi + 0x478], rbx',
        0x3F73EC: 'cmp byte ptr [r10 + 0x165d], dl',
        0x3F7414: 'mov dword ptr [rcx - 4], eax', 0x3F741A: 'mov dword ptr [rcx], eax',
        0x3F7D14: 'call 0x2f21e0', 0x3F7D22: 'mov dword ptr [rip + 0x1bd27f0], eax',
        0x4DA3B9: 'call 0x2fc850',
    }
    anchors = []
    for at, expected in wanted.items():
        ins = next(md.disasm(image[at:at+15], at))
        actual = f'{ins.mnemonic} {ins.op_str}'
        assert actual == expected, (hex(at), actual)
        anchors.append({'rva': hex(at), 'instruction': actual, 'bytes': ins.bytes.hex()})
    strings = {}
    for at in (0x465B4C, 0x465B69, 0x465BA5, 0x3F997B, 0x3F99BF, 0x4DA39C):
        ins = next(md.disasm(image[at:at+15], at))
        op = ins.operands[1]
        assert ins.mnemonic == 'lea' and op.mem.base == capstone.x86.X86_REG_RIP
        address = ins.address+ins.size+op.mem.disp
        value = image[address:image.index(0, address)].decode('ascii')
        strings[hex(at)] = {'rva': hex(address), 'value': value}
    assert strings['0x3f997b']['value'] == 'CUserStrategyState'
    assert strings['0x3f99bf']['value'] == 'COtherStrategyState'
    assert 0x3F7D28 + 0x1BD27F0 == 0x1FCA518
    historical = json.loads((ROOT/'lockstep-traces/load-rng-run-e/unwound-stacks.json').read_text(encoding='utf-8'))[0]
    pcs = [f['pc_rva'] for f in historical['unwind']['frames']]
    assert '0x2ee64c' in pcs and '0x508b8c' in pcs and 'CLoadState' in historical['states']
    evidence = {'schema': 'san14.startup-identity-audit.v1', 'created': datetime.now().astimezone().isoformat(),
                'result': 'STATIC_ANCHORS_PASS_DYNAMIC_LOAD_ORDER_PENDING', 'types': types,
                'anchors': anchors, 'state_transition_labels': strings,
                'cached_player_force_rva': '0x1fca518',
                'historical_actual_load': {'event': historical['event'], 'states': historical['states'], 'pc_rvas': pcs},
                'observation_points': [{'rva': hex(at), 'bytes32': image[at:at+32].hex()} for at in POINTS],
                'findings': [
                    'Recorded real save load traversed worker 508B40 -> 2EE4A0 -> deserializer 2F76C0; success subsequently runs additional post-load functions. Their complete side effects remain unaudited.',
                    'CStrategyState creation already contains a local-player predicate; its update selects CUserStrategyState versus COtherStrategyState under additional conditions. The latter name alone does not establish all its behavior. Waiting until user menus exist is not a sufficient identity initialization strategy.',
                    'CUserStrategyState initialization conditionally generates proposals, then constructs local UI and copies rank-derived world arrays.',
                    '3F7B60 stores a separate force-ID cache at 1FCA518. It is not proven to run on every load path.',
                ],
                'safe_identity_insertion_point_proven': False, 'game_memory_writes': 0,
                'scope': 'RTTI and instruction assertions plus an existing real load call stack. No new load, player switch, menu rendering or complete call-graph proof.'}
    (ROOT/'startup-identity-audit.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'result': evidence['result'], 'anchors': len(anchors), 'labels': strings,
                      'cached_player_force_rva': '0x1fca518'}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
