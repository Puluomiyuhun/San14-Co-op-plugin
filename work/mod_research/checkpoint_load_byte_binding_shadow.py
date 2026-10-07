"""Offline raw-load boundary and Title handoff regression; no game access."""
from datetime import datetime
import hashlib
import json
import struct

from checkpoint_push_native_chain import ChainHarness, ROOT, BASE, MEM, sso
from save_return_shadow_base import d
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *

NAME = 'mppush01.s14'
SHA = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
SIZE = 274880
ARCHIVE = ROOT / 'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'


def ascii_at(h, address):
    return bytes(h.u.mem_read(address, 96)).split(b'\0', 1)[0].decode('ascii')


def raw_identity_ok(snapshot):
    """Mechanical predicate only; caller must separately bind the load transaction."""
    return (snapshot['rva'] == '0x3a9227' and snapshot['parent_return_rva'] == '0x2f77cf'
            and snapshot['filename'] == NAME and snapshot['mode'] == 1
            and snapshot['requested'] == snapshot['logical_length'] == snapshot['eax_signed'] == SIZE
            and snapshot['cursor'] == snapshot['buffer']
            and snapshot['end'] - snapshot['buffer'] == SIZE
            and snapshot['sha256'] == SHA)


def stream_case(label, payload, read_return, filename=NAME, size=SIZE, caller=0x2F77CF):
    h = ChainHarness()
    h.u.mem_map(MEM + 0x200000, 0x80000)
    stream, name = MEM + 0x1A0000, MEM + 0x1A1000
    allocator, allocvt = MEM + 0x1A2000, MEM + 0x1A3000
    holder, storage, vt = MEM + 0x1B0000, MEM + 0x1B1000, MEM + 0x1B2000
    context_stub, size_stub, read_stub, alloc_stub = [MEM + 0x1C1000 + i * 0x1000 for i in range(4)]
    buffer = MEM + 0x200000
    h.u.mem_write(stream, bytes(24) + struct.pack('<Q', 15))
    h.u.mem_write(name, sso(filename))
    h.putq(allocator, allocvt)
    h.putq(allocvt + 0x28, alloc_stub)
    h.putq(BASE + 0x123CB28, context_stub)
    h.putq(holder, storage)
    h.putq(storage, vt)
    h.putq(vt + 0x78, size_stub)
    h.putq(vt + 8, read_stub)
    h.stubs[BASE + 0x18FB0] = lambda: h.ret(MEM + 0x1B5000)
    h.stubs[BASE + 0x838070] = lambda: h.ret(allocator)
    h.stubs[context_stub] = lambda: h.ret(holder)
    h.stubs[size_stub] = lambda: h.ret(size)
    h.stubs[alloc_stub] = lambda: h.ret(buffer)
    for rva in (0x3AA730, 0x3AA6A0, 0x3A5B60):
        h.stubs[BASE + rva] = lambda: h.ret(0)
    def read():
        assert h.reg(UC_X86_REG_R8) == buffer and h.reg(UC_X86_REG_R9) == size
        if read_return > 0:
            h.u.mem_write(buffer, payload[:min(size, read_return)])
        h.ret(read_return & 0xFFFFFFFF)
    h.stubs[read_stub] = read
    snapshots = []
    def observe(u, address, length, data):
        if address != BASE + 0x3A9227:
            return
        # Read registers/memory only; this observer does not change the VM state.
        at = h.reg(UC_X86_REG_RDI)
        eax = h.reg(UC_X86_REG_RAX) & 0xFFFFFFFF
        snapshots.append(dict(rva='0x3a9227', parent_return_rva=hex(h.readq(h.reg(UC_X86_REG_RSP) + 0x48) - BASE),
            filename=h.read_sso(at), mode=h.read32(at + 0x20), requested=h.read32(at + 0x24),
            logical_length=h.read32(at + 0x28), buffer=h.readq(at + 0x40), cursor=h.readq(at + 0x30),
            end=h.readq(at + 0x38), eax_signed=eax - (1 << 32) if eax & (1 << 31) else eax,
            sha256=hashlib.sha256(h.u.mem_read(buffer, size)).hexdigest()))
    h.u.hook_add(UC_HOOK_CODE, observe)
    def setup(sp):
        h.putq(sp + 0x20, 0)
        h.putq(sp + 0x28, 0x7D000)
        h.putq(sp + 0x30, 0xFFFFFFFF)
    # This is the real archive CALL instruction, giving the real parent return.
    # We stop before the archive's success branch or any parser/world update.
    h.run(0x2F77CA, stop=BASE + 0x2F77CF, args=(stream, name, 1, 0), setup=setup)
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    if caller != 0x2F77CF:
        # Explicitly synthetic mismatch of an otherwise valid observed snapshot.
        snapshot = dict(snapshot, parent_return_rva=hex(caller))
    native_success = bool(h.reg(UC_X86_REG_RAX) & 0xFF)
    matched = raw_identity_ok(snapshot)
    assert native_success == (read_return != 0)
    assert matched == (label == 'exact_archived_bytes')
    assert 0x2F77D7 not in h.visits and 0x2E7D30 not in h.visits
    return dict(case=label, result='PASS', native_wrapper_success=native_success,
                mechanical_full_byte_identity=matched, observed=snapshot, native_instructions=len(h.visits),
                actual_Steam_read=False, world_deserialization_executed=False)


def title_case(slot, replace):
    h = ChainHarness()
    title, force_a, person_a, force_b, person_b = [MEM + 0x1A0000 + i * 0x1000 for i in range(5)]
    h.put32(title + 0x478, 0xFFFFFFFF)
    h.put32(title + 0x47C, slot & 0xFFFFFFFF)
    h.u.mem_write(force_a + 0x10, struct.pack('<H', 666))
    h.u.mem_write(force_b + 0x10, struct.pack('<H', 952))
    h.putq(h.root + 0x148 + 666 * 8, person_a)
    selected = []
    def select():
        selected.append('source_world_force')
        h.ret(force_a)
    h.stubs[BASE + 0x2F21E0] = select
    h.stubs[BASE + 0x2F2BB0] = lambda: h.ret(int(h.reg(UC_X86_REG_RCX) in (force_a, person_a)))
    h.run(0x4BDD90, args=(title,))
    initial_pair = [h.readq(title + off) for off in (0x4A0, 0x4A8)]
    assert initial_pair == ([force_a, person_a] if slot >= 0 else [0, 0])
    calls = []
    h.stubs[BASE + 0x509460] = lambda: h.ret(title)
    h.stubs[BASE + 0x39C260] = lambda: h.ret(0)
    h.stubs[BASE + 0x3A0690] = lambda: h.ret(0)
    def initialize():
        calls.append({'person': h.reg(UC_X86_REG_RCX), 'caller_rva': hex(h.readq(h.reg(UC_X86_REG_RSP)) - BASE)})
        h.ret(0)
    h.stubs[BASE + 0x2FC850] = initialize
    boundaries = []
    def pair_handoff(u, address, size, data):
        if address == BASE + 0x4DA3B2:
            boundaries.append(hex(address - BASE))
            assert h.reg(UC_X86_REG_RAX) == title
            if replace:
                # VM-only substitution of a fixture pair. This is not live code
                # and does not stand in for actual ID/ownership/world guards.
                h.putq(title + 0x4A0, force_b)
                h.putq(title + 0x4A8, person_b)
    h.u.hook_add(UC_HOOK_CODE, pair_handoff)
    h.run(0x4DA390)
    expected_person = person_b if replace else person_a
    assert calls == ([{'person': expected_person, 'caller_rva': '0x4da3be'}] if slot >= 0 else [])
    return {'case': 'title_slot_and_identity_argument', 'result': 'PASS', 'title_slot': slot,
            'VM_pair_replaced': replace and bool(boundaries), 'native_initializer_calls': calls,
            'slot_negative_skips_handoff_boundary': slot < 0 and not boundaries,
            'native_initializer_body_executed': False, 'native_instructions': len(h.visits)}


def main():
    data = ARCHIVE.read_bytes()
    assert len(data) == SIZE and hashlib.sha256(data).hexdigest() == SHA
    changed = bytearray(data)
    changed[-1] ^= 1
    rows = [stream_case('exact_archived_bytes', data, SIZE),
            stream_case('short_read_nonzero', data, 1),
            stream_case('negative_read_nonzero', data, -1),
            stream_case('zero_read', data, 0),
            stream_case('different_full_payload', bytes(changed), SIZE),
            stream_case('wrong_filename', data, SIZE, filename='mpckpt01.s14'),
            stream_case('wrong_native_parent_snapshot', data, SIZE, caller=0x837005),
            stream_case('wrong_length', data, SIZE - 1, size=SIZE - 1)]
    rows += [title_case(-1, True), title_case(63, False), title_case(63, True)]
    report = {'schema': 'san14.checkpoint-load-byte-boundary-shadow.v1', 'result': 'PASS', 'cases': rows,
              'captured_image_sha256': hashlib.sha256(d.image).hexdigest(), 'archived_file_sha256': SHA,
              'scope': 'Copied native 2F77CA CALL and 3A90C0 open/read path; Steam and allocator methods are VM stubs. '
                       'Copied Title 4BDD90/4DA390; force selection, validity, initializer body and 39C260/3A0690 tail services are explicit stubs.',
              'boundary': {'raw_read_return_rva': '0x3A9227', 'expected_archive_return_rva': '0x2F77CF',
                           'parent_return_at_boundary': '[RSP+0x48]', 'stream_register': 'RDI', 'byte_count_register': 'EAX',
                           'mode_offset': '0x20', 'size_offset': '0x24', 'length_offset': '0x28',
                           'cursor_offset': '0x30', 'end_offset': '0x38', 'buffer_offset': '0x40'},
              'limitations': ['This validates mechanical capture of the actual archive read buffer, not a live B load.',
                  'A raw-byte mismatch occurs after prior native world cleanup; rollback is not established.',
                  'Filename/caller/hash do not replace before-request metadata/slot binding or per-worker observation.',
                  'Synthetic slot63 is not a chosen live slot; only a nonnegative Title-slot gate is demonstrated.',
                  'The actual identity initializer is not executed here; prior real switch evidence is separate.',
                  'No proof of complete world equivalence, RNG preservation, economic equality or hidden-menu experience.'],
              'game_access': False, 'Steam_API_called': False, 'live_installer_created': False,
              'load_authorized': False, 'room_ready': False}
    output = ROOT / ('checkpoint_load_byte_binding_shadow_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'result': 'PASS', 'cases': len(rows), 'path': str(output), 'game_access': False}))


if __name__ == '__main__':
    main()
