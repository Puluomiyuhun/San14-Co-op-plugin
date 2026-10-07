"""Copied-native metadata ownership/header tests; no game process or save writes."""
import json,struct
import private_checkpoint_load_shadow as n
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
ROOT=n.ROOT;BASE=n.BASE;MEM=n.MEM
def parser(payload,expect_ok):
    u=n.new();header=MEM+0x1000;stream=MEM+0x2000;cursor=[4];reads=[];global_writes=[]
    n.execute(u,0x2E32A0,(header,))
    u.mem_write(stream+0x20,struct.pack('<I',1));u.mem_write(stream+0x88,payload[:4])
    def read(uc):
        assert uc.reg_read(UC_X86_REG_RCX)==stream
        dst=uc.reg_read(UC_X86_REG_RDX);size=uc.reg_read(UC_X86_REG_R8)
        assert 0<size<4096
        start=cursor[0];raw=payload[start:start+size];cursor[0]+=size
        if len(raw)!=size:uc.mem_write(stream+0x50,struct.pack('<I',1));raw=raw.ljust(size,b'\0')
        uc.mem_write(dst,raw);reads.append((start,size));n.ret(uc,stream)
    def writes(uc,access,address,size,value,data):
        if BASE<=address<BASE+len(n.d.image):global_writes.append((address-BASE,size))
    watch=u.hook_add(UC_HOOK_MEM_WRITE,writes)
    result=n.execute(u,0x2FAAD0,(header,stream),{BASE+0x3A9330:read})
    u.hook_del(watch)
    ok=bool(u.reg_read(UC_X86_REG_RAX)&0xff)
    assert ok==expect_ok,(ok,expect_ok,cursor,global_writes)
    assert not global_writes and 0x2F76C0 not in result['visited'] and 0x2E7D30 not in result['visited']
    return {'check':'native_header_parser' if expect_ok else 'native_header_parser_truncated','result':'PASS','bytes_consumed':cursor[0],
            'read_calls':len(reads),'global_writes':global_writes,'header_hex':bytes(u.mem_read(header,0x150)).hex(),
            'stub_scope':'Only raw stream Read primitive 3A9330. Native 2FAAD0 and its field helpers execute; source bytes are an offline existing34 backup, not a new private checkpoint.'}
def ownership(slot,preexisting=False):
    u=n.new();manager=MEM+0x1000;head=MEM+0x2000;header=MEM+0x3000;name=MEM+0x4000;node=MEM+0x8000;old=MEM+0x9000
    u.mem_write(manager+0x10,n.q(head));u.mem_write(head,n.q(head)+n.q(head))
    n.execute(u,0x2E32A0,(header,));u.mem_write(header,b'OFFLINE-FIXTURE!!')
    u.mem_write(name,b'mpckpt01.s14\0');n.execute(u,0x511D0,(header+0x128,name,12))
    if preexisting:
        n.execute(u,0x2E32A0,(old+0x10,));u.mem_write(old,n.q(head)+n.q(head));u.mem_write(head,n.q(old)+n.q(old));u.mem_write(manager+0x18,n.q(1))
    allocations=[]
    def alloc(uc):
        allocations.append(uc.reg_read(UC_X86_REG_RCX));assert allocations==[0x160];n.ret(uc,node)
    before=bytes(u.mem_read(header,0x150))
    result=n.execute(u,0x2E0E80,(manager+0x10,head,old if preexisting else head,header),{BASE+0x3A5820:alloc})
    assert u.reg_read(UC_X86_REG_RAX)==node and n.text_at(u,node+0x138)=='mpckpt01.s14'
    assert bytes(u.mem_read(header,0x150))==before,'copy must not consume source'
    assert bytes(u.mem_read(node+0x10,0x124))==before[:0x124]
    # Execute the actual scanner's list-linking instructions, stop at next phase.
    u.reg_write(UC_X86_REG_R13,manager);u.reg_write(UC_X86_REG_R14,0xBA2E8BA2E8BA2D)
    u.reg_write(UC_X86_REG_RDI,head);u.reg_write(UC_X86_REG_RAX,node)
    n.execute(u,0x837114,stubs={BASE+0x837137:lambda uc:n.ret(uc)})
    assert n.u64(u,manager+0x18)==(2 if preexisting else 1)
    assert n.u64(u,head+8)==node and n.u64(u,(old if preexisting else head))==node
    assert not n.u64(u,manager+0x20+slot*8)
    u.reg_write(UC_X86_REG_R13,manager);u.reg_write(UC_X86_REG_RDI,slot);u.reg_write(UC_X86_REG_R12,node+0x10)
    n.execute(u,0x837315,stubs={BASE+0x83731D:lambda uc:n.ret(uc)})
    n.execute(u,0x836710,(manager,slot));assert u.reg_read(UC_X86_REG_RAX)==node+0x10
    freed=[]
    def free(uc):freed.append(uc.reg_read(UC_X86_REG_RCX));n.ret(uc)
    n.execute(u,0x836DF0,(manager,),{BASE+0x3A58B0:free})
    assert freed==([old,node] if preexisting else [node])
    assert n.u64(u,head)==head and n.u64(u,head+8)==head and n.u64(u,manager+0x18)==0
    assert bytes(u.mem_read(manager+0x20,120*8))==bytes(120*8)
    return {'check':'native_metadata_node_ownership','slot':slot,'preexisting_node':preexisting,'result':'PASS','allocation_sizes':allocations,
            'freed_node_count':len(freed),'filename':'mpckpt01.s14','source_remained_owned_by_caller':True,
            'scope':'Native ctor, SSO assignment, node allocator/copy, exact scanner link/table instructions and native clear. Allocation/free are emulator stubs. This is not native-file metadata registration in SAN14.'}
cases=[]
backup=(ROOT.parent/'mod_test/replay-checkpoint-34/svdexSC34.s14').read_bytes()
cases.append(parser(backup,True));cases.append(parser(backup[:64],False))
for slot in (63,99,109):cases.extend((ownership(slot),ownership(slot,True),n.worker(slot,'mpckpt01.s14'),n.archive(slot,'mpckpt01.s14')))
for slot in (-1,0,34,119,120,121):
    u=n.new();manager=MEM+0x1000
    if 0<=slot<120:u.mem_write(manager+0x20+slot*8,n.q(MEM+0x3000))
    n.execute(u,0x836710,(manager,slot));value=u.reg_read(UC_X86_REG_RAX)
    assert value==(MEM+0x3000 if 0<=slot<120 else 0)
    cases.append({'check':'native_metadata_slot_bounds','slot':slot,'returns_null':value==0,'result':'PASS'})
report={'schema':'san14.private-checkpoint-metadata-shadow.v1','result':'PASS','cases':cases,'game_access':False,'eligible_live_execution':False,
 'limits':['No Steam stream open/close was executed. Parser stream Read is a byte-buffer stub using an existing backup.','No private-checkpoint file or its final hash was present in this test.','No proof yet of native callback installation, concurrent container users, arbitrary native exceptions, or complete live registration/load lifecycle.']}
(ROOT/'private_checkpoint_metadata_shadow.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','cases':len(cases),'game_access':False,'eligible_live_execution':False}))
