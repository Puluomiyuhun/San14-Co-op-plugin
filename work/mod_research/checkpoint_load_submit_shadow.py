"""Bounded offline native slot selection / existence-only validator evidence.

No process APIs, game hooks or real Steam access. Row widgets are explicitly
synthetic fixture input, not a proposed production UI adapter. This does not
execute the confirmation scheduler, CGame transition, or world deserializer.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
from checkpoint_metadata_boundary_cc_shadow import CCHarness, BASE, MEM, ROOT
from unicorn.x86_const import UC_X86_REG_RAX


def invariants(h):
    return (bytes(h.u.mem_read(h.world, 0x2200)), h.read32(BASE + 0x18EB8B0),
            h.read32(h.cache + 0x3EC), h.readq(h.manager + 0x30))


def row_case(row, cc, compact, expected):
    h = CCHarness()
    widget = MEM + 0x2B1000
    h.put32(widget + 0x80, row & 0xFFFFFFFF)
    h.put32(widget + 0x178, compact)
    h.put32(widget + 0x248, cc)
    for i in range(50):
        h.put32(widget + 0x180 + i * 4, i)
    h.put32(h.list + 0x170, 0xFFFFFFFF)
    before = invariants(h)
    h.run(0x4D1600, args=(h.list, widget))
    selected = h.read32(h.list + 0x170)
    assert selected == expected and invariants(h) == before
    return {'case': 'native_row_callback', 'result': 'PASS', 'row': row,
            'cc_flag': cc, 'compact_flag': compact, 'selected_slot': selected,
            'pending_load_unchanged': True, 'queue_unchanged': True,
            'world_prefix_and_rng_unchanged_in_VM': True,
            'native_entry': '0x4D1600',
            'limit': 'Fixture supplies a synthetic widget and identity row map. '
                     'This proves the leaf arithmetic only; no UI construction, '
                     'event delivery or safe live selection is implied.'}


def validate_case(kind):
    h = CCHarness()
    # Native 2E24B0 invokes native 2F4B20, which clears two archive bookkeeping
    # trees. Give it valid empty native-layout trees; do not stub that function.
    for n, global_rva in enumerate((0x1FCA330, 0x1FCA340)):
        head = MEM + 0x2B0000 + n * 0x100
        h.putq(BASE + global_rva, head)
        for off in (0, 8, 16):
            h.putq(head + off, head)
        h.u.mem_write(head + 0x19, b'\x01')
    h.run(0x836EF0, args=(h.cache, 0))
    assert h.readq(h.cache + 0x20 + 63 * 8)
    slot = 63
    expected = 1
    if kind == 'missing_after_scan':
        h.cc_present = False
        expected = 0
    elif kind == 'null_metadata':
        h.putq(h.cache + 0x20 + 63 * 8, 0)
        expected = 0
    elif kind == 'out_of_range':
        slot = 120
        expected = 0
    before = invariants(h)
    reads_before, exists_before = len(h.scan_reads), len(h.scans)
    start = len(h.visits)
    h.run(0x835D30, args=(h.cache, slot))
    accepted = h.reg(UC_X86_REG_RAX) & 0xFFFFFFFF
    visited = set(h.visits[start:])
    assert accepted == expected and invariants(h) == before
    assert len(h.scan_reads) == reads_before
    expected_exists = int(kind in ('present', 'missing_after_scan'))
    assert len(h.scans) - exists_before == expected_exists
    assert (0x2F7610 in visited) == bool(expected_exists)
    return {'case': 'native_exists_validator_' + kind, 'result': 'PASS',
            'slot': slot, 'accepted': bool(accepted),
            'new_FileExists_queries': h.scans[exists_before:],
            'new_archive_bytes_read': 0, 'pending_load_unchanged': True,
            'queue_unchanged': True, 'world_prefix_and_rng_unchanged_in_VM': True,
            'native_entries': ['0x835D30'] + (['0x2E24B0', '0x2F4B20',
                               '0x2F7610', '0x2E34A0'] if expected_exists else []),
            'limits': 'Steam context/FileExists and scanner stream transport are '
                      'fixture doubles inherited from CCHarness. Native scanner '
                      'and archived header parser execute during preparation; '
                      '835D30 itself reads no file bytes and proves no SHA.'}


def main():
    cases = [row_case(3, 1, 0, 63), row_case(-1, 1, 0, 60),
             row_case(50, 1, 0, 60), row_case(3, 0, 0, 3),
             row_case(3, 1, 1, 113)]
    cases += [validate_case(k) for k in ('present', 'missing_after_scan',
                                      'null_metadata', 'out_of_range')]
    result = {
        'schema': 'san14.checkpoint-load-submit-shadow.v1', 'result': 'PASS',
        'cases': cases, 'game_access': False, 'load_requested': False,
        'live_execution_eligible': False,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'captured_image_sha256': hashlib.sha256((ROOT / 'game-runtime-image.bin').read_bytes()).hexdigest(),
        'finding': 'Native row callback can map CC row3 to slot63, but neither '
                   'that callback nor native 835D30 validation commits pending. '
                   'The validator is metadata-present plus Steam FileExists, '
                   'not a new header or file-byte identity verification.',
        'not_executed': ['real UI category construction or input',
                         '1F65D0 confirmation modal and 50B690 yield',
                         'full SaveLoad Update selected-load branch',
                         'Game/Title transition or world load'],
        'negative_warning': '4D1600 maps invalid row -1 or row50 to CC slot60, '
                            'so the callback alone is not a safe validating slot setter.'}
    path = ROOT / ('checkpoint_load_submit_shadow_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with path.open('x', encoding='utf8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'result': 'PASS', 'cases': len(cases), 'path': str(path),
                      'game_access': False}))


if __name__ == '__main__':
    main()
