"""Offline same-frame SaveLoad Update and pending-pop audit; no game process."""
from datetime import datetime
import hashlib
import json
import struct
from checkpoint_load_mode_native_chain import LoadModeHarness, ROOT, BASE, MEM
from save_return_shadow_base import d
from unicorn.x86_const import *


def prepare(init_cancel):
    h = LoadModeHarness(0, False, init_cancel)
    h.u.mem_write(h.request, bytes(8))
    h.run(0x411980, args=(h.manager, BASE + 0x12DD6E0, h.request, h.carrier))
    h.apply()
    assert h.stack_names()[-1] == 'SaveLoad'
    assert h.readq(h.manager + 0x30) == int(init_cancel)
    assert h.read32(h.save + 0x68) == 0 and h.read32(h.save + 0x6C) == 1
    return h


def update(h, cancel_input=False):
    graphics_vt = h.readq(h.readq(h.save + 0x60))
    for off in (0x108, 0x110):
        h.stub(graphics_vt, off, lambda: h.ret(0), 'graphics_not_busy')
    h.stubs[BASE + 0x7849B0] = lambda: h.ret(0)
    h.stubs[BASE + 0x784C10] = lambda: h.ret(0)
    input_data, keyboard, settings = MEM + 0x282000, MEM + 0x283000, MEM + 0x284000
    h.put32(input_data + 8, 0)
    h.put32(input_data + 12, 1)
    # Real 3A29E0 sees a cancel edge only in this fixture variant.
    h.put32(input_data + 0x18, 0x10 if cancel_input else 0)
    h.putq(BASE + 0x1FD1678, settings)
    h.stubs[BASE + 0x5086A0] = lambda: h.ret(0)
    h.stubs[BASE + 0x292220] = lambda: h.ret(input_data)
    h.stubs[BASE + 0xF840] = lambda: h.ret(keyboard)
    input_clear = []
    h.stubs[BASE + 0x3A2700] = lambda: (input_clear.append('input_clear_stub'), h.ret(0))
    callbacks = []
    callback, event, eventptr = MEM + 0x285000, MEM + 0x286000, MEM + 0x287000
    h.putq(callback, BASE + 0x12EA2D8)
    h.putq(callback + 8, h.save)
    h.putq(eventptr, event)
    h.put32(event + 0x80, 1)
    def synthetic_button_dispatch():
        # UI dispatch is a test double; the bound callback and native pop run.
        callbacks.append('76ECB0_to_native_4FC970')
        h.u.reg_write(UC_X86_REG_RCX, callback)
        h.u.reg_write(UC_X86_REG_RDX, eventptr)
        h.u.reg_write(UC_X86_REG_RIP, BASE + 0x4FC970)
    h.stubs[BASE + 0x76ECB0] = synthetic_button_dispatch
    call, slotbox = MEM + 0x280000, MEM + 0x281000
    h.putq(slotbox, h.stack + 5 * 8)
    h.putq(call + 8, slotbox)
    for off in (0x10, 0x18, 0x20):
        h.putq(call + off, 0)
    start = len(h.visits)
    h.run(0x50B730, args=(call,))
    visits = h.visits[start:]
    assert {0x50B730, 0x509790, 0x509640, 0x4AA200, 0x3A29E0} <= set(visits)
    assert 0x4AA26B not in visits  # unsigned -1 selection took JA before mode branch
    assert 0x4AA589 not in visits  # no pending-load write
    assert h.read32(h.cache + 0x3EC) == 0xFFFFFFFF
    assert h.read32(h.save + 0x6C) == 3
    assert bool(callbacks) == cancel_input
    return {'native_entries': [hex(x) for x in (0x50B730, 0x509790, 0x509640, 0x4AA200, 0x3A29E0)],
            'instructions': len(visits), 'original_update_calls': visits.count(0x4AA200),
            'pending_pop_count_after': h.readq(h.manager + 0x30),
            'pending_load_after': -1, 'button_dispatch': callbacks, 'input_clear': input_clear}


def sequence(init_cancel, cancel_input, after_cancel):
    h = prepare(init_cancel)
    world = bytes(h.u.mem_read(h.world, 0x2200))
    rng = h.read32(BASE + 0x18EB8B0)
    observation = update(h, cancel_input)
    count = h.readq(h.manager + 0x30)
    if after_cancel and count == 0:
        h.run(0x4D4AA0, args=(h.save,))
    count = h.readq(h.manager + 0x30)
    assert count == (2 if init_cancel and cancel_input else 1)
    pending = h.readq(h.manager + 0x40)
    assert [h.read32(pending + i * 16) for i in range(count)] == [1] * count
    assert bytes(h.u.mem_read(h.world, 0x2200)) == world and h.read32(BASE + 0x18EB8B0) == rng
    # No gameplay/save/load code is executed; positive single-pop scenarios then
    # use the same real apply/finalize/resume path as the existing fixture.
    if count == 1:
        h.apply()
        assert h.stack_names() == ['Root', 'Motor', 'Game', 'Strategy', 'User']
        assert [h.readq(h.stack + i * 8) for i in range(5)] == h.states
        assert h.readq(h.manager + 0x30) == 0
        assert h.snapshot()['advance_game'] == h.snapshot()['advance_panel'] == 0
    forbidden = {0x508B40, 0x2EE4A0, 0x2F76C0, 0x508CA0, 0x2EE740, 0x3F9B00}
    assert not forbidden & set(h.visits)
    return {'result': 'PASS', 'init_cancel': init_cancel, 'cancel_input': cancel_input,
            'after_update_cancel_if_queue_empty': after_cancel, 'update': observation,
            'pop_count': count, 'duplicate_pop_risk_demonstrated': count == 2,
            'same_user_restored_in_single_pop_cases': count == 1,
            'init_observations': h.init_observations, 'world_prefix_date_rng_unchanged': True,
            'selection_minus_one_branch_confirmed': True,
            'limits': 'UI busy/animation/input singleton accessors and button event dispatch are explicit VM stubs. '
                      'Real 3A29E0, SaveLoad Update, native callback and queue execute. No OS scheduling proof.'}


def pending_branch(baseline, current):
    h = prepare(False)
    h.putq(h.manager + 0x30, current)
    target = BASE + (0x50B470 if baseline == current else 0x50B669)
    def setup(sp):
        h.u.reg_write(UC_X86_REG_R15, h.manager)
        h.u.reg_write(UC_X86_REG_R14, baseline)
        h.putq(sp + 0x40, h.stack)
    h.run(0x50B632, stop=target, setup=setup)
    return {'result': 'PASS', 'pending_at_update_start': baseline, 'pending_after_update': current,
            'next_rva': hex(target - BASE), 'pending_nonzero_alone_stops_loop': False}


def main():
    rows = [sequence(True, False, False), sequence(True, True, False),
            sequence(False, False, True), sequence(False, True, True)]
    branches = [pending_branch(1, 1), pending_branch(0, 1)]
    output = ROOT / ('checkpoint_load_mode_dispatch_audit_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    report = {'schema': 'san14.checkpoint-load-mode-dispatch-audit.v1', 'result': 'PASS',
              'cases': rows, 'dispatcher_tail_cases': branches, 'game_access': False,
              'source_sha256': hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest(),
              'native_chain_source_sha256': hashlib.sha256((ROOT / 'checkpoint_load_mode_native_chain.py').read_bytes()).hexdigest(),
              'findings': ['Native Init returns EAX=1 and has not appended SaveLoad at its return boundary; original stack is still five states.',
                  'A queued Init-after pop does not suppress the same-frame Update. Busy/UI animation may defer it, but is not a guarantee.',
                  'Real native Update with selection UINT32_MAX takes JA before either save/load decision branch.',
                  'Invalid selection still executes native cancel-input test; input can dispatch another cancel/pop.',
                  'Cancel in Update AFTER when its queue remains empty avoids double-enqueue in these fixtures. An already queued native cancel must be independently attributed before accepting it.',
                  'State+6C is lifecycle/animation progress, not a general Update-disable bit; do not write it as a shortcut.'],
              'live_execution_eligible': False,
              'limits': ['The OS worker scheduler is not executed here. Actual dispatcher pending comparison and actual 50B730 worker body execute separately.',
                         'Native input predicate calls singleton helpers which may perform lazy initialization; it is not safe to call extra times and label the whole chain purely read-only.',
                         'No live installer, arbitrary phase changes, or real game/test once execution.']}
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'result': 'PASS', 'cases': len(rows) + len(branches), 'path': str(output), 'game_access': False}))


if __name__ == '__main__':
    main()
