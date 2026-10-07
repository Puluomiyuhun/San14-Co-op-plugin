"""Offline explicit-name dataflow checks in a private emulator, never SAN14.

Only the binder executes without stubs. Other checks stub all external side
effects and establish argument forwarding, not that a real save is possible.
"""
from pathlib import Path
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)];sys.argv=sys.argv[:1]
import disasm_chained as d
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
BASE=0x7ff749440000;MEM=0x300000000;STOP=MEM+0xff00
assert hashlib.sha256(d.image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
def q(value):return struct.pack('<Q',value)
def sso(value):
    value=value.encode('ascii');assert 0<len(value)<=15
    return value.ljust(16,b'\0')+q(len(value))+q(15)
def empty():return bytes(24)+q(15)
def new():
    u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(BASE,(len(d.image)+4095)&~4095);u.mem_write(BASE,d.image)
    u.mem_map(MEM,0x40000);return u
def u64(u,p):return struct.unpack('<Q',u.mem_read(p,8))[0]
def cstring(u,p):return bytes(u.mem_read(p,64)).split(b'\0',1)[0].decode('ascii')
def text_at(u,p):
    n=u64(u,p+16);cap=u64(u,p+24);assert n<=15 and cap==15
    return bytes(u.mem_read(p,n)).decode('ascii')
def ret(u,value=0):
    sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RAX,value)
    u.reg_write(UC_X86_REG_RIP,u64(u,sp));u.reg_write(UC_X86_REG_RSP,sp+8)
def execute(u,rva,args=(),stubs=None):
    stubs=stubs or {};visits=[];calls=[]
    sp=MEM+0x3fef8;u.mem_write(sp,q(STOP));u.reg_write(UC_X86_REG_RSP,sp)
    for reg,arg in zip((UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9),args):u.reg_write(reg,arg)
    def hook(uc,address,size,data):
        if address==STOP:uc.emu_stop();return
        if address in stubs:
            calls.append(hex(address-BASE) if address>=BASE else hex(address));stubs[address](uc);return
        assert BASE<=address<BASE+len(d.image),f'Unrecognized external instruction {address:#x}'
        visits.append(address-BASE)
    handle=u.hook_add(UC_HOOK_CODE,hook)
    u.emu_start(BASE+rva,STOP,count=50000);u.hook_del(handle)
    assert u.reg_read(UC_X86_REG_RIP)==STOP,'Instruction cap reached'
    return {'instructions':len(visits),'stub_calls':calls,'visited':visits}
def binder(slot,name):
    u=new();obj=MEM+0x1000
    u.mem_write(obj,struct.pack('<iI',slot,0)+sso(name)+empty())
    u.mem_write(BASE+0x201ed18,empty());u.mem_write(BASE+0x201ed38,empty())
    result=execute(u,0x2fc750,(obj,))
    assert text_at(u,BASE+0x201ed18)==name and text_at(u,obj+8)==''
    assert struct.unpack('<i',u.mem_read(BASE+0x201ed10,4))[0]==slot
    return {'check':'binder','slot':slot,'filename':name,'instructions':result['instructions'],'stubs':0,'result':'PASS'}
def worker(slot,name):
    u=new();u.mem_write(BASE+0x201ed10,struct.pack('<i',slot));u.mem_write(BASE+0x201ed18,sso(name));u.mem_write(BASE+0x201ed38,empty())
    observed={}
    def open_archive(uc):
        observed.update(filename=cstring(uc,uc.reg_read(UC_X86_REG_R8)),index=uc.reg_read(UC_X86_REG_RDX)&0xffffffff)
        ret(uc,0) # Deliberately bypass all serializer and real finalizer work.
    stubs={BASE+0x2ee740:open_archive}
    for address in (0x39c260,0x3a0690,0x39c440,0x39d500):stubs[BASE+address]=lambda uc:ret(uc)
    result=execute(u,0x508ca0,stubs=stubs)
    assert observed=={'filename':name,'index':0}
    return {'check':'worker_arguments','slot_global':slot,**observed,'stub_calls':result['stub_calls'],'result':'PASS'}
def archive_name(name):
    u=new();archive=MEM+0x1000;filename=MEM+0x2000;heap=[MEM+0x4000];observed={}
    u.mem_write(archive+0x30,empty());u.mem_write(archive+0x50,empty());u.mem_write(filename,name.encode()+b'\0')
    def alloc(uc):
        at=heap[0];heap[0]+=0x1000;ret(uc,at)
    def ctor(uc):ret(uc,uc.reg_read(UC_X86_REG_RCX))
    def open_stream(uc):
        observed.update(filename=text_at(uc,uc.reg_read(UC_X86_REG_RDX)),mode=uc.reg_read(UC_X86_REG_R8),arg4=uc.reg_read(UC_X86_REG_R9));ret(uc,1)
    stubs={BASE+0x3a5820:alloc,BASE+0x3a5120:ctor,BASE+0x3a4fc0:ctor,BASE+0x3a90c0:open_stream,BASE+0x2f7b50:lambda uc:ret(uc)}
    result=execute(u,0x2f7a10,(archive,0,filename),stubs)
    assert observed=={'filename':name,'mode':0,'arg4':0}
    assert 0x2f7abe not in result['visited'] and 0x2f7ad9 not in result['visited'] and 0x2f1650 not in result['visited']
    assert text_at(u,archive+0x50)==name
    return {'check':'archive_explicit_branch','filename':name,'standard_name_formatter_executed':False,'stub_calls':result['stub_calls'],'result':'PASS'}
def finalize(name):
    u=new();stream=MEM+0x1000;context=MEM+0x2000;storage=MEM+0x2100;vtable=MEM+0x2200
    context_stub=MEM+0x3000;write_stub=MEM+0x3100;buffer=MEM+0x5000;buffer_p=MEM+0x4000;size_p=MEM+0x4010
    payload=b'PRIVATE-FIXTURE-NOT-SAVE'
    u.mem_write(stream,sso(name));u.mem_write(stream+0x30,q(1));u.mem_write(stream+0x40,q(0))
    u.mem_write(stream+0x58,q(buffer_p));u.mem_write(stream+0x70,q(size_p))
    u.mem_write(buffer_p,q(buffer));u.mem_write(size_p,struct.pack('<I',len(payload)));u.mem_write(buffer,payload)
    u.mem_write(BASE+0x123cb28,q(context_stub));u.mem_write(context,q(storage));u.mem_write(storage,q(vtable));u.mem_write(vtable,q(write_stub))
    observed={}
    def get_context(uc):
        assert uc.reg_read(UC_X86_REG_RCX)==BASE+0x18d08b8;ret(uc,context)
    def file_write(uc):
        assert uc.reg_read(UC_X86_REG_RCX)==storage
        n=uc.reg_read(UC_X86_REG_R9)&0xffffffff
        observed.update(filename=cstring(uc,uc.reg_read(UC_X86_REG_RDX)),bytes_hex=bytes(uc.mem_read(uc.reg_read(UC_X86_REG_R8),n)).hex());ret(uc,1)
    stubs={BASE+0x3a8720:lambda uc:ret(uc),BASE+0x3a6270:lambda uc:ret(uc),context_stub:get_context,write_stub:file_write}
    result=execute(u,0x3a6a10,(stream,),stubs)
    assert observed=={'filename':name,'bytes_hex':payload.hex()}
    return {'check':'finalizer_filename_to_stub_FileWrite','filename':name,'bytes_forwarded':len(payload),'stub_calls':result['stub_calls'],'result':'PASS'}
rows=[]
for slot in (-1,0,34,49):rows.append(binder(slot,'mpcheck01.s14'));rows.append(worker(slot,'mpcheck01.s14'))
rows.extend((archive_name('mpcheck01.s14'),finalize('mpcheck01.s14')))
report={'schema':'san14.save-checkpoint-explicit-name-shadow.v1','result':'PASS','cases':rows,'game_access':False,
        'native_save_proven':False,'standard_slot_profile_changed':False,
        'scope':'Binder without external stubs; worker, archive branch and finalizer dataflow with controlled external stubs. No real serializer, Steam API, game state stack or game save file is exercised.'}
(ROOT/'save_checkpoint_explicit_name_shadow.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({'result':'PASS','cases':len(rows),'game_access':False,'native_save_proven':False}))
