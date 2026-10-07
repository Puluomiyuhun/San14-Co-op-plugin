"""Bounded offline evidence for the Menu-pause / Game-BEFORE request boundary.

Actual copied instructions run in isolated Unicorn memory. There is no game
process access, live installer, Storage API, pending CAS, or world load here.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
from checkpoint_load_mode_native_chain import LoadModeHarness, ROOT, BASE, MEM
from checkpoint_load_mode_dispatch_audit import update
from save_return_shadow_base import d
from unicorn.x86_const import *


def prepared():
    h = LoadModeHarness(0, False, False)
    h.put32(h.coordinator, 0xAF)  # Actual readonly sample's pre-pause flags.
    h.u.mem_write(h.request, bytes(8))
    h.run(0x411980, args=(h.manager, BASE + 0x12DD6E0, h.request, h.carrier))
    h.apply()
    snap = h.snapshot()
    assert snap['stack'] == ['Root', 'Motor', 'Game', 'Strategy', 'User', 'SaveLoad']
    assert snap['control_pause'] == 1 and snap['cursor_enabled'] == 0
    assert snap['coordinator_flags'] == 0xAE
    assert all(h.readq(h.coordinator + off) == 0 for off in (0x2E8, 0x328, 0x368))
    assert h.readq(h.manager + 0x30) == 0
    return h


def user_top_gate():
    h = prepared()
    # Deliberately dirty sentinels demonstrate the top-state gate, not eligible
    # production input; the production inspector refuses these pending fields.
    h.put32(h.toolbar + 0x88, 123)
    h.put32(h.states[2] + 0x47C, 1)
    h.put32(h.panel + 0x1B0, 1)
    snapshot = h.snapshot()
    world = bytes(h.u.mem_read(h.world, 0x2200))
    first = len(h.visits)
    h.run(0x3F9B00, args=(h.user, 0, 0, 0))
    visits = h.visits[first:]
    assert {0x3F9B00, 0x509640, 0x3FA0AE} <= set(visits)
    assert 0x3F9B16 not in visits and h.snapshot() == snapshot
    assert bytes(h.u.mem_read(h.world, 0x2200)) == world
    # Negative contrast ends before the first business-body call.
    h.putq(h.manager + 0x10, 5)
    h.run(0x3F9B00, stop=BASE + 0x3F9B16, args=(h.user, 0, 0, 0))
    return {'case': 'real_User_Update_top_gate', 'result': 'PASS',
            'native_pause_flags_before': '0xAF', 'native_pause_flags_after': '0xAE',
            'six_states_returns_before_business_body': True,
            'five_states_reaches_business_body_boundary': True,
            'dirty_sentinels_unchanged': True,
            'limits': 'Actual User pause and top gate execute; singleton accessors and peripheral UI callbacks are inherited explicit stubs. The five-state contrast stops before business execution.'}


def menu_no_selection():
    h = prepared()
    row = update(h, False)
    assert row['pending_pop_count_after'] == 0
    assert 0x50B690 not in h.visits
    return {'case': 'real_SaveLoad_Update_no_selection_no_exit_input', 'result': 'PASS',
            'observation': row, 'cooperative_yield_entered': False,
            'limits': 'Actual 50B730, top predicate, SaveLoad Update and 3A29E0 execute. Graphics/input accessors are explicit stubs; no full OS scheduler proof.'}


def worker_lifetime(yielded):
    h = prepared()
    pool, lock, thunk_a, thunk_b = MEM + 0x280000, MEM + 0x282000, MEM + 0x283000, MEM + 0x284000
    worker = pool + 8
    h.putq(h.user + 0x50, worker)
    h.putq(worker + 0x10, lock)
    h.put32(worker + 0x78, int(yielded))
    h.put32(pool + 0x208, 1)
    # The real pending worker branch invokes two imported critical-section
    # routines. Only those OS primitives are stubbed in the yielded case.
    h.putq(BASE + 0x123C328, thunk_a)
    h.putq(BASE + 0x123C0D8, thunk_b)
    lock_calls = []
    h.stubs[thunk_a] = lambda: (lock_calls.append('enter'), h.ret(0))
    h.stubs[thunk_b] = lambda: (lock_calls.append('leave'), h.ret(0))
    h.stubs[BASE + 0x145B20] = lambda: h.ret(pool)
    def setup(sp):
        h.u.reg_write(UC_X86_REG_RDI, worker)
        h.putq(sp + 0x40, h.stack + 4 * 8)
    h.run(0x50B487 if yielded else 0x50B5F9, stop=BASE + 0x50B632, setup=setup)
    assert h.readq(h.user + 0x50) == (worker if yielded else 0)
    assert h.read32(pool + 0x208) == (1 if yielded else 0)
    assert lock_calls == (['enter', 'leave'] if yielded else [])
    return {'case': 'dispatcher_yielded_retains_worker' if yielded else 'dispatcher_completed_clears_worker',
            'result': 'PASS', 'state_worker_retained': yielded,
            'pool_in_use': h.read32(pool + 0x208), 'OS_lock_stubs': lock_calls,
            'limits': 'Real branch body only, with chosen branch entry and synthetic wrapper/stack. No actual worker threads, scheduler fairness, or join proof.'}


def game_pending(optional, world_kind, panel_request, blocked=False):
    h = prepared()
    # Isolated test setup, explicitly not a live CAS implementation.
    h.put32(h.cache + 0x3EC, 63)
    h.putq(BASE + 0x1FC8488, MEM + 0x285000 if optional else 0)
    h.u.mem_write(h.world + 0xBC, bytes([world_kind & 255]))
    h.put32(h.panel + 0x1F4, panel_request)
    # Execute actual tiny getters 1C1A70 / 1C0CD0, including root/world lookup.
    del h.stubs[BASE + 0x1C1A70]
    assert BASE + 0x1C0CD0 not in h.stubs
    newgame, title = MEM + 0x290000, MEM + 0x2A0000
    h.names[newgame], h.names[title] = 'ReplacementGame', 'Title'
    def allocate():
        size = h.reg(UC_X86_REG_RDX)
        assert size in (0x498, 0x13E10)
        h.ret(newgame if size == 0x498 else title)
    h.stub(h.allocvt, 0x40, allocate, 'transition_state_allocation')
    title_args = []
    def title_ctor():
        target, arg = h.reg(UC_X86_REG_RCX), h.reg(UC_X86_REG_RDX)
        assert target == title
        title_args.append(h.read32(arg))
        h.putq(title, MEM + 0x2E0000)
        h.put32(title + 0x4B0, h.read32(arg))
        h.ret(title)
    h.stubs[BASE + 0x426440] = title_ctor
    world = bytes(h.u.mem_read(h.world, 0x2200))
    rng = h.read32(BASE + 0x18EB8B0)
    first = len(h.visits)
    if blocked:
        h.run(0x3F8140, stop=BASE + 0x3F81C0, args=(h.states[2], 0, 0, 0))
        assert h.readq(h.manager + 0x30) == 0 and h.read32(h.panel + 0x1F4) == panel_request
        return {'case': 'optional_present_active_kind_and_panel_request', 'result': 'PASS',
                'production_inspector_must_reject': True,
                'reached_native_modal_write_boundary': '0x3F81C0',
                'limits': 'Stops before clearing panel flag or constructing modal; no attempt to prove modal safety.'}
    h.run(0x3F8140, args=(h.states[2], 0, 0, 0))
    visits = h.visits[first:]
    assert {0x3F8140, 0x1C1A70, 0x3DFB40, 0x3E3B90, 0x509EC0} <= set(visits)
    if optional:
        assert 0x1C0CD0 in visits
    assert not {0x3F81C0, 0x3F8544, 0x50B690, 0x3F9B00} & set(visits)
    assert title_args == [1]
    pending = h.readq(h.manager + 0x40)
    commands = [{'kind': h.read32(pending + i * 16),
                 'name': h.cstring(h.readq(pending + i * 16 + 8) + 0x70)}
                for i in range(h.readq(h.manager + 0x30))]
    assert commands == [{'kind': 3, 'name': 'CGameState'}, {'kind': 2, 'name': 'CTitleState'}]
    assert h.read32(h.states[2] + 0x474) == h.read32(h.states[2] + 0x478) == 1
    assert bytes(h.u.mem_read(h.world, 0x2200)) == world and h.read32(BASE + 0x18EB8B0) == rng
    # The actual dispatcher tail must stop after this queue change, before it
    # dispatches Strategy, User, or SaveLoad again in this iteration.
    def tail_setup(sp):
        h.u.reg_write(UC_X86_REG_R15, h.manager)
        h.u.reg_write(UC_X86_REG_R14, 0)
        h.putq(sp + 0x40, h.stack + 2 * 8)
    h.run(0x50B632, stop=BASE + 0x50B669, setup=tail_setup)
    return {'case': 'pending63_Game_branch', 'result': 'PASS', 'optional_present': optional,
            'signed_world_kind': world_kind, 'panel_request': panel_request,
            'commands': commands, 'native_Title_constructor_param': 1,
            'actual_optional_getters_executed': True,
            'world_prefix_and_rng_unchanged': True, 'direct_path_cooperative_yield': False,
            'dispatcher_stops_before_later_states': True,
            'limits': 'Actual Game Update and both queue builders execute. State allocation and Title constructor are stubs; no transitive no-yield proof for that constructor, no queue consumption/teardown/deserialization or real OS scheduling.'}


def main():
    rows = [user_top_gate(), menu_no_selection(), worker_lifetime(True), worker_lifetime(False),
            game_pending(False, 0, 1), game_pending(True, -1, 1),
            game_pending(True, 0, 0), game_pending(True, -1, 0),
            game_pending(True, 0, 1, True)]
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out = ROOT / ('checkpoint_load_input_boundary_shadow_' + stamp + '.json')
    result = {'schema': 'san14.checkpoint-load-input-boundary-shadow.v1', 'result': 'PASS',
              'cases': rows, 'game_access': False, 'live_installer': False,
              'global_input_pause_proved': False,
              'image_sha256': hashlib.sha256(d.image).hexdigest(),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'dependency_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                  ('checkpoint_load_mode_native_chain.py', 'checkpoint_load_mode_dispatch_audit.py',
                   'checkpoint_push_native_chain.py', 'save_return_user_shadow.py', 'save_return_shadow_base.py')},
              'recommendation': 'Genuine native SaveLoad pause, successful guarded Menu AFTER receipt, then same-attachment owned Game BEFORE. At Game BEFORE verify no other state worker, input neutral, no queue/selection, verify bytes, durable intent, re-inspect, own aligned pending CAS, immediately invoke original. This inspector is not a global lock.'}
    with out.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    ranges = ((0x3F9B00, 0x3F9B25), (0x3F5920, 0x3F5970), (0xC020, 0xC080),
              (0x50B470, 0x50B4B3), (0x50B5F0, 0x50B66D), (0x50B690, 0x50B72A),
              (0x50B730, 0x50B790), (0x3F8140, 0x3F81F3), (0x3F842B, 0x3F847B),
              (0x1C1A70, 0x1C1A78), (0x1C0CD0, 0x1C0CE6))
    disasm = ROOT / ('checkpoint_load_input_boundary_disasm_' + stamp + '.txt')
    with disasm.open('x', encoding='utf-8') as f:
        for start, end in ranges:
            f.write('\nRVA range %X..%X\n' % (start, end))
            for inst in d.decoder.disasm(d.image[start:end], BASE + start):
                f.write('%08X  %-8s %s\n' % (inst.address - BASE, inst.mnemonic, inst.op_str))
    print(json.dumps({'result': 'PASS', 'cases': len(rows), 'path': str(out), 'disassembly': str(disasm), 'game_access': False}))


if __name__ == '__main__':
    main()
