"""Native SaveLoad Update branch execution with explicit modal test double.

Offline only. This does NOT prove the real dialog's coroutine scheduling or
authorize calling Update from User AFTER. All resulting load requests remain
inside Unicorn memory and are never consumed by CGame/Title.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
from checkpoint_metadata_boundary_cc_shadow import CCHarness, BASE, MEM, ROOT
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import *


def run_case(kind):
    h = CCHarness()
    h.u.mem_write(h.request, bytes(8))
    h.run(0x411980, args=(h.manager, BASE + 0x12DD6E0, h.request, h.carrier))
    h.apply()
    h.run(0x836EF0, args=(h.cache, 0))
    assert h.readq(h.cache + 0x20 + 63 * 8)
    # Synthetic dispatcher-current-state and existing Game name. Real modal
    # scheduling is not executed; native 2A1DB0/509450 read this current state.
    h.putq(h.manager + 0x48, h.save)
    h.u.mem_write(h.states[2] + 0x70, b'CGameState\0')
    h.put32(h.list + 0x170, 63)
    if kind == 'missing_after_scan':
        h.cc_present = False
    if kind == 'null_metadata':
        h.putq(h.cache + 0x20 + 63 * 8, 0)
    if kind == 'slot120':
        h.put32(h.list + 0x170, 120)
    if kind == 'no_selection':
        h.put32(h.list + 0x170, 0xFFFFFFFF)
    if kind == 'not_stack_top':
        h.putq(h.manager + 0x10, 5)
    if kind == 'no_game_parent':
        h.u.mem_write(h.states[2] + 0x70, b'AbsentGame\0')
    for n, global_rva in enumerate((0x1FCA330, 0x1FCA340)):
        head = MEM + 0x2B0000 + n * 0x100
        h.putq(BASE + global_rva, head)
        for off in (0, 8, 16):
            h.putq(head + off, head)
        h.u.mem_write(head + 0x19, b'\x01')
    # Localized-string/formatting peripherals are not relevant to submit order.
    vt = MEM + 0x2B4000
    h.putq(BASE + 0x18CBF00, vt)
    h.stub(vt, 8, lambda: h.ret(h.output), 'localized_string')
    h.stubs[BASE + 0x2D54E0] = lambda: h.ret(0)
    h.stubs[BASE + 0x188970] = lambda: h.ret(0)
    confirmations, errors, pending_writes = [], [], []
    def modal_stub():
        assert h.reg(UC_X86_REG_RCX) == h.output
        assert h.read32(h.cache + 0x3EC) == 0xFFFFFFFF
        accepted = kind != 'decline'
        confirmations.append({'accepted': accepted, 'pending_before': -1})
        h.put32(h.save + 0x58, int(accepted))
        h.ret(int(accepted))
    h.stubs[BASE + 0x1F65D0] = modal_stub
    h.stubs[BASE + 0x1D5170] = lambda: (errors.append('native_error_dialog_stub'), h.ret(0))
    # Actual cancel predicate executes with no cancel edge; singleton getters
    # and keyboard service are explicit fixture doubles.
    input_data, keyboard, settings = MEM + 0x282000, MEM + 0x283000, MEM + 0x284000
    h.put32(input_data + 8, 0)
    h.put32(input_data + 12, 1)
    h.put32(input_data + 0x18, 0)
    h.putq(BASE + 0x1FD1678, settings)
    h.stubs[BASE + 0x5086A0] = lambda: h.ret(0)
    h.stubs[BASE + 0x292220] = lambda: h.ret(input_data)
    h.stubs[BASE + 0xF840] = lambda: h.ret(keyboard)
    def watch(u, access, address, size, value, data):
        if address == h.cache + 0x3EC:
            pending_writes.append({'instruction_rva': hex(h.reg(UC_X86_REG_RIP) - BASE),
                                   'size': size, 'value': value})
    h.u.hook_add(UC_HOOK_MEM_WRITE, watch)
    before_world = bytes(h.u.mem_read(h.world, 0x2200))
    before_rng = h.read32(BASE + 0x18EB8B0)
    start, reads_before, exists_before = len(h.visits), len(h.scan_reads), len(h.scans)
    h.run(0x4AA200, args=(h.save, 0, 0, 0))
    visits = h.visits[start:]
    pending = h.read32(h.cache + 0x3EC)
    selected = h.read32(h.list + 0x170)
    queued = h.readq(h.manager + 0x30)
    successful = kind in ('accept', 'no_game_parent')
    assert pending == (63 if successful else 0xFFFFFFFF)
    assert queued == int(kind == 'no_game_parent')
    if queued:
        assert h.read32(h.readq(h.manager + 0x40)) == 1
    assert bool(confirmations) == (kind not in ('no_selection', 'not_stack_top'))
    assert bool(errors) == (kind in ('missing_after_scan', 'null_metadata', 'slot120'))
    assert bool(pending_writes) == successful
    if successful:
        assert pending_writes == [{'instruction_rva': '0x4aa589', 'size': 4, 'value': 63}]
        assert {0x2A1DB0, 0x835D30, 0x2F7610, 0x5096C0} <= set(visits)
    if kind in ('decline', 'missing_after_scan', 'null_metadata', 'slot120', 'no_selection'):
        assert selected == 0xFFFFFFFF
    if kind == 'decline':
        assert 0x835D30 not in visits
    assert len(h.scan_reads) == reads_before
    assert bytes(h.u.mem_read(h.world, 0x2200)) == before_world
    assert h.read32(BASE + 0x18EB8B0) == before_rng
    forbidden = {0x3F8140, 0x3F9B00, 0x508B40, 0x2EE4A0, 0x2FC750, 0x508CA0}
    assert not forbidden.intersection(visits)
    return {'case': kind, 'result': 'PASS', 'native_entry': '0x4AA200',
            'pending_load_after': -1 if pending == 0xFFFFFFFF else pending,
            'selected_after': -1 if selected == 0xFFFFFFFF else selected,
            'pending_writes': pending_writes, 'new_queue_count': queued,
            'queue_kind_if_any': 1 if queued else None,
            'confirmation_stub_observations': confirmations, 'error_dialog_stubs': errors,
            'new_FileExists_queries': h.scans[exists_before:], 'new_file_bytes_read': 0,
            'world_prefix_rng_unchanged_in_VM': True,
            'native_game_transition_or_advance_executed': False,
            'native_checks_executed': [hex(x) for x in (0x509640, 0x2A1DB0, 0x509450,
                     0x835D30, 0x2F7610, 0x5096C0, 0x10A60, 0x3A29E0) if x in visits]}


def main():
    cases = [run_case(k) for k in ('accept', 'decline', 'missing_after_scan',
                   'null_metadata', 'slot120', 'no_selection', 'not_stack_top', 'no_game_parent')]
    report = {'schema': 'san14.checkpoint-load-submit-update-shadow.v1', 'result': 'PASS',
              'cases': cases, 'game_access': False, 'live_execution_eligible': False,
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'captured_image_sha256': hashlib.sha256((ROOT / 'game-runtime-image.bin').read_bytes()).hexdigest(),
              'scope': 'Actual complete 4AA200 and native top-state, confirmation-result, metadata/exists, '
                       'parent lookup, pending store, optional native pop queue and no-edge cancel predicate. '
                       'State/UI/header preparation uses inherited CCHarness native code with declared doubles.',
              'critical_limit': '1F65D0 is replaced by a synchronous fixture response. Its real modal creation '
                       'and 50B690 coroutine yield are NOT executed. manager+48 current state and list+170 are '
                       'fixture setup. This does not prove production automation or User-AFTER safety.',
              'additional_stubs': ['localized string resource/formatting', 'input singleton getters',
                       'error-dialog UI', 'Steam FileExists transport', 'inherited UI/allocator/storage primitives'],
              'conclusion': 'Native Update submits pending63 only after accepted confirmation and metadata-present '
                       'FileExists. It refuses a non-top SaveLoad. With CGameState present it queues no local pop; '
                       'a later CGame update consumes pending and drives Title/load. No reviewed slot-only setter exists.'}
    path = ROOT / ('checkpoint_load_submit_update_shadow_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with path.open('x', encoding='utf8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'result': 'PASS', 'cases': len(cases), 'path': str(path), 'game_access': False}))


if __name__ == '__main__':
    main()
