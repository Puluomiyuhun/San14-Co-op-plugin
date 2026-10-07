"""Verify a candidate native reload request route using captured code and logs only.

This never imports a game reader, executes native game code or opens a process.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'python_deps'))
import capstone

ANCHORS = {
    0x4AA582: 'mov rax, qword ptr [rip + 0x1b7ad8f]',
    0x4AA589: 'mov dword ptr [rax + 0x3ec], esi',
    0x3F8177: 'mov rax, qword ptr [rip + 0x1c2d19a]',
    0x3F817E: 'cmp dword ptr [rax + 8], 0',
    0x3F8184: 'cmp dword ptr [rax + 0x3ec], 0',
    0x3F818D: 'mov dword ptr [rcx + 0x474], r12d',
    0x3F842B: 'cmp dword ptr [rdi + 0x478], 0',
    0x3F8438: 'mov dword ptr [rdi + 0x478], r12d',
    0x3F8451: 'call 0x3dfb40',
    0x3F846D: 'call 0x3e3b90',
    0x4A370C: 'mov rax, qword ptr [rip + 0x1b81c05]',
    0x4A3713: 'cmp dword ptr [rax + 0x3ec], 0',
    0x4A3721: 'call 0x4ceab0',
    0x4CEAE0: 'mov rcx, qword ptr [rip + 0x1b56831]',
    0x4CEAE7: 'mov edi, dword ptr [rcx + 0x3ec]',
    0x4CEAF7: 'call 0x836710',
    0x4CEAFC: 'test rax, rax',
    0x4CEAFF: 'je 0x4cec0f',
    0x4CEB05: 'mov dword ptr [rbx + 0x47c], edi',
    0x4CEB0B: 'lea rdx, [rax + 0x128]',
    0x4CEB62: 'call 0x410810',
    0x4CEB67: 'mov dword ptr [rbx + 0x470], 0xd',
    0x4CEBF4: 'call 0x4bf5a0',
    0x836710: 'cmp edx, 0x77',
    0x836718: 'mov rax, qword ptr [rcx + rax*8 + 0x20]',
    0x835D91: 'call 0x2f7610',
    0x835D9A: 'setns bl',
    0x4BF5C5: 'mov dword ptr [rip + 0x1b5f705], eax',
    0x4BF5CE: 'mov dword ptr [rip + 0x1b5f700], eax',
    0x4BF5D7: 'mov dword ptr [rip + 0x1b5f6fb], eax',
    0x4BF5E1: 'lea rcx, [rip + 0x1b5f6f8]',
    0x4DA2BE: 'lea rdx, [rip + 0x2e87b]',
    0x4DA2F9: 'mov dword ptr [rip + 0x1b44905], 0',
    0x508B87: 'call 0x2ee4a0',
    0x508BC2: 'mov dword ptr [rip + 0x1b16040], ebx',
    0x4F7064: 'call 0x834460',
    0x4F7074: 'call 0x834bc0',
    0x465AB6: 'cmp dword ptr [rip + 0x1bb914b], 0',
    0x465AEC: 'mov dword ptr [rbx + 8], 0x7ffffffd',
    0x465B3D: 'mov dword ptr [rbx + 8], 0x7ffffffe',
    0x835DDE: 'mov dword ptr [rbx + 0x3ec], 0xffffffff',
    0x4FAC37: 'jmp 0x4cc690',
    0x4CC696: 'cmp dword ptr [rip + 0x1b5256b], 0',
    0x4CC6A2: 'call 0x4bdd90',
    0x4CC6AA: 'call 0x4bee50',
    0x4BDE1C: 'mov qword ptr [rbx + 0x4a8], rsi',
    0x4BDE2D: 'mov qword ptr [rbx + 0x4a0], rdi',
    0x4BEE8C: 'lea rdx, [rip + 0x1b4fd]',
    0x4DA3B2: 'mov rcx, qword ptr [rax + 0x4a8]',
    0x4DA3B9: 'call 0x2fc850',
}


def main():
    image = (ROOT / 'game-runtime-image.bin').read_bytes()
    image_sha = hashlib.sha256(image).hexdigest()
    assert image_sha == '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
    q = lambda p: struct.unpack_from('<Q', image, p)[0]
    base = q(0x12CC4A8 + 0x28) - 0x3F9B00
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    anchors = []
    for at, expected in ANCHORS.items():
        ins = next(md.disasm(image[at:at+15], at))
        actual = f'{ins.mnemonic} {ins.op_str}'
        assert actual == expected, (hex(at), actual, expected)
        row = {'rva': hex(at), 'bytes': ins.bytes.hex(), 'instruction': actual}
        for op in ins.operands:
            if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                row['rip_target'] = hex(ins.address + ins.size + op.mem.disp)
        anchors.append(row)
    types = []
    for vt, name, offset, target in (
        (0x12CC9B8, 'CGameState', 0x28, 0x3F8140),
        (0x12DAAF0, 'CTitleState', 8, 0x4A2E30),
        (0x12DBD68, 'CLoadState', 0x28, 0x4A85C0),
    ):
        loc = q(vt-8)-base
        td = struct.unpack_from('<I', image, loc+12)[0]
        assert image[td+16:image.index(0, td+16)].decode() == f'.?AV{name}@@'
        assert q(vt+offset)-base == target
        types.append({'type': name, 'vtable': hex(vt), 'method_offset': hex(offset), 'method': hex(target)})
    assert q(0x12EA4D0+16)-base == 0x4FAC30
    historical_path = ROOT / 'startup-switch-traces/20261006-124754-542123/trace.jsonl'
    rows = [json.loads(line) for line in historical_path.read_text(encoding='utf-8').splitlines()]
    names = ('deserialize_return', 'load_worker_result', 'title_selection_boundary',
             'title_selection_written', 'native_identity_initializer', 'native_identity_return',
             'strategy_initialize', 'user_strategy_initialize', 'first_user_update')
    history = []
    positions = []
    for name in names:
        matching = [(i, r) for i, r in enumerate(rows) if r.get('event') == name]
        assert len(matching) == 1, name
        i, row = matching[0]
        positions.append(i)
        history.append({k: row[k] for k in ('event', 'seq', 'tick_ms', 'thread', 'states', 'player') if k in row})
    assert positions == sorted(positions)
    assert rows[-1] == {'event':'detached','captured':True,'registers_restored':True}
    out = {
        'schema': 'san14.reload-entry-static-audit.v1',
        'created': datetime.now().astimezone().isoformat(),
        'result': 'STATIC_NATIVE_REQUEST_ROUTE_IDENTIFIED_AUTOMATIC_TRIGGER_UNTESTED',
        'game_access': False, 'native_calls': 0, 'game_memory_writes': 0,
        'runtime_image_sha256': image_sha, 'anchors': anchors, 'types': types,
        'candidate_request': {
            'manager_pointer_rva':'0x2025318','mode_offset':'0x8','ordinary_load_mode':0,
            'pending_slot_offset':'0x3ec','idle_pending_slot':-1,'slot_range':[0,119],
            'metadata_table_offset':'0x20','metadata_stride':8,'metadata_filename_string_offset':'0x128',
            'native_user_commit_rva':'0x4aa589','consumer_rva':'0x3f8177',
            'candidate_mutation':'A single guarded pending-slot write on the native update thread, only if manager mode already equals 0 and pending slot equals -1.',
            'automatic_trigger_proven':False,
            'directory_cache_refresh_for_received_file_proven':False,
            'slot_number_to_visible_label_mapping_proven':False,
        },
        'native_route': [
            'CSaveLoadState selection confirms and native file-availability check (835D30 -> 2F7610) succeeds before pending-slot commit; this check is not full header/content validation.',
            'CGameState update sees mode 0 and nonnegative pending slot; marks +474 and uses +478 as native transition reentry gate.',
            'Native state manager queues CGameState transition and a new CTitleState, whose initialization sees the pending slot.',
            'CTitleState 4CEAB0 resolves cached slot metadata and filename, enqueues CLoadState with callback, binds global slot/mode/string via 4BF5A0.',
            'CLoadState creates worker 508B40; worker calls 2EE4A0 -> 2F76C0 and publishes result at 201EC08.',
            'CLoadState waits for worker completion/join and native minimum display interval, then takes success/error branch and clears request metadata.',
            'On success callback 4FAC30 -> 4CC690 calls 4BDD90 to construct Title force/ruler selection from loaded world, then starts worker 4DA390.',
            'At 4DA3B2 before MOV RCX, replace Title +4A0/+4A8 together using stable B force/ruler IDs resolved in NEW world; native 2FC850 runs exactly once.',
            'Wait for fresh CGameState/CStrategyState/CUserStrategyState and verify B identity plus authority world before releasing input.',
        ],
        'load_state_phases': {'0':'set start timestamp and phase 1','1':'create/start 508B40 worker; reset result; phase 2','2':'wait/join thread; phase 3','3':'minimum elapsed display check; phase 4','4':'result-specific completion/error then request cleanup'},
        'binding_globals': {'slot':'0x201ecd0','special_mode':'0x201ecd4','alternate_mode':'0x201ecd8','filename_string':'0x201ece0','result':'0x201ec08'},
        'historical_manual_load': {'trace': str(historical_path.relative_to(ROOT)), 'sha256':hashlib.sha256(historical_path.read_bytes()).hexdigest(), 'points':history,
            'scope':'Actual user-triggered load and one B identity handoff; earliest new request commit/Title-init path was not instrumented.'},
        'must_hold_before_pilot': [
            'Trusted A checkpoint bytes/hash/profile and authoritative phase bound to one durable load intent.',
            'B fully quiescent at supported planning boundary; no simulation/save/load workers, native commands, pending formal event or modal UI.',
            'Exact supported code/RTTI profile, expected GameState object and empty transition queue; room input remains held throughout.',
            'Native manager mode already 0, pending -1, candidate slot metadata exists and names the exact staged artifact; immutable hash equals the already proven valid slot34 fixture for this pilot.',
            'Use a dedicated backed-up scratch slot; never slot34 or an unapproved occupied slot. Slot numeric mapping must be observed, not guessed.',
            'Resolve B force/ruler/main-district in newly loaded world. If B force has ceased to exist, stop for defeat/spectator policy instead of forcing pointers.',
            'Do not reuse the earlier hard-coded slot34/783-record identity switch binary against a new period checkpoint; update guards to the checkpoint manifest and same-stage baseline.',
        ],
        'restart_and_failure': [
            'Native pending slot and success flag are singleton fields, not room/epoch scoped or durable; external one-attempt journal required.',
            'Missing cached slot metadata returns from Title resolver without starting a load; it is not a successful no-op.',
            'A nonzero result alone is insufficient: must match current worker start/join and requested checkpoint; never accept stale state or repeat on timeout.',
            'Native load can mutate world before detecting errors. Once worker has started, hold B and perform explicit recovery; do not resume speculative world or automatically retry.',
            'Keep A unchanged at authoritative boundary until B loaded receipt and world checks pass.',
        ],
        'full_world_equality_proven':False,
        'remaining_shared_world_issue':'Original native identity/UI initialization consumes RNG and computes viewpoint-dependent city previews. Apply shared-human rules/sidecar at audited boundaries and check semantic full world, not raw pointers or unqualified file hash.',
    }
    (ROOT/'reload-entry-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':out['result'],'anchors':len(anchors),'types':len(types),'historical_points':len(history),'game_access':False},ensure_ascii=False))

if __name__ == '__main__':
    main()
