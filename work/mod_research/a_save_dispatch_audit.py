"""Offline Save queue successor executing actual User lifecycle callbacks.

Only a caller-supplied, hash-pinned research image is accepted. No process,
Steam, current save, injection or production permission interface exists.
"""
import ast
import struct
from pathlib import Path
from types import SimpleNamespace

P = Path(__file__).resolve().parent
BASE, MEM, STOP = 0x7FF749440000, 0x300000000, 0x3000F0000


def need(ok, message):
    if not ok:
        raise AssertionError(message)


def make_harness(raw, selected=False, phase=2):
    import unicorn
    from unicorn import x86_const
    ns = {k: getattr(unicorn, k) for k in ('Uc', 'UC_ARCH_X86', 'UC_MODE_64', 'UC_HOOK_CODE')}
    ns.update({k: getattr(x86_const, k) for k in dir(x86_const) if k.startswith('UC_')})
    ns.update(BASE=BASE, MEM=MEM, STOP=STOP, d=SimpleNamespace(image=raw),
              struct=struct, q=lambda n: struct.pack('<Q', n))
    path = P / 'private_checkpoint_save_apply_regression.py'
    tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Harness']
    need(len(classes) == 1, 'one archived queue harness class')
    exec(compile(ast.Module(body=classes, type_ignores=[]), str(path), 'exec'), ns)
    x = x86_const

    class LifecycleHarness(ns['Harness']):
        def __init__(self):
            super().__init__()
            self.services = []
            self.native_events = []
            self.input = MEM + 0x60000
            self.updater = MEM + 0x62000
            self.toolbar = MEM + 0x64000
            self.scene = MEM + 0x66000
            self.panel = MEM + 0x67000
            self.secondary = MEM + 0x68000
            self.cursor = MEM + 0x69000
            self.put32(self.user + 0x470, phase)
            self.putq(self.user + 0x478, self.toolbar)
            self.putq(self.states[2] + 0x480, self.panel)
            self.putq(self.panel + 0x178, self.secondary)
            self.put32(self.secondary + 0x198, 77)
            self.u.mem_write(self.input, struct.pack('<H', 1))
            self.put32(self.updater + 0x28, 0)
            if selected:
                self.putq(self.user + 0x4A8, MEM + 0x6A000)
            vt = self.readq(self.user)
            self.native_callbacks = {0x3F5530: 'resume', 0x3F5920: 'pause',
                                     0x3F7710: 'enter_event', 0x3F7A70: 'exit_event'}
            # The predecessor constructor double only returned the first
            # prebuilt state. Reused owned allocation needs its graphics slot
            # reconstructed after native pop cleared it; no real UI is built.
            def save_construct():
                self.putq(self.save + 0x60, MEM + 0x50000)
                self.put32(self.save + 0x470, 0)
                self.service('Save constructor with fresh owned graphics association', self.save)
            self.stubs[BASE + 0x4263C0] = save_construct
            for offset, rva in ((0x18, 0x3F5530), (0x20, 0x3F5920),
                                (0x58, 0x3F7710), (0x60, 0x3F7A70)):
                need(struct.unpack_from('<Q', raw, 0x12CC4A8 + offset)[0] == BASE + rva,
                     'native User vtable source')
                self.putq(vt + offset, BASE + rva)
            toolbar_vt = MEM + 0x6B000
            self.putq(self.toolbar, toolbar_vt)
            for offset in (0x38, 0x40):
                self.stub(toolbar_vt, offset,
                          lambda offset=offset: self.service('toolbar virtual '+hex(offset)), 'toolbar')
            for rva, label, value in (
                (0x161170, 'updater singleton', self.updater),
                (0xF720, 'input singleton', self.input),
                (0x173F0, 'cursor singleton', self.cursor),
                (0x5086A0, 'special save-mode service absent', 0),
                (0x2F5F70, 'scene mode predicate', 1),
                (0x509460, 'named Game state lookup', self.states[2]),
                (0x194A90, 'global UI singleton', self.scene),
                (0x3ECFD0, 'scene effect singleton', self.scene),
                (0x17A480, 'secondary scene singleton', self.scene),
                (0xF570, 'graphics singleton', self.scene),
                (0x7842E0, 'toolbar graphics membership', 0),
                (0x784D50, 'Game panel mode', 1),
            ):
                self.stubs[BASE + rva] = lambda label=label, value=value: self.service(label, value)
            for rva, label in ((0x8242B0, 'cursor enable'), (0x177EE0, 'scene effect clear'),
                               (0x12EE0, 'secondary scene clear'), (0x1A8540, 'global UI refresh'),
                               (0x7A9D40, 'secondary panel refresh'), (0xEF9F20, 'cookie validation')):
                self.stubs[BASE + rva] = lambda label=label: self.service(label)
            self.stubs[BASE + 0x2F2BB0] = lambda: self.service('selection validity', int(self.reg(x.UC_X86_REG_RCX) != 0))
            self.stubs[BASE + 0x3E8EF0] = lambda: self.service('selection clear business')
            self.stubs[BASE + 0xEF9F20] = lambda: self.service('cookie validation preserving RAX', self.reg(x.UC_X86_REG_RAX))
            # Camera math is a named leaf double. Native 8F50 sets the input
            # enable bit; native 13E90 takes its bit1-clear branch afterwards.
            self.stubs[BASE + 0xD390] = self.math_zero
            self.stubs[BASE + 0xF1D950] = self.math_zero

        def service(self, label, value=0):
            self.services.append(dict(label=label, rcx=hex(self.reg(x.UC_X86_REG_RCX)),
                                      edx=self.reg(x.UC_X86_REG_RDX) & 0xFFFFFFFF))
            self.ret(value)

        def math_zero(self):
            self.u.reg_write(x.UC_X86_REG_XMM0, 0)
            self.service('camera scalar math')

        def hook(self, machine, address, size, unused):
            rva = address - BASE
            if rva in self.native_callbacks:
                self.native_events.append(dict(method=self.native_callbacks[rva],
                    user=hex(self.reg(x.UC_X86_REG_RCX)), kind=self.reg(x.UC_X86_REG_RDX) & 0xFFFFFFFF,
                    phase=struct.unpack('<I', self.u.mem_read(self.user + 0x470, 4))[0]))
            super().hook(machine, address, size, unused)

        def input_state(self):
            return dict(enabled=bool(self.u.mem_read(self.input, 1)[0] & 1),
                        paused=struct.unpack('<I', self.u.mem_read(self.updater + 0x28, 4))[0],
                        handlers=[hex(self.readq(self.input + off + 0x38)) for off in (0x2B0, 0x2F0, 0x330)],
                        phase=struct.unpack('<I', self.u.mem_read(self.user + 0x470, 4))[0],
                        panel_refresh=struct.unpack('<I', self.u.mem_read(self.secondary + 0x198, 4))[0])

        def run(self, *args, **kwargs):
            try:
                return super().run(*args, **kwargs)
            except Exception as exc:
                pc = self.reg(x.UC_X86_REG_RIP)
                raise RuntimeError('archive execution failed at '+hex(pc-BASE)+
                                   '; recent='+str(self.visits[-12:])) from exc

    return LifecycleHarness()


def lifecycle_case(raw, selected=False, phase=2):
    h = make_harness(raw, selected, phase)
    snapshots = []
    for generation in (1, 2):
        need(h.queue(0x2DF990) == 0, 'normal push kind')
        need(h.apply() == ['Root', 'Motor', 'Game', 'Strategy', 'User', 'Save'], 'six-state automatic Save')
        paused = h.input_state()
        need(not paused['enabled'] and paused['paused'] == 1 and all(int(p, 16) == 0 for p in paused['handlers']),
             'actual native pause must clear handlers/enable before Save')
        need(h.complete() == ['Root', 'Motor', 'Game', 'Strategy', 'User'], 'same User after native pop')
        restored = h.input_state()
        need(restored['phase'] == phase, 'native lifecycle preserves phase, does not force phase2')
        if phase == 2:
            need(restored['enabled'] and restored['paused'] == 0, 'native phase2 resume restores enable/updater')
            need(restored['handlers'][0] == hex(h.input + 0x2B0) and restored['handlers'][2] == hex(h.input + 0x330),
                 'actual native inline callable containers rebound')
            need(h.readq(h.input + 0x330 + 8) == h.user, 'native retained callback captures exact User')
            need(restored['panel_refresh'] == 1, 'native resume publishes panel refresh')
        else:
            need(not restored['enabled'] and restored['paused'] == 1, 'nonplanning phase is not made planning by pop')
        snapshots.append(dict(generation=generation, paused=paused, restored=restored))
    need(not any(row['state'] == 'User' and row['method'] in ('destroy', 'finalize') for row in h.callbacks),
         'existing User lifetime retained')
    methods = [e['method'] for e in h.native_events]
    need(methods.count('pause') == 2 and methods.count('resume') == 2, 'two actual lifecycle pairs')
    need(all(e['user'] == hex(h.user) for e in h.native_events), 'all native lifecycle callbacks retain same User')
    need(sum(s['label'] == 'selection clear business' for s in h.services) == (2 if selected else 0),
         'selected objects route to unresolved business; idle path avoids it')
    need({0x3F5920, 0xC020, 0x3F5530, 0x3F7710, 0x3F7A70} <= set(h.visits), 'native callbacks executed')
    if phase == 2:
        need({0x3DF8B0, 0x3DF670, 0x404AA0, 0x327900, 0x500320, 0x8F50, 0x13E90,
              0x4F9AF0, 0x402F60} <= set(h.visits),
             'native callback storage and enable paths executed')
    return dict(case=('selected-' if selected else 'idle-')+'phase'+str(phase)+'-two-save-lifecycles',
                result='PASS', snapshots=snapshots, native_events=h.native_events, services=h.services,
                native_instruction_count=len(h.visits), native_rvas=sorted(set(h.visits)),
                other_callbacks=h.callbacks, serializer_executed=False, actual_os_threads=False,
                selected_business_is_double=selected, production_permit=False)
