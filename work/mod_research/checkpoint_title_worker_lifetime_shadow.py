"""Offline native pop/Finalize/Title-worker lifetime ordering counterexamples.

Real state-pop instructions and Load Finalize/destructor execute. OS worker
creation/start/destruction and native identity initializer are declared doubles.
The two schedules are isolated VM interleavings, not observed OS scheduling.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import struct
from checkpoint_push_native_chain import ChainHarness, ROOT, BASE, MEM
from checkpoint_load_bridge_shadow import thread_dispatch
from save_return_shadow_base import d
from unicorn import UC_PROT_NONE
from unicorn.x86_const import *


class LifetimeHarness(ChainHarness):
    def __init__(self):
        super().__init__()
        self.title, self.load = self.states[2], self.save
        self.names[self.title] = 'Title'
        self.names[self.load] = 'Load'
        self.official = [self.states[0], self.states[1], self.title, self.load]
        self.events = []
        self.load_freed = False
        self.worker_started = False
        for n, p in enumerate(self.official):
            self.putq(self.stack + n * 8, p)
        self.putq(self.manager + 0x10, 4)
        self.putq(self.manager + 0x30, 0)  # queue already copied/cleared before switch
        self.put32(self.pending, 1)
        self.putq(self.pending + 8, 0)
        self.putq(self.load, BASE + 0x12DBD68)
        self.put32(self.load + 8, 0x7FFFFFFD)
        self.put32(self.load + 0x470, 4)
        # Native callback small-buffer layout, destructor included.
        callback = self.load + 0x10
        self.putq(callback, BASE + 0x12EA4D0)
        self.putq(callback + 8, self.title)
        self.putq(self.load + 0x48, callback)
        self.u.mem_write(self.title + 0x70, b'CTitleState\0')
        self.put32(self.title + 0x470, 13)  # actual load-queued store4CEB67
        self.put32(self.title + 0x478, 0xFFFFFFFF)
        self.put32(self.title + 0x47C, 63)
        force, person = MEM + 0x1A0000, MEM + 0x1A1000
        self.force, self.person = force, person
        self.u.mem_write(force + 0x10, struct.pack('<H', 666))
        self.putq(self.root + 0x148 + 666 * 8, person)
        self.put32(BASE + 0x201EC08, 1)
        self.stubs[BASE + 0x2F21E0] = lambda: self.ret(force)
        self.stubs[BASE + 0x2F2BB0] = lambda: self.ret(1)
        ui, vt = MEM + 0x1B0000, MEM + 0x1B1000
        self.putq(self.title + 0x4B8, ui)
        self.putq(ui, vt)
        self.stub(vt, 0xC0, lambda: self.ret(0), 'title_ui')
        self.stubs[BASE + 0x50C710] = lambda: self.ret(0)
        self.stubs[BASE + 0x833CB0] = self.create_worker
        self.stubs[BASE + 0x834B60] = self.start_worker
        self.stubs[BASE + 0x833440] = self.destroy_load_thread
        # The worker must execute native509460 instead of inherited singleton stub.
        del self.stubs[BASE + 0x509460]
        self.stubs[BASE + 0x2FC850] = self.initialize_identity
        self.stubs[BASE + 0x39C260] = lambda: self.ret(MEM + 0x1B2000)
        self.stubs[BASE + 0x3A0690] = lambda: self.ret(0xAABBCCDDEEFF0011)
        self.initializers = []

    def snap(self, event):
        return {'event': event, 'stack': self.stack_names(),
                'stack_addresses': [hex(self.readq(self.stack + i * 8))
                                    for i in range(self.readq(self.manager + 0x10))],
                'title_phase': self.read32(self.title + 0x470),
                'load_freed': self.load_freed}

    def create_worker(self):
        assert self.reg(UC_X86_REG_RCX) == self.title + 0x520
        assert self.reg(UC_X86_REG_RDX) == BASE + 0x4DA390
        self.events.append(self.snap('Title_thread_construct_stub'))
        self.ret(0)

    def start_worker(self):
        assert self.reg(UC_X86_REG_RCX) == self.title + 0x520
        self.worker_started = True
        self.events.append(self.snap('Title_thread_start_stub'))
        self.ret(0)

    def destroy_load_thread(self):
        assert self.reg(UC_X86_REG_RCX) == self.load + 0x478
        self.events.append(self.snap('Load_embedded_thread_destroy_stub'))
        self.ret(0)

    def free(self):
        p = self.reg(UC_X86_REG_RDX)
        self.frees.append(self.names.get(p, 'storage'))
        if p == self.load:
            self.events.append(self.snap('allocator_before_free_Load'))
            self.load_freed = True
            # Isolated test only: make every stale dereference fail after free.
            self.u.mem_protect(self.load, 0x1000, UC_PROT_NONE)
        self.ret(0)

    def initialize_identity(self):
        assert self.reg(UC_X86_REG_RCX) == self.person
        self.initializers.append(self.snap('native_2FC850_body_stub'))
        self.ret(0)

    def hook(self, u, address, size, data):
        if hasattr(self, 'events') and address in (BASE + 0x497110, BASE + 0x4FAC30,
                BASE + 0x50B1FB, BASE + 0x437E70, BASE + 0x4DA390):
            self.events.append(self.snap('native_' + hex(address - BASE)))
        super().hook(u, address, size, data)

    def begin_pop(self, stop):
        def setup(sp):
            for reg, value in ((UC_X86_REG_R12, self.load), (UC_X86_REG_R15, self.manager),
                               (UC_X86_REG_RBX, 0), (UC_X86_REG_RSI, 0),
                               (UC_X86_REG_RDI, self.pending)):
                self.u.reg_write(reg, value)
            self.putq(sp + 0x30, 0)
        self.run(0x50B18A, stop=BASE + stop, setup=setup)

    def run_title_worker(self):
        assert self.worker_started
        self.events.append(self.snap('Title_worker_BEFORE'))
        return thread_dispatch(self, self.title + 0x520, 0x4DA390)


def schedule(eager):
    h = LifetimeHarness()
    if eager:
        # Stop after native worker-start CALL returns but before phase15 store.
        h.begin_pop(0x4BEEC2)
        assert h.stack_names() == ['Root', 'Motor', 'Title', 'Load']
        assert h.read32(h.title + 0x470) == 13 and not h.load_freed
        cpu = h.u.context_save()
        # Use a different VM stack to model a distinct OS worker. thread_dispatch
        # normally uses EF000; preserve the paused caller stack around this run.
        paused_stack = bytes(h.u.mem_read(MEM + 0xEE000, 0x2000))
        worker = h.run_title_worker()
        h.u.mem_write(MEM + 0xEE000, paused_stack)
        h.u.context_restore(cpu)
        h.stop = BASE + 0x50B394
        h.u.emu_start(BASE + 0x4BEEC2, h.stop, count=100000)
        assert h.reg(UC_X86_REG_RIP) == h.stop
    else:
        h.begin_pop(0x50B394)
        assert h.load_freed and h.stack_names() == ['Root', 'Motor', 'Title']
        worker = h.run_title_worker()
    assert h.load_freed and h.stack_names() == ['Root', 'Motor', 'Title']
    assert len(h.initializers) == 1
    assert h.read32(h.title + 0x470) == 15
    before = next(x for x in h.events if x['event'] == 'Title_worker_BEFORE')
    assert before['load_freed'] != eager
    required = {0x497110, 0x4FAC30, 0x4CC690, 0x4BDD90, 0x4BEE50,
                0x437E70, 0x4DA390, 0x509460, 0x4FABC0}
    assert required <= set(h.visits)
    return {'case': 'worker_before_Finalize_returns' if eager else 'worker_after_Load_freed',
            'result': 'PASS', 'worker_before': before, 'worker': worker,
            'events': h.events, 'final_stack': h.stack_names(),
            'load_page_NOACCESS_before_late_worker': not eager,
            'native_title_lookup_succeeded': True, 'initializer_calls': 1,
            'native_pop_Finalize_destructor_executed': True,
            'OS_scheduling_actually_executed': False}


def main():
    cases = [schedule(True), schedule(False)]
    out = {'schema': 'san14.checkpoint-title-worker-lifetime-shadow.v1',
           'result': 'PASS', 'cases': cases, 'game_access': False,
           'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'image_sha256': hashlib.sha256(d.image).hexdigest(),
           'scope': 'Actual native type1-pop tail, Load Finalize/callback/Title start path, '
                    'Load destructor, and generic worker invocation/native Title lookup execute. '
                    'State objects are synthetic; OS thread/allocator free/UI and identity initializer bodies '
                    'are explicit doubles. Two possible schedules are imposed, not observed.',
           'conclusion': 'Title worker BEFORE can see four formal states while Load Finalize '
                    'has not returned, or three after Load has been freed. It must never rely on '
                    'dereferencing the prior Load pointer to reconstruct join evidence. '
                    'Preserve transaction-bound immutable Load evidence before this boundary.',
           'not_proved': ['actual game thread scheduling', 'native join success in this test',
                         'complete dispatcher/world lifetime synchronization', 'live identity adapter safety']}
    path = ROOT / ('checkpoint_title_worker_lifetime_shadow_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with path.open('x', encoding='utf8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({'result': 'PASS', 'cases': len(cases), 'path': str(path), 'game_access': False}))


if __name__ == '__main__':
    main()
