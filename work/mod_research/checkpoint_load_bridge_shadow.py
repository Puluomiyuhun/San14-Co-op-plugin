"""Offline virtual-call boundary proof. No process/API/install access.

The VM bridge is an explicit Python surrogate, not a new production bridge ABI
proof. Real captured worker dispatch, leaf callable, Load Update and Title
callback code execute; the operating system, deserializer and UI are stubs.
"""
from datetime import datetime
import hashlib
import json
import struct

from checkpoint_push_native_chain import ChainHarness, ROOT, BASE, MEM, sso
from checkpoint_load_byte_binding_shadow import ARCHIVE, NAME, SHA, SIZE
from save_return_shadow_base import d
from unicorn.x86_const import *

THREAD_VT = 0x138E8C0
RAW_VT_RETURN = 0x3A9227
WORKER_RETURN = 0x834D9B
TOKEN = 0x12345678


def read_match(s):
    return (s['cookie'] == TOKEN and s['current_thread'] == s['worker_thread']
            and s['worker_function'] == 0x508B40 and s['callable_owned']
            and s['storage_exact'] and s['caller'] == RAW_VT_RETURN
            and s['parent'] == 0x2F77CF and s['filename'] == NAME
            and s['requested'] == s['returned_signed'] == SIZE
            and s['sha256'] == SHA and s['matched_reads_before'] == 0)


def static_assertions():
    q = lambda p: struct.unpack_from('<Q', d.image, p)[0] - BASE
    vtables = {
        'CLoadState': {'rva': 0x12DBD68, 'methods': {8: 0x665CD0, 0x10: 0x497110, 0x18: 0x495150, 0x28: 0x4A85C0}},
        'thread_function_callable': {'rva': THREAD_VT, 'methods': {0x10: 0x4FABC0}},
        'Title_load_completion_callable': {'rva': 0x12EA4D0, 'methods': {0x10: 0x4FAC30}},
    }
    for item in vtables.values():
        assert all(q(item['rva'] + off) == fun for off, fun in item['methods'].items())
    expected = {0x4FABC0: 'jmp qword ptr [rcx + 8]',
        0x834D88: 'mov rcx, qword ptr [rbx + 0x48]',
        0x834D98: 'call qword ptr [rax + 0x10]',
        0x3A9224: 'call qword ptr [rax + 8]',
        0x497131: 'call qword ptr [rax + 0x10]',
        0x4FAC37: 'jmp 0x4cc690',
        0x4CC6A2: 'call 0x4bdd90', 0x4CC6AA: 'call 0x4bee50',
        0x4BEE8C: 'lea rdx, [rip + 0x1b4fd]',
        0x4DA2BE: 'lea rdx, [rip + 0x2e87b]',
        0x4F7074: 'call 0x834bc0', 0x4F7079: 'mov dword ptr [rbx + 0x470], 3',
        0x4DA3B9: 'call 0x2fc850'}
    rows = []
    for rva, text in expected.items():
        i = next(d.decoder.disasm(d.image[rva:rva+15], rva))
        assert i.mnemonic + ' ' + i.op_str == text, (hex(rva), i.op_str)
        rows.append({'rva': hex(rva), 'instruction': text, 'bytes': i.bytes.hex()})
    return {'vtables': vtables, 'instructions': rows}


def raw_read_case(label, returned=SIZE, mutate=False, bad=None):
    h = ChainHarness()
    h.u.mem_map(MEM + 0x200000, 0x80000)
    stream, name, allocator, allocvt = [MEM + 0x1A0000 + i * 0x1000 for i in range(4)]
    holder, storage, vt = [MEM + 0x1B0000 + i * 0x1000 for i in range(3)]
    get, sizefn, readbridge, allocfn = [MEM + 0x1C1000 + i * 0x1000 for i in range(4)]
    buffer = MEM + 0x200000
    payload = bytearray(ARCHIVE.read_bytes())
    if mutate:
        payload[-1] ^= 1
    h.u.mem_write(stream, sso(''))
    h.u.mem_write(name, sso(NAME))
    h.putq(allocator, allocvt); h.putq(allocvt + 0x28, allocfn)
    h.putq(BASE + 0x123CB28, get); h.putq(holder, storage); h.putq(storage, vt)
    h.putq(vt + 0x78, sizefn); h.putq(vt + 8, readbridge)
    h.stubs[BASE + 0x18FB0] = lambda: h.ret(MEM + 0x1B5000)
    h.stubs[BASE + 0x838070] = lambda: h.ret(allocator)
    h.stubs[get] = lambda: h.ret(holder)
    h.stubs[sizefn] = lambda: h.ret(SIZE)
    h.stubs[allocfn] = lambda: h.ret(buffer)
    for r in (0x3AA730, 0x3AA6A0, 0x3A5B60):
        h.stubs[BASE + r] = lambda: h.ret(0)
    rows = []
    original_calls = []
    def read():
        sp = h.reg(UC_X86_REG_RSP)
        args = [h.reg(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)]
        assert args[0] == storage and args[2:] == [buffer, SIZE]
        original_calls.append(args)
        if returned > 0:
            h.u.mem_write(buffer, bytes(payload[:min(returned, SIZE)]))
        raw_rax = 0xA5A55A5A00000000 | (returned & 0xFFFFFFFF)
        raw_xmm0 = 0x112233445566778899AABBCCDDEEFF00
        h.u.reg_write(UC_X86_REG_XMM0, raw_xmm0)
        snap = dict(cookie=TOKEN, current_thread=7, worker_thread=7,
            worker_function=0x508B40, callable_owned=True, storage_exact=args[0] == storage,
            caller=h.readq(sp)-BASE, parent=h.readq(sp+0x50)-BASE,
            filename=bytes(h.u.mem_read(args[1], len(NAME))).decode(),
            requested=args[3], returned_signed=returned,
            sha256=hashlib.sha256(h.u.mem_read(buffer, SIZE)).hexdigest(), matched_reads_before=0)
        if bad:
            snap.update(bad)
        rows.append({'entry_rsp_parent_offset': '0x50', 'snapshot': snap,
            'matched': read_match(snap), 'original_rax': hex(raw_rax), 'original_xmm0': hex(raw_xmm0)})
        h.ret(raw_rax)
    h.stubs[readbridge] = read
    def setup(sp):
        h.putq(sp+0x20, 0); h.putq(sp+0x28, 0x7D000); h.putq(sp+0x30, 0xFFFFFFFF)
    h.run(0x2F77CA, stop=BASE+0x2F77CF, args=(stream, name, 1, 0), setup=setup)
    assert len(original_calls) == len(rows) == 1
    assert rows[0]['matched'] == (label == 'exact')
    assert bool(h.reg(UC_X86_REG_RAX) & 0xFF) == (returned != 0)
    assert h.reg(UC_X86_REG_XMM0) == 0x112233445566778899AABBCCDDEEFF00
    return {'case': 'raw_vtable_'+label, 'result': 'PASS', 'native_read_calls': 1,
        'evidence': rows[0], 'native_instructions': len(h.visits),
        'scope': 'Actual archive CALL and native stream wrapper; FileRead original and bridge are explicit VM surrogates. Observer preserves return; it does not abort mismatch.'}


def thread_dispatch(h, thread, fn, before=None):
    call = thread + 0x10
    h.putq(thread + 0x48, call); h.putq(call, BASE+THREAD_VT); h.putq(call+8, BASE+fn)
    bridge, after = MEM+0x1FE000, MEM+0x1FE100
    h.putq(BASE+THREAD_VT+0x10, bridge)
    records = []
    def enter():
        sp = h.reg(UC_X86_REG_RSP)
        assert h.reg(UC_X86_REG_RCX) == h.readq(thread+0x48) == call
        ret = h.readq(sp)
        assert ret == BASE+WORKER_RETURN
        record = {'callable': hex(call), 'thread_object': hex(thread), 'function_rva': hex(fn),
            'caller_rva': hex(ret-BASE), 'original_calls': 1}
        records.append(record)
        if before:
            before()
        def leave():
            record['returned_rax'] = hex(h.reg(UC_X86_REG_RAX))
            record['returned_xmm0'] = hex(h.reg(UC_X86_REG_XMM0))
            h.u.reg_write(UC_X86_REG_RIP, ret)
        h.stubs[after] = leave
        h.putq(sp, after)
        h.u.reg_write(UC_X86_REG_RIP, BASE+0x4FABC0)
    h.stubs[bridge] = enter
    h.run(0x834D88, stop=BASE+WORKER_RETURN,
        setup=lambda sp: h.u.reg_write(UC_X86_REG_RBX, thread))
    assert len(records) == 1 and 0x4FABC0 in h.visits
    return records[0]


def load_worker_case():
    h = ChainHarness()
    load = MEM+0x1A0000
    h.put32(load+0x470, 1)
    h.put32(BASE+0x201ECD0, 63); h.put32(BASE+0x201ECD4, 0); h.put32(BASE+0x201ECD8, 0)
    h.u.mem_write(BASE+0x201ECE0, sso(NAME))
    h.putq(BASE+0x1A38F30, 0)
    created = []
    def create():
        created.append((h.reg(UC_X86_REG_RCX), h.reg(UC_X86_REG_RDX)))
        h.ret(0)
    h.stubs[BASE+0x833CB0] = create
    h.stubs[BASE+0x194A90] = lambda: h.ret(0)
    h.stubs[BASE+0x509640] = lambda: h.ret(1)
    h.stubs[BASE+0x50C710] = lambda: h.ret(0)
    h.putq(BASE+0x1A38F30, 0)
    h.run(0x4A85C0, args=(load,))
    assert created == [(load+0x478, BASE+0x508B40)]
    assert h.read32(load+0x470) == 2 and h.read32(BASE+0x201EC08) == 0
    deserialize = []
    def deserial():
        deserialize.append((h.reg(UC_X86_REG_RCX), h.reg(UC_X86_REG_RDX), h.reg(UC_X86_REG_R8)))
        h.ret(1)
    h.stubs[BASE+0x2EE4A0] = deserial
    h.stubs[BASE+0x24A570] = lambda: h.ret(0xFEEDBEEFDEAD1234)
    worker = thread_dispatch(h, load+0x478, 0x508B40)
    assert len(deserialize) == 1 and deserialize[0][:2] == (h.root, 63)
    assert h.read32(BASE+0x201EC08) == 1
    joins = []
    h.stubs[BASE+0x834BC0] = lambda: (joins.append(h.reg(UC_X86_REG_RCX)), h.ret(0))
    h.run(0x4A85C0, args=(load,))
    assert h.read32(load+0x470) == 3 and joins == [load+0x478]
    return {'case': 'native_load_update_worker_join', 'result': 'PASS', 'worker': worker,
        'created_thread_offset': '0x478', 'native_worker_result': 1, 'phase_after_join': 3,
        'join_arguments': list(map(hex, joins)), 'native_instructions': len(h.visits),
        'scope': 'Actual Load phase1/2, 4DA240, 508B40 and join control flow; OS thread creation/join and world deserialization are explicit stubs.'}


def title_worker_case(replace):
    h = ChainHarness()
    title, force_a, person_a, force_b, person_b, callback, arg = [MEM+0x1A0000+i*0x1000 for i in range(7)]
    h.put32(title+0x478, 0xFFFFFFFF); h.put32(title+0x47C, 63)
    h.putq(callback, BASE+0x12EA4D0); h.putq(callback+8, title); h.putq(arg, h.save)
    h.u.mem_write(force_a+0x10, struct.pack('<H',666)); h.putq(h.root+0x148+666*8,person_a)
    h.put32(BASE+0x201EC08,1)
    h.stubs[BASE+0x2F21E0] = lambda: h.ret(force_a)
    h.stubs[BASE+0x2F2BB0] = lambda: h.ret(1)
    ui, vt = MEM+0x1B0000, MEM+0x1B1000
    h.putq(title+0x4B8,ui);h.putq(ui,vt)
    h.stub(vt,0xC0,lambda:h.ret(0),'title_ui')
    created=[]
    def create():
        created.append((h.reg(UC_X86_REG_RCX),h.reg(UC_X86_REG_RDX)));h.ret(0)
    h.stubs[BASE+0x833CB0]=create
    h.stubs[BASE+0x50C710]=lambda:h.ret(0)
    h.run(0x4FAC30,args=(callback,arg))
    assert created==[(title+0x520,BASE+0x4DA390)]
    assert [h.readq(title+x) for x in (0x4A0,0x4A8)]==[force_a,person_a]
    assert h.read32(title+0x470)==15
    initializers=[]
    h.stubs[BASE+0x509460]=lambda:h.ret(title)
    def init():
        initializers.append(h.reg(UC_X86_REG_RCX));h.ret(0)
    h.stubs[BASE+0x2FC850]=init
    h.stubs[BASE+0x39C260]=lambda:h.ret(MEM+0x1B2000)
    h.stubs[BASE+0x3A0690]=lambda:h.ret(0xAA55FEEDCAFEBEEF)
    def before():
        assert not initializers
        assert [h.readq(title+x) for x in (0x4A0,0x4A8)]==[force_a,person_a]
        if replace:
            h.putq(title+0x4A0,force_b);h.putq(title+0x4A8,person_b)
    worker=thread_dispatch(h,title+0x520,0x4DA390,before)
    assert initializers==[person_b if replace else person_a]
    return {'case':'title_worker_before_identity_'+str(replace),'result':'PASS','worker':worker,
        'source_pair_selected_before_worker':True,'initializer_person':hex(initializers[0]),
        'initializer_calls':1,'replacement_is_fixture_only':replace,'native_instructions':len(h.visits),
        'scope':'Actual 4FAC30/4CC690/4BDD90/4BEE50 then 834D88 virtual invocation/4FABC0/4DA390. OS/UI, validity/force lookup and 2FC850 initializer body are explicit stubs; slot63 is synthetic.'}


def main():
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==SHA
    static=static_assertions()
    rows=[raw_read_case('exact'),raw_read_case('short',returned=1),
          raw_read_case('negative',returned=-1),raw_read_case('zero',returned=0),
          raw_read_case('payload',mutate=True)]
    for name,bad in [('no_worker_cookie',{'cookie':0}),('foreign_thread',{'current_thread':8}),
        ('other_worker',{'worker_function':0x4DA390}),('unowned_callable',{'callable_owned':False}),
        ('other_storage',{'storage_exact':False}),('other_callsite',{'caller':0x837000}),
        ('other_archive_parent',{'parent':0x837005}),('other_name',{'filename':'mpckpt01.s14'}),
        ('duplicate',{'matched_reads_before':1})]:
        rows.append(raw_read_case(name,bad=bad))
    rows += [load_worker_case(),title_worker_case(False),title_worker_case(True)]
    out={'schema':'san14.checkpoint-load-virtual-bridge-shadow.v1','result':'PASS','cases':rows,
        'static':static,'image_sha256':hashlib.sha256(d.image).hexdigest(),'archive_sha256':SHA,
        'game_access':False,'Steam_API_called':False,'live_installer_created':False,
        'production_ABI_bridge_executed':False,'scope':'VM virtual-call candidates and binding mechanics, not a production loader or complete-world proof.'}
    path=ROOT/('checkpoint_load_bridge_shadow_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'path':str(path),'game_access':False}))


if __name__=='__main__':main()
