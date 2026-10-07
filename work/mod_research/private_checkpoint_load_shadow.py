"""Offline copied-native private filename ABI checks. Never opens SAN14."""
from pathlib import Path
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)];sys.argv=sys.argv[:1]
import disasm_chained as d
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
BASE=0x7ff749440000;MEM=0x300000000;STOP=MEM+0xff00
assert hashlib.sha256(d.image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
q=lambda x:struct.pack('<Q',x)
def sso(name):
    raw=name.encode('ascii');assert len(raw)<=15
    return raw.ljust(16,b'\0')+q(len(raw))+q(15)
def new():
    u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(BASE,(len(d.image)+4095)&~4095);u.mem_write(BASE,d.image)
    u.mem_map(MEM,0x40000);return u
def u64(u,p):return struct.unpack('<Q',u.mem_read(p,8))[0]
def i32(u,p):return struct.unpack('<i',u.mem_read(p,4))[0]
def text_at(u,p):
    n=u64(u,p+16);cap=u64(u,p+24);assert n<=15 and cap==15
    return bytes(u.mem_read(p,n)).decode('ascii')
def cstring(u,p):return bytes(u.mem_read(p,64)).split(b'\0',1)[0].decode('ascii')
def ret(u,value=0):
    sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RAX,value)
    u.reg_write(UC_X86_REG_RIP,u64(u,sp));u.reg_write(UC_X86_REG_RSP,sp+8)
def execute(u,rva,args=(),stubs=None):
    stubs=stubs or {};visits=[];calls=[];sp=MEM+0x3fef8
    u.mem_write(sp,q(STOP));u.reg_write(UC_X86_REG_RSP,sp)
    for reg,arg in zip((UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9),args):u.reg_write(reg,arg&0xffffffffffffffff)
    def hook(uc,address,size,data):
        if address==STOP:uc.emu_stop();return
        if address in stubs:calls.append(hex(address-BASE) if address>=BASE else hex(address));stubs[address](uc);return
        assert BASE<=address<BASE+len(d.image),f'Unrecognized external instruction {address:#x}'
        visits.append(address-BASE)
    handle=u.hook_add(UC_HOOK_CODE,hook);u.emu_start(BASE+rva,STOP,count=100000);u.hook_del(handle)
    assert u.reg_read(UC_X86_REG_RIP)==STOP,'Instruction cap reached'
    return {'instructions':len(visits),'stub_calls':calls,'visited':visits}
def binder(slot,name):
    u=new();obj=MEM+0x1000
    u.mem_write(obj,struct.pack('<iIII',slot,0,0,0)+sso(name)+bytes(8))
    u.mem_write(BASE+0x201ECE0,sso(''))
    result=execute(u,0x4BF5A0,(obj,))
    assert i32(u,BASE+0x201ECD0)==slot and i32(u,BASE+0x201ECD4)==0 and i32(u,BASE+0x201ECD8)==0
    assert text_at(u,BASE+0x201ECE0)==name and text_at(u,obj+0x10)==''
    return {'check':'native_binder_SSO','slot':slot,'filename':name,'source_string_consumed':True,'instructions':result['instructions'],'stubs':0,'result':'PASS'}
def worker(slot,name):
    u=new();u.mem_write(BASE+0x201ECD0,struct.pack('<iII',slot,0,0));u.mem_write(BASE+0x201ECE0,sso(name))
    observed={}
    def load(uc):
        raw=uc.reg_read(UC_X86_REG_RDX)&0xffffffff
        observed.update(filename=cstring(uc,uc.reg_read(UC_X86_REG_R8)),slot=raw-(1<<32) if raw&(1<<31) else raw)
        ret(uc,0) # No deserializer or post-success real-world updates execute.
    result=execute(u,0x508B40,stubs={BASE+0x2EE4A0:load})
    assert observed=={'filename':name,'slot':slot}
    assert 0x508BBB not in result['visited']
    return {'check':'worker_argument_forwarding',**observed,'stub_calls':result['stub_calls'],'result':'PASS'}
def archive(slot,name):
    u=new();obj=MEM+0x1000;filename=MEM+0x2000;heap=[MEM+0x4000];vtable=MEM+0x17000;delete_stub=MEM+0x18000
    u.mem_write(obj+0x30,sso(''));u.mem_write(obj+0x50,sso(''));u.mem_write(filename,name.encode()+b'\0')
    u.mem_write(vtable+0x78,q(delete_stub));observed={}
    def alloc(uc):p=heap[0];heap[0]+=0x1000;ret(uc,p)
    def ctor(uc):p=uc.reg_read(UC_X86_REG_RCX);uc.mem_write(p,q(vtable));ret(uc,p)
    def open_stream(uc):
        observed.update(filename=text_at(uc,uc.reg_read(UC_X86_REG_RDX)),mode=uc.reg_read(UC_X86_REG_R8),arg4=uc.reg_read(UC_X86_REG_R9));ret(uc,0)
    stubs={BASE+0x3A5820:alloc,BASE+0x3A5120:ctor,BASE+0x3A4FC0:ctor,BASE+0x3A90C0:open_stream,
           BASE+0x3A55D0:lambda uc:ret(uc),BASE+0xEF97B4:lambda uc:ret(uc),delete_stub:lambda uc:ret(uc)}
    result=execute(u,0x2F76C0,(obj,slot,filename),stubs)
    assert observed=={'filename':name,'mode':1,'arg4':0}
    assert i32(u,obj+0x20)==slot and text_at(u,obj+0x50)==name
    assert 0x2F7775 not in result['visited'] and 0x2F1650 not in result['visited']
    return {'check':'archive_explicit_filename','slot':slot,**observed,'standard_name_formatter_executed':False,'deserializer_executed':False,'stub_calls':result['stub_calls'],'result':'PASS'}
def title_identity(slot):
    u=new();title=MEM+0x1000;root=MEM+0x2000;world=MEM+0x10000;force=MEM+0x11000;person=MEM+0x12000
    u.mem_write(title+0x478,struct.pack('<ii',-1,slot));u.mem_write(BASE+0x1FCA1E0,q(root))
    # Root extent is outside the scratch block; a separate mapping preserves offsets.
    root=MEM+0x100000;u.mem_map(root,0x90000);u.mem_write(BASE+0x1FCA1E0,q(root));u.mem_write(root+0x85130,q(world))
    u.mem_write(force+0x10,struct.pack('<H',666));u.mem_write(root+0x148+666*8,q(person));selected=[]
    def select(uc):selected.append('world_force');ret(uc,force)
    def valid(uc):ret(uc,1 if uc.reg_read(UC_X86_REG_RCX) in (force,person) else 0)
    result=execute(u,0x4BDD90,(title,),{BASE+0x2F21E0:select,BASE+0x2F2BB0:valid})
    if slot>=0:assert selected and u64(u,title+0x4A0)==force and u64(u,title+0x4A8)==person
    else:assert not selected and not u64(u,title+0x4A0) and not u64(u,title+0x4A8)
    return {'check':'title_resume_slot_gate','title_slot':slot,'world_identity_selected':bool(selected),'stub_calls':result['stub_calls'],'result':'PASS'}
cases=[]
for slot in (-1,0,34,49):cases.extend((binder(slot,'mpckpt01.s14'),worker(slot,'mpckpt01.s14'),archive(slot,'mpckpt01.s14')))
cases.extend((title_identity(-1),title_identity(34)))
report={'schema':'san14.private-checkpoint-load-shadow.v1','result':'PASS','cases':cases,'game_access':False,
 'scope':'Copied binder and SSO helpers run without external stubs. Worker stubs the world-load call; archive stubs allocation/storage and deliberately fails opening before deserialization; title check stubs semantic lookup/validation. Proves argument flow and a title-slot condition, not a real load or atomic safe entry.',
 'blocking_risks':['Setting Title+47C=-1 breaks its default resume-identity branch.','Writing pending=34 and relying on a later debugger filename edit can load34 on observer interruption. This is not an eligible live pilot.','The independent save has not yet supplied its immutable hash/size/creation manifest.'],
 'eligible_live_execution':False}
(ROOT/'private_checkpoint_load_shadow.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','cases':len(cases),'game_access':False,'eligible_live_execution':False}))
