"""Native queue append plus real null-reallocation branch in a private emulator."""
from pathlib import Path
from datetime import datetime
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent;sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)];sys.argv=sys.argv[:1]
import disasm_chained as d
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
BASE=0x7ff749440000;MEM=0x300000000;STOP=MEM+0x8000
assert hashlib.sha256(d.image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
assert struct.unpack_from('<Q',d.image,0x1283498+0x48)[0]==BASE+0x1479B0
q=lambda v:struct.pack('<Q',v)
def r64(u,p):return struct.unpack('<Q',u.mem_read(p,8))[0]
def ret(u,value):
    sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RAX,value);u.reg_write(UC_X86_REG_RIP,r64(u,sp));u.reg_write(UC_X86_REG_RSP,sp+8)
rows=[]
for capacity in (0,64):
    u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(BASE,(len(d.image)+4095)&~4095);u.mem_write(BASE,d.image);u.mem_map(MEM,0x30000)
    manager=MEM+0x1000;allocator=MEM+0x2000;vtable=MEM+0x3000;state=MEM+0x4000;new_storage=MEM+0x5000
    state_stub=MEM+0x8100;alloc_stub=MEM+0x8200
    u.mem_write(manager,q(allocator));u.mem_write(manager+0x28,q(allocator));u.mem_write(manager+0x30,q(0)+q(capacity)+q(new_storage if capacity else 0))
    u.mem_write(allocator,q(vtable));u.mem_write(vtable+0x40,q(state_stub));u.mem_write(vtable+0x48,q(BASE+0x1479B0));u.mem_write(vtable+0x28,q(alloc_stub))
    sp=MEM+0x2FEF8;u.mem_write(sp,q(STOP));u.reg_write(UC_X86_REG_RSP,sp);u.reg_write(UC_X86_REG_RCX,manager);u.reg_write(UC_X86_REG_RDX,BASE+0x12AA8E0);u.reg_write(UC_X86_REG_R8,0)
    visits=[];allocations=[];reallocations=[]
    def hook(uc,address,size,data):
        if address==STOP:uc.emu_stop();return
        if address==state_stub:
            assert uc.reg_read(UC_X86_REG_RCX)==allocator and uc.reg_read(UC_X86_REG_RDX)==0x4F0 and uc.reg_read(UC_X86_REG_R8)==16;ret(uc,state);return
        if address==BASE+0x4263C0:
            assert uc.reg_read(UC_X86_REG_RCX)==state and uc.reg_read(UC_X86_REG_RDX)==0;ret(uc,state);return
        if address==BASE+0x509EC0:
            assert uc.reg_read(UC_X86_REG_RCX)==manager and uc.reg_read(UC_X86_REG_RDX)==state and uc.reg_read(UC_X86_REG_R8)==BASE+0x12AA8E0;ret(uc,0);return
        if address==BASE+0x1479B0:
            reallocations.append({'old_pointer':uc.reg_read(UC_X86_REG_RDX),'new_bytes':uc.reg_read(UC_X86_REG_R8)})
        if address==alloc_stub:
            assert uc.reg_read(UC_X86_REG_RCX)==allocator and uc.reg_read(UC_X86_REG_RDX)==1024
            descriptor=uc.reg_read(UC_X86_REG_R8);assert struct.unpack('<I',uc.mem_read(descriptor,4))[0]==0x30
            allocations.append({'bytes':1024,'via_real_null_dispatch':True});ret(uc,new_storage);return
        assert BASE<=address<BASE+len(d.image),hex(address);visits.append(address-BASE)
    u.hook_add(UC_HOOK_CODE,hook);u.emu_start(BASE+0x412520,STOP,count=10000)
    assert u.reg_read(UC_X86_REG_RIP)==STOP
    assert r64(u,manager+0x30)==1 and r64(u,manager+0x38)==64 and r64(u,manager+0x40)==new_storage
    assert struct.unpack('<I',u.mem_read(new_storage,4))[0]==2 and r64(u,new_storage+8)==state
    if capacity==0:
        assert reallocations==[{'old_pointer':0,'new_bytes':1024}] and len(allocations)==1 and 0x1479CA in visits and 0x1479E6 in visits
    else:assert not reallocations and not allocations and 0x1479B0 not in visits
    rows.append({'initial_capacity':capacity,'initial_pointer_null':capacity==0,'result':'PASS','reallocation_calls':reallocations,'allocation_calls':allocations,'final_count':1,'final_capacity':64,'item_type':2,'object_matches':True,'native_instructions':len(visits)})
stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f');path=ROOT/('private_checkpoint_save_queue_shadow_'+stamp+'.json')
result={'result':'PASS','cases':rows,'game_access':False,'native_save_proven':False,
        'evidence':{'queue':'4125A9..4125EF grows (count-cap+1) rounded up to 64 items; passes old pointer to allocator+48 and stores returned pointer before append',
                    'allocator':'Captured vtable1283498+48 ->1479B0. At1479CA tests old pointer; NULL tail-calls vtable+28 allocation at1479E6.',
                    'root_readonly_observation':'Root reported allocator vtable1283498 and methods+40=8388D0,+48=1479B0 from the current process.'},
        'scope':'Actual copied 412520 and1479B0 null branch. State allocation/constructor/name registration and underlying allocate(+28) are emulator stubs. Proves native empty-vector growth/argument/data flow, not a real heap allocation or save.'}
with path.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
print(json.dumps({'result':'PASS','cases':len(rows),'evidence':str(path),'game_access':False}))
