"""Bounded archived constructor execution, with deliberately deferred OS workers.

No process discovery, game launch, current save access or installation. Service
doubles are explicit: this is a counterexample to an assumed wait guarantee,
not an observed Windows scheduling race or a production startup implementation.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import sys
import a_save_writer_scope_audit as core

P = Path(__file__).resolve().parent
SPANS = {'pool_init': (0x509580, 0x509639),
         'control_ctor': (0x833CB0, 0x833DF2),
         'thread_factory': (0x83A070, 0x83A208)}
CORE_SHA = '36885d10878f9ad5f80a3e8946c8895e020a50130b192c7fc46d20e5d4e56c05'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def execute(raw, eager):
    core.RANGES.update(SPANS)  # only this isolated audit interpreter
    v = core.VM(raw)
    v.allow = set(SPANS)
    b, a = core.BASE, core.ARENA
    manager, allocator, table = a+0x150000, a+0x151000, a+0x152000
    pool = b+0x1A24DA0
    v.put(b+0x833D70+7+0x17F21D9, manager)
    v.put(b+0x833CD5+8+0x17F158B, 1)  # existing shared counter
    v.put(manager+0x20, allocator)
    v.put(allocator, table)
    v.m.mem_write(pool, bytes(0x300))
    allocated, threads, events = [], [], []
    next_alloc = [a+0x160000]

    def allocation():
        p = next_alloc[0]
        next_alloc[0] += 0x1000
        allocated.append(p)
        v.m.mem_write(p, bytes(0x500))
        v.ret(p)

    v.put(table+0x30, b+0x2100000)
    v.model(0x2100000, 'allocator service double', allocation)

    def callable():
        # Initializer passes null callable; emulate only this empty move.
        core.need(v.get(v.reg('RCX')+0x38) == 0, 'empty callable only')
        v.put(v.reg('RDX')+0x38, 0)
        v.ret()

    v.model(0x160F0, 'empty callable container service double', callable)
    v.model(0x83A000, 'counter allocation and critical-section service double', allocation)
    v.model(0xEF9F20, 'cookie check double preserving RAX', lambda: v.ret(v.reg('RAX')))

    def copy_name():
        v.m.mem_write(v.reg('RCX'), bytes(v.m.mem_read(v.reg('RDX'), v.reg('R8'))))
        v.ret(v.reg('RCX'))

    v.model(0xF1AF70, 'name copy service double', copy_name)

    def event():
        events.append({'signaled': v.reg('R8') != 0})
        v.ret(0xE000+len(events))

    def create():
        sp = v.reg('RSP')
        core.need(v.get(sp+0x28, 4) == 4, 'native factory requests suspended creation')
        core.need(v.reg('R8') == b+0x83A930, 'native ThreadEntry address')
        tid = 100+len(threads)
        v.put(v.get(sp+0x30), tid, 4)
        threads.append(dict(handle=0xF000+tid, object=v.reg('R9'), resumed=False,
                            modeled_initial_wait=False))
        v.ret(threads[-1]['handle'])

    v.model(0xF31084, 'CRT thread-create double; child not executed', create)

    def resume():
        t = next(t for t in threads if t['handle'] == v.reg('RCX'))
        t['resumed'] = True
        t['modeled_initial_wait'] = eager
        v.ret(1)

    for slot, stub, label, fn in [
        (0x123C2C8, 0x2100100, 'event factory double', event),
        (0x123C188, 0x2100200, 'thread-priority service double', lambda: v.ret(1)),
        (0x123C1A8, 0x2100300, 'thread-resume service double', resume),
    ]:
        v.put(b+slot, b+stub)
        v.model(stub, label, fn)
    v.run(0x509580, (pool,))
    core.need(len(threads) == 4 and all(t['resumed'] for t in threads), 'four resumed workers')
    core.need([v.get(pool+0x10+i*0x80) for i in range(4)] == [t['object'] for t in threads],
              'native constructors publish their own objects')
    core.need(v.reg('RAX') == 1, 'native initializer returns success')
    core.need(sum(x['modeled_initial_wait'] for x in threads) == (4 if eager else 0),
              'explicit scheduling assumption retained')
    return dict(case='modeled-ready-before-return' if eager else 'all-children-deferred',
                result='PASS', native_instruction_count=len(v.visits),
                native_initializer_returned=True, created_suspended=4, resumed=4,
                modeled_children_at_initial_wait=4 if eager else 0,
                actual_child_instructions=0, modeled_calls=v.models,
                meaning='Native parent can return without a service proving the child reached its initial wait.')


def main():
    private = Path(os.environ['SAN14_PRIVATE_FIXTURE_ROOT']).resolve()
    sys.path.insert(0, str(private/'python_deps'))
    image = private/'game-runtime-image.bin'
    pins = {n: sha(P/n) for n in ('b_reload_cold_start_audit.py', 'a_save_writer_scope_audit.py')}
    core.need(pins['a_save_writer_scope_audit.py'] == CORE_SHA, 'frozen VM identity')
    core.need(sha(image) == core.IMAGE_SHA, 'archive identity')
    run = P/'b_reload_cold_start_audit_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    result = dict(schema='san14.cold-start-archive-audit.v1', result='FAIL', sources=pins,
                  archive_sha256=core.IMAGE_SHA, cases=[], game_access=False,
                  actual_OS_scheduling=False, production_permit=False)
    try:
        raw = image.read_bytes()
        for eager in (False, True):
            result['cases'].append(execute(raw, eager))
        core.need(all(sha(P/n) == h for n,h in pins.items()) and sha(image) == core.IMAGE_SHA,
                  'input identities unchanged')
        result['result'] = 'PASS'
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        (run/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({'result': result['result'], 'cases': len(result['cases']), 'path': str(run/'result.json')}))


if __name__ == '__main__':
    main()
