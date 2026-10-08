"""Read-only report-block control-flow audit; never a native publisher/permit.

The original 19-byte block executes in Unicorn. Control-flow decisions and its
external flush callee are explicitly models. Separate unchanged predecessor
executions cover real archived flush/insert/clear instructions.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import itertools
import json
import os
import sys

import a_save_early_audit as predecessor

EARLY_SHA = '90738e6ae318ffbb4252d1629a6f819ea86f72cb2e6de1162844bdda1636adb4'
HERE = Path(__file__).resolve().parent


def require(ok, why):
    if not ok:
        raise AssertionError(why)


def block(raw, policy, flag, queued):
    """Execute original cmp/branch/call/clear; policy/callee remain models."""
    import unicorn as uc
    from unicorn import x86_const as x
    base, user, stack = 0x140000000, 0x50000000, 0x60000000
    begin, after_call, end = 0x3F9BA8, 0x3F9BB5, 0x3F9BBB
    m = uc.Uc(uc.UC_ARCH_X86, uc.UC_MODE_64)
    m.mem_map(base + 0x3F9000, 0x1000)
    m.mem_map(user, 0x1000)
    m.mem_map(stack, 0x1000)
    m.mem_write(base + begin, raw[begin:end])
    m.mem_write(user + 0x660, flag.to_bytes(4, 'little'))
    m.reg_write(x.UC_X86_REG_RSI, user)
    m.reg_write(x.UC_X86_REG_RBP, 0)  # Actual 3F9B9C xor ebp,ebp precondition.
    m.reg_write(x.UC_X86_REG_RSP, stack + 0x800)
    queue = [f'pending-{i}' for i in range(queued)]
    calls, writes, trace = [], [], []

    def step(machine, address, size, unused):
        rva = address - base
        trace.append(hex(rva))
        if rva == begin and policy == 'whole-block-defer':
            machine.reg_write(x.UC_X86_REG_RIP, base + end)
        elif rva == 0x3F9BB0:
            if policy != 'call-only-skip':
                calls.append('explicit-flush-double')
                queue.clear()
            machine.reg_write(x.UC_X86_REG_RIP, base + after_call)

    def write(machine, access, address, size, value, unused):
        writes.append(dict(offset=hex(address - user), size=size, value=value))

    m.hook_add(uc.UC_HOOK_CODE, step)
    m.hook_add(uc.UC_HOOK_MEM_WRITE, write)
    m.emu_start(base + begin, base + end, count=20)
    require(m.reg_read(x.UC_X86_REG_RIP) == base + end, 'block continuation lost')
    require(m.reg_read(x.UC_X86_REG_RSI) == user and
            m.reg_read(x.UC_X86_REG_RBP) == 0 and
            m.reg_read(x.UC_X86_REG_RSP) == stack + 0x800,
            'modeled branch did not preserve relevant registers/stack')
    return dict(policy=policy, before=dict(flag=flag, queue_count=queued),
                after=dict(flag=int.from_bytes(m.mem_read(user + 0x660, 4), 'little'),
                           queue_count=len(queue)),
                instructions=trace, actual_user_writes=writes,
                modeled_callees=calls, pending_values=queue,
                native_owner=False, native_bridge=False)


def control_flow_cases(raw):
    rows = []
    for flag, queued in ((0, 0), (1, 0), (1, 1), (0, 1)):
        r = block(raw, 'whole-block-defer', flag, queued)
        require(r['before'] == r['after'] and not r['actual_user_writes'] and
                not r['modeled_callees'], 'whole-block deferral lost pending data')
        rows.append(dict(case=f'whole-block-{flag}-{queued}', result='PASS', **r))
    r = block(raw, 'call-only-skip', 1, 1)
    require(r['after'] == dict(flag=0, queue_count=1) and len(r['actual_user_writes']) == 1,
            'wrong-call-only counterexample not reproduced')
    rows.append(dict(case='call-only-skip-loses-trigger', result='PASS',
                     meaning='counterexample reproduced, never a valid implementation', **r))
    r = block(raw, 'transparent', 1, 1)
    require(r['after'] == dict(flag=0, queue_count=0) and len(r['modeled_callees']) == 1,
            'transparent block did not run flush double and native clear')
    rows.append(dict(case='transparent-native-clear', result='PASS', **r))
    # Explicitly replay retained diagnostic values after release. This proves
    # only a model property, not that the real source owns release/lifetime.
    retained = block(raw, 'whole-block-defer', 1, 1)
    replay = block(raw, 'transparent', **{
        'flag': retained['after']['flag'], 'queued': retained['after']['queue_count']})
    require(replay['after'] == dict(flag=0, queue_count=0), 'deferred model lost replay')
    rows.append(dict(case='model-release-retains-work', result='PASS',
                     deferred=retained, released=replay, native_release=False))
    return rows


def early_epilogue(raw, variant):
    """Candidate earlier whole-tail cut; archived prolog/epilog actually run."""
    import capstone as cs
    import unicorn as uc
    from unicorn import x86_const as x
    base, user, stack = 0x140000000, 0x50000000, 0x60001008
    m = uc.Uc(uc.UC_ARCH_X86, uc.UC_MODE_64)
    m.mem_map(base + 0x3F9000, 0x2000)
    m.mem_map(user, 0x2000)
    m.mem_map(stack - 0x1008, 0x3000)
    m.mem_write(base + 0x3F9B00, raw[0x3F9B00:0x3FA0B4])
    def put(at, value, n=4):
        m.mem_write(at, value.to_bytes(n, 'little'))
    def get(at, n=4):
        return int.from_bytes(m.mem_read(at, n), 'little')
    put(user + 0x470, 2)
    put(user + 0x660, int(variant == 'pending'))
    queued = int(variant == 'pending')
    put(stack, base + 0x3FA0B4, 8)
    registers = (x.UC_X86_REG_RBX, x.UC_X86_REG_RBP, x.UC_X86_REG_R14,
                 x.UC_X86_REG_R15, x.UC_X86_REG_RSI)
    saved = [0x11, 0x22, 0x33, 0x44, 0x55]
    for reg, value in zip(registers, saved):
        m.reg_write(reg, value)
    m.reg_write(x.UC_X86_REG_RCX, user)
    m.reg_write(x.UC_X86_REG_RSP, stack)
    decoder = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_64)
    calls, writes, decisions = [], [], []
    def step(machine, address, size, unused):
        nonlocal queued
        if address == base + 0x3F9BA8:
            decisions.append('model cut 3F9BA8 -> original epilogue 3FA09F')
            machine.reg_write(x.UC_X86_REG_RIP, base + 0x3FA09F)
            return
        ins = next(decoder.disasm(bytes(machine.mem_read(address, size)), address))
        if ins.mnemonic == 'call':
            target = int(ins.op_str, 16) - base
            require(target in (0x509640, 0x15FA20, 0x16C5F0), 'unexpected call before candidate cut')
            calls.append(hex(target))
            if target == 0x16C5F0:
                if variant == 'late-pending':
                    put(user + 0x660, 1)
                    queued = 1
                elif variant == 'upstream-writer':
                    put(user + 0x1000, 7)  # Explicit modeled world-like writer.
            machine.reg_write(x.UC_X86_REG_RAX, 1 if target == 0x509640 else 0)
            machine.reg_write(x.UC_X86_REG_RIP, address + size)
    def write(machine, access, address, size, value, unused):
        if user <= address < user + 0x2000:
            writes.append(dict(offset=hex(address - user), size=size, value=value))
    m.hook_add(uc.UC_HOOK_CODE, step)
    m.hook_add(uc.UC_HOOK_MEM_WRITE, write)
    m.emu_start(base + 0x3F9B00, base + 0x3FA0B4, count=100)
    require(m.reg_read(x.UC_X86_REG_RIP) == base + 0x3FA0B4 and
            m.reg_read(x.UC_X86_REG_RSP) == stack + 8 and
            [m.reg_read(reg) for reg in registers] == saved, 'native prolog/epilog lost return state')
    require(calls == ['0x509640', '0x15fa20', '0x16c5f0'] and len(decisions) == 1,
            'earlier cut did not skip report/selection/action body')
    wanted = int(variant in ('pending', 'late-pending'))
    require(get(user + 0x660) == wanted and queued == wanted and not writes,
            'native candidate cut consumed pending or wrote User')
    require(get(user + 0x1000) == (7 if variant == 'upstream-writer' else 0),
            'upstream modeled writer counterexample lost')
    return dict(case='early-epilogue-' + variant, result='PASS',
                modeled_external_calls=calls, modeled_decisions=decisions,
                actual_user_writes=writes, flag=get(user + 0x660), queue_count=queued,
                upstream_model_write=get(user + 0x1000), archived_return=True,
                native_bridge=False, full_write_exclusion=False)


def model_cases():
    """Bounded reference schedules, explicitly NOT a production locking proof."""
    # Let an external producer and filtered clear both occur between samples.
    # The old report guard and a consumer-only branch see exactly the same end.
    schedules = []
    for producer, consumer in itertools.combinations(range(1, 5), 2):
        flag = queue = cursor = 0
        snapshots, writes = [], []
        for tick in range(6):
            if tick in (0, 5):
                snapshots.append((flag, queue, cursor))
            if tick == producer:
                flag = queue = 1
                writes.append('uncovered producer')
            if tick == consumer:
                flag = queue = 0
                writes.append('uncovered filtered consumer, cursor unchanged')
        require(snapshots == [(0, 0, 0), (0, 0, 0)] and len(writes) == 2,
                'sample ABA schedule disappeared')
        schedules.append(dict(producer_tick=producer, consumer_tick=consumer,
                              snapshots=snapshots, writes=writes))
    # A common exclusive owner would serialize admission, every writer and the
    # artifact copy. This reference records deferral without changing payload.
    events = []
    pending, deferred, held = [], [], False
    held = True
    for event in ('producer', 'consumer', 'selection-writer'):
        if held:
            deferred.append(event)
        else:
            pending.append(event)
    require(not pending and deferred == ['producer', 'consumer', 'selection-writer'],
            'common-boundary reference lost work')
    events.append(dict(point='through-artifact-copy', pending=list(pending), deferred=list(deferred)))
    held = False
    pending.extend(deferred)
    deferred.clear()
    require(not held and pending == ['producer', 'consumer', 'selection-writer'],
            'release reference reordered deferred actions')
    events.append(dict(point='after-reference-release', pending=list(pending), deferred=list(deferred)))
    return [dict(case='consumer-only-still-has-external-ABA', result='PASS',
                 meaning='six bypass schedules reproduced; no exclusion claim', schedules=schedules),
            dict(case='common-owner-reference-contract', result='PASS', events=events,
                 all_writers_assumed=True, implemented_native_boundary=False)]


def main():
    value = os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    require(value, 'Set SAN14_PRIVATE_FIXTURE_ROOT; no current game discovery')
    private = Path(value).resolve()
    sys.path.insert(0, str(private / 'python_deps'))
    run = HERE / 'a_save_report_boundary_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    paths = [Path(__file__).resolve(), HERE / 'a_save_early_audit.py',
             HERE / 'a_save_report_owner.cpp', HERE / 'a_save_action_gate.cpp']
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    sources = {p.name: digest(p) for p in paths}
    result = dict(schema='san14.a-save-report-boundary-audit.v1', result='FAIL',
                  game_access=False, publication=False, production_permit=False,
                  full_write_exclusion=False, native_owner_composed=False,
                  sources_sha256=sources, cases=[])
    try:
        require(sources['a_save_early_audit.py'] == EARLY_SHA, 'frozen predecessor changed')
        raw = (private / 'game-runtime-image.bin').read_bytes()
        require(hashlib.sha256(raw).hexdigest() == predecessor.ARCHIVE_SHA, 'archive differs')
        result['archive_sha256'] = predecessor.ARCHIVE_SHA
        for name, (a, z, wanted) in predecessor.RANGES.items():
            require(hashlib.sha256(raw[a:z]).hexdigest() == wanted, f'archive range differs: {name}')
        # These three execute complete archived User/report internals using the
        # frozen, separately documented external models, not this flush double.
        for case in ('report-one', 'report-other-owner', 'flag-zero-queued'):
            result['cases'].append(dict(kind='unchanged-archived-baseline',
                                        **predecessor.execute(raw, case)))
        result['cases'].extend(control_flow_cases(raw))
        result['cases'].extend(early_epilogue(raw, case) for case in
                               ('quiet', 'pending', 'late-pending', 'upstream-writer'))
        result['cases'].extend(model_cases())
        require(sources == {p.name: digest(p) for p in paths}, 'source changed during audit')
        result['result'] = 'PASS'
        result['count'] = len(result['cases'])
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        out = run / 'result.json'
        out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(dict(result=result['result'], count=len(result['cases']), path=str(out))))


if __name__ == '__main__':
    main()
