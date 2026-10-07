"""Offline native-dispatch observation plan, decoder and archived-code exercise.

This module contains no process discovery, attachment, hook installation or game
writes. capture_tap is the read-only sampling contract for a future native
recorder: instruction taps run BEFORE the indicated instruction. The default
command executes archived dispatcher/runner instructions in Unicorn with the
existing explicit User/Windows API doubles. It grants no runtime authority.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parent
IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
# These are instruction boundaries, not functions suitable for naive onLeave.
TAPS = {
    0x50B4B3: ('new_pool_selection', 'call', '0x145b20'),
    0x50B4AE: ('existing_task_resume', 'jmp', '0x50b58c'),
    0x50B598: ('state_attached', 'lea', 'rcx, [rdi + 8]'),
    0x50B730: ('state_callable_enter', 'mov', 'qword ptr [rsp + 8], rbx'),
    0x50B785: ('user_update_return', 'mov', 'rbx, qword ptr [rsp + 0x30]'),
    0x834D9B: ('callable_return', 'mov', 'rcx, qword ptr [rbx + 8]'),
    0x834DB4: ('runner_done_store', 'call', None),
    0x50B5F9: ('parent_observed_done', 'mov', 'rax, qword ptr [rsp + 0x40]'),
    0x50B607: ('state_detached', 'call', '0x145b20'),
    0x50B632: ('dispatcher_common_tail', 'xor', 'eax, eax'),
    0x50B690: ('cooperative_yield_enter', 'push', 'rbx'),
    0x4AAF64: ('title_520_join_return', 'jmp', '0x4ab051'),
    0x4AAF89: ('title_590_join_return', 'lea', 'rax, [rbp - 0x29]'),
}
CHAIN = ('state_attached', 'state_callable_enter', 'user_update_return',
         'callable_return', 'runner_done_store', 'parent_observed_done',
         'state_detached', 'dispatcher_common_tail')


def decode_profile():
    """Verify exact captured image and decode every proposed tap offline."""
    sys.path.insert(0, str(ROOT / 'python_deps'))
    import capstone
    image = (ROOT / 'game-runtime-image.bin').read_bytes()
    if hashlib.sha256(image).hexdigest() != IMAGE_SHA:
        raise ValueError('archived_image_sha256')
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    rows = []
    for rva, (name, mnemonic, operands) in TAPS.items():
        ins = next(decoder.disasm(image[rva:rva + 15], rva))
        if ins.mnemonic != mnemonic or (operands is not None and ins.op_str != operands):
            raise ValueError(f'tap_instruction_{rva:x}: {ins.mnemonic} {ins.op_str}')
        rows.append(dict(rva=hex(rva), event=name, instruction=f'{ins.mnemonic} {ins.op_str}',
                         bytes=ins.bytes.hex(), sample_before_instruction=True))
    return rows


def capture_tap(rva, regs, read, thread_id, sequence):
    """Sample via supplied read(address,size), never via a process API.

    A future recorder must bound/filter the exact task and preserve every event
    or flag loss. This function does not install or authorize that recorder.
    Addresses are integers in this internal schema; no address is dereferenced
    by the analyzer. Title samples do not read any historical freed Load.
    """
    def q(p): return struct.unpack('<Q', read(p, 8))[0]
    def u(p): return struct.unpack('<I', read(p, 4))[0]
    row = dict(seq=sequence, rva=hex(rva), event=TAPS[rva][0], thread=thread_id)
    try:
        if rva in (0x4AAF64, 0x4AAF89):
            title = regs['rbx']
            offset = 0x520 if rva == 0x4AAF64 else 0x590
            control = title + offset
            row.update(title=title, control=control, phase=u(title + 0x470),
                       handle=q(control), critical=q(control + 8), completion=q(control + 0x60))
            return row
        if rva in (0x50B4B3, 0x50B4AE):
            row.update(state=q(q(regs['rsp'] + 0x40)), existing_worker=regs['rdi'])
            return row
        if rva in (0x50B598, 0x50B5F9, 0x50B607, 0x50B632):
            worker = regs['rdi']
            slot = q(regs['rsp'] + 0x40)
            state = q(slot)
        elif rva == 0x50B730:
            callable_ = regs['rcx']
            slot = q(q(callable_ + 8))
            state = q(slot)
            worker = q(state + 0x50)
        elif rva in (0x834D9B, 0x834DB4):
            worker = regs['rbx'] - 8
            callable_ = q(worker + 0x50)
            slot = q(q(callable_ + 8))
            state = q(slot)
        else:
            state = regs['rbx'] if rva == 0x50B785 else regs['rcx']
            worker = q(state + 0x50)
            callable_ = q(worker + 0x50)
            slot = q(q(callable_ + 8))
        callable_ = q(worker + 0x50)
        handle = q(worker + 8)
        row.update(worker=worker, control=worker + 8, state=state, slot=slot,
                   callable=callable_, callable_entry=q(q(callable_) + 0x10),
                   native_thread=u(handle + 0x10), attached=q(state + 0x50),
                   done=u(worker + 0x58), yielded=u(worker + 0x78),
                   stopped=u(worker + 0x5C))
    except Exception as error:
        row['memory_fault'] = type(error).__name__
    return row


def analyze(rows):
    """Classify one filtered task trace, not a global scheduling fence.

    Requires the independently sampled native task chain; an external 'ready'
    flag, elapsed time or empty wrapper count cannot substitute for its events.
    Resume and pool-selection markers are diagnostic only, not admission tokens.
    """
    out = dict(schema='san14.native-dispatch-handoff-analysis.v1',
               classification='INCOMPLETE', task_chain_observed=False,
               scheduler_fence=False, live_authority=False, blockers=[])
    def reject(reason):
        out['classification'] = 'REJECTED'
        out['blockers'].append(reason)
        return out
    seq = [r.get('seq') for r in rows]
    if any(type(n) is not int or n < 1 for n in seq) or seq != sorted(set(seq)):
        return reject('non_monotonic_or_duplicate_sequence')
    if any(r.get('memory_fault') for r in rows): return reject('sample_memory_fault')
    if any(r.get('lost_events', 0) for r in rows): return reject('record_loss')
    for row in rows:
        try: tap = TAPS[int(row['rva'], 16)][0]
        except (KeyError, ValueError, TypeError): return reject('unknown_tap')
        if row.get('event') != tap: return reject('event_rva_mismatch')
    task_rows = [r for r in rows if r.get('event') in CHAIN or r.get('event') == 'cooperative_yield_enter']
    if not task_rows:
        out['blockers'] = ['no_task_chain']; return out
    first = task_rows[0]
    keys = ('worker', 'control', 'state', 'slot', 'callable', 'native_thread', 'callable_entry')
    if any(type(first.get(k)) is not int or first[k] <= 0 for k in keys):
        return reject('missing_task_identity')
    parent = None
    for row in task_rows:
        if any(row.get(k) != first[k] for k in keys): return reject('task_identity_changed')
        if row.get('control') != row['worker'] + 8: return reject('control_worker_mapping')
        if row.get('stopped') != 0: return reject('stopping_worker')
        worker_event = row['event'] in ('state_callable_enter', 'user_update_return',
            'callable_return', 'runner_done_store', 'cooperative_yield_enter')
        if worker_event:
            if row.get('thread') != row['native_thread']: return reject('native_thread_mismatch')
        else:
            if not row.get('thread') or row['thread'] == row['native_thread']:
                return reject('parent_thread_invalid')
            if parent is None: parent = row['thread']
            if parent != row['thread']: return reject('parent_thread_changed')
    names = [r['event'] for r in task_rows]
    if 'cooperative_yield_enter' in names:
        out.update(classification='YIELDED_TASK_STILL_OWNED',
                   blockers=['yield_is_not_return_or_join; preserve the original task ticket'])
        return out
    if names != list(CHAIN):
        out['blockers'] = ['missing_or_duplicate_native_chain_event']; return out
    for index, row in enumerate(task_rows):
        if row.get('yielded') != 0: return reject('yielded_normal_chain')
        if row.get('done') != (1 if index >= 4 else 0): return reject('native_done_order')
        if row.get('attached') != (0 if index >= 6 else row['worker']):
            return reject('state_worker_detach_order')
    out.update(classification='ONE_STATE_TASK_RETURNED_AND_DETACHED', task_chain_observed=True,
               worker=first['worker'], state=first['state'], parent_thread=parent,
               blockers=['This proves only the observed task; not all producer/admission paths.',
                         'Bind fresh task creation versus cooperative resume before changing generation.',
                         'Require separately paired Load join and both Title worker joins.'])
    return out


def exercise():
    # Prevent the archived disassembler from parsing our CLI arguments.
    saved = sys.argv[:]
    sys.argv = sys.argv[:1]
    try:
        from checkpoint_metadata_boundary_shadow import Scheduler, BASE
        from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RBX, UC_X86_REG_RDI, UC_X86_REG_RCX
    finally:
        sys.argv = saved

    class Recorder(Scheduler):
        def __init__(self):
            self.samples = []
            super().__init__()
            self.put32(self.thread + 0x10, 202)  # Explicit native thread-id fixture.
        def hook(self, u, address, size, data):
            rva = address - BASE
            if rva in TAPS:
                regs = dict(rsp=self.reg(UC_X86_REG_RSP), rbx=self.reg(UC_X86_REG_RBX),
                            rdi=self.reg(UC_X86_REG_RDI), rcx=self.reg(UC_X86_REG_RCX))
                self.samples.append(capture_tap(rva, regs, self.u.mem_read,
                                    101 if self.role == 'parent' else 202, len(self.samples) + 1))
            super().hook(u, address, size, data)

    results = []
    for mode in ('normal', 'yield'):
        recorder = Recorder()
        recorder.start_parent(); recorder.start_worker()
        recorder.poll_parent()
        if mode == 'normal': recorder.finish_worker()
        else: recorder.yield_worker()
        recorder.poll_parent()
        result = analyze(recorder.samples)
        expected = 'ONE_STATE_TASK_RETURNED_AND_DETACHED' if mode == 'normal' else 'YIELDED_TASK_STILL_OWNED'
        assert result['classification'] == expected, result
        results.append(dict(mode=mode, samples=recorder.samples, analysis=result))
    return results


def main():
    profile = decode_profile()
    if len(sys.argv) == 3 and sys.argv[1] == '--trace':
        rows = [json.loads(line) for line in Path(sys.argv[2]).read_text(encoding='utf8').splitlines() if line.strip()]
        print(json.dumps(analyze(rows), indent=2)); return
    if len(sys.argv) != 1: raise SystemExit('usage: checkpoint_dispatch_handoff_probe.py [--trace JSONL]')
    result = dict(schema='san14.native-dispatch-handoff-exercise.v1', profile=profile,
                  image_sha256=IMAGE_SHA, game_access=False, live_authority=False,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  cases=exercise(), limits=['User Update body and Win32 APIs are doubles.',
                      'Thread IDs and process-local task memory are fixtures.',
                      'No live tap installer is provided or run; actual OS scheduling is not established.'])
    path = ROOT / ('checkpoint_dispatch_handoff_probe_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    path.write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(dict(result='PASS', native_cases=2, taps=len(profile), path=str(path))))


if __name__ == '__main__': main()
