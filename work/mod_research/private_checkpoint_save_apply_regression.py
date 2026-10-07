"""Offline state-entry regression using copied queue, dispatcher and save cleanup.

This is NOT a live-ready export profile. Actual native lifecycle callbacks are
recorded stubs; their UI/selection/gameplay side effects remain unproved.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent;sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)];sys.argv=sys.argv[:1]
import disasm_chained as d
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
BASE=0x7ff749440000;MEM=0x300000000;STOP=MEM+0xF0000
assert hashlib.sha256(d.image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
q=lambda n:struct.pack('<Q',n)
class Harness:
    def __init__(self):
        self.u=Uc(UC_ARCH_X86,UC_MODE_64);self.u.mem_map(BASE,(len(d.image)+4095)&~4095);self.u.mem_write(BASE,d.image);self.u.mem_map(MEM,0x100000)
        self.manager=MEM+0x1000;self.allocator=MEM+0x2000;self.allocvt=MEM+0x2800;self.stack=MEM+0x3000;self.pending=MEM+0x4000;self.carrier=MEM+0x5000;self.temp=MEM+0x6000
        self.states=[MEM+0x10000+i*0x1000 for i in range(5)];self.user=self.states[-1];self.save=MEM+0x18000
        self.names={p:n for p,n in zip(self.states,['Root','Motor','Game','Strategy','User'])};self.names[self.save]='Save'
        self.callbacks=[];self.frees=[];self.visits=[];self.stubs={};self.index=MEM+0x7000;self.heads=MEM+0x7100;self.counts=MEM+0x7200;self.nodes=MEM+0x7300
        for offset in (0,8,0x28):self.putq(self.manager+offset,self.allocator)
        for offset,value in ((0x10,5),(0x18,16),(0x20,self.stack),(0x30,0),(0x38,64),(0x40,self.pending)):self.putq(self.manager+offset,value)
        self.putq(self.allocator,self.allocvt)
        self.stub(self.allocvt,0x40,lambda: self.ret(self.save),'state_allocate')
        self.stub(self.allocvt,0x28,lambda: self.ret(self.pending),'pending_allocate')
        self.putq(self.allocvt+0x48,BASE+0x1479B0)
        self.stub(self.allocvt,0x58,self.free,'allocator_free')
        for at in self.states+[self.save]:
            vt=MEM+0x30000+(at-self.states[0]);self.putq(at,vt);self.put32(at+0x470,2 if at==self.user else 0);self.put32(at+0x6c,3)
            for offset,label in ((0,'destroy'),(8,'initialize'),(0x10,'finalize'),(0x18,'resume'),(0x20,'pause'),(0x58,'enter_event'),(0x60,'exit_event')):
                self.stub(vt,offset,lambda label=label:self.callback(label),label)
        for i,state in enumerate(self.states):self.putq(self.stack+i*8,state)
        # A preconstructed graphics context avoids unrelated UI allocation. Its
        # lifecycle is also stubbed, never inferred to be harmless in the game.
        context=MEM+0x50000;contextvt=MEM+0x51000;self.putq(self.save+0x60,context);self.putq(context,contextvt)
        for offset in (0,0x28,0x38,0x40,0x180):self.stub(contextvt,offset,lambda:self.ret(1),'graphics_callback')
        self.stubs[BASE+0x4263C0]=lambda:self.ret(self.save)
        self.stubs[BASE+0x50B7A0]=self.grow_temporary
        self.stubs[BASE+0xF690]=lambda:self.ret(self.manager)
        self.stubs[BASE+0x835DD0]=lambda:self.ret(0)
        self.stubs[BASE+0x172D0]=self.push_temporary_node
        self.stubs[BASE+0xC7660]=self.pop_temporary_node
        for address in (0x201ED18,0x201ED38):self.u.mem_write(BASE+address,bytes(24)+q(15))
        self.put32(BASE+0x201EC2C,1) # Synthetic worker success; no worker is run.
        self.u.hook_add(UC_HOOK_CODE,self.hook)
    def readq(self,at):return struct.unpack('<Q',self.u.mem_read(at,8))[0]
    def putq(self,at,n):self.u.mem_write(at,q(n))
    def put32(self,at,n):self.u.mem_write(at,struct.pack('<I',n))
    def reg(self,reg):return self.u.reg_read(reg)
    def ret(self,value):
        sp=self.reg(UC_X86_REG_RSP);self.u.reg_write(UC_X86_REG_RAX,value);self.u.reg_write(UC_X86_REG_RIP,self.readq(sp));self.u.reg_write(UC_X86_REG_RSP,sp+8)
    def stub(self,vt,offset,function,label):
        address=MEM+0x80000+len(self.stubs)*0x100;self.stubs[address]=function;self.putq(vt+offset,address)
    def callback(self,label):
        self.callbacks.append({'state':self.names.get(self.reg(UC_X86_REG_RCX),'other'),'method':label,'kind':self.reg(UC_X86_REG_RDX)&0xffffffff});self.ret(1)
    def free(self):self.frees.append(self.names.get(self.reg(UC_X86_REG_RDX),'storage'));self.ret(0)
    def grow_temporary(self):
        vector=self.reg(UC_X86_REG_RCX);self.putq(vector,self.temp);self.putq(vector+8,self.temp);self.putq(vector+16,self.temp+16*self.reg(UC_X86_REG_RDX));self.ret(self.temp)
    def push_temporary_node(self):
        node=self.nodes+0x100+self.readq(self.counts)*0x20;self.putq(node+0x10,self.readq(self.heads));self.putq(self.heads,node);self.putq(self.counts,self.readq(self.counts)+1);self.ret(node)
    def pop_temporary_node(self):
        node=self.readq(self.heads);self.putq(self.heads,self.readq(node+0x10));self.putq(self.counts,self.readq(self.counts)-1);self.ret(0)
    def hook(self,u,address,size,data):
        if address==self.stop:u.emu_stop();return
        if address in self.stubs:self.stubs[address]();return
        assert BASE<=address<BASE+len(d.image),f'Unrecognized external {address:#x}'
        self.visits.append(address-BASE)
    def run(self,start,stop=STOP,args=(),setup=None):
        sp=MEM+0xEF000;self.u.mem_write(sp-0x1000,bytes(0x2000));self.putq(sp,STOP);self.u.reg_write(UC_X86_REG_RSP,sp);self.u.reg_write(UC_X86_REG_RBP,sp+0x300)
        for reg,arg in zip((UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9),args):self.u.reg_write(reg,arg)
        if setup:setup(sp)
        self.stop=stop;self.u.emu_start(BASE+start,stop,count=100000)
        assert self.reg(UC_X86_REG_RIP)==stop,'Instruction limit'
    def stack_names(self):return [self.names[self.readq(self.stack+i*8)] for i in range(self.readq(self.manager+0x10))]
    def queue(self,entry):
        self.run(entry,args=(self.manager,BASE+0x12AA8E0,0,self.carrier))
        assert self.readq(self.manager+0x30)==1
        return struct.unpack('<I',self.u.mem_read(self.readq(self.manager+0x40),4))[0]
    def apply(self):
        # Execute actual event-dispatch switch for one command against a temporary
        # stack-list snapshot. Only its generic linked-list backend is stubbed.
        objects=[self.readq(self.stack+i*8) for i in range(self.readq(self.manager+0x10))]
        previous=0
        for i,state in enumerate(objects):
            node=self.nodes+i*0x20;self.putq(node,state);self.putq(node+0x10,previous);previous=node
        self.putq(self.heads,previous);self.putq(self.counts,len(objects))
        self.putq(BASE+0x201D3B0,self.counts);self.putq(BASE+0x201D3B8,self.heads);self.put32(BASE+0x201D3E0,1);self.put32(BASE+0x201D370,0)
        def setup_event(sp):
            for register,value in ((UC_X86_REG_R15,self.manager),(UC_X86_REG_R12,self.readq(self.manager+0x40)),(UC_X86_REG_RBX,self.index),(UC_X86_REG_R8,self.heads),(UC_X86_REG_R13,0),(UC_X86_REG_RSI,0)):self.u.reg_write(register,value)
            self.putq(sp+0x38,0);self.putq(sp+0x30,0)
        self.run(0x50A150,BASE+0x50A713,setup=setup_event)
        # Actual pending-copy, pending-free/clear, kind dispatch and stack mutation.
        # Stop after the single command, before unrelated per-frame state updates.
        def setup_apply(sp):
            for register,value in ((UC_X86_REG_R15,self.manager),(UC_X86_REG_RSI,0)):self.u.reg_write(register,value)
            self.putq(sp+0x38,0);self.putq(sp+0x30,0)
        self.run(0x50A7BA,BASE+0x50B396,setup=setup_apply)
        return self.stack_names()
    def complete(self):
        self.run(0x465C10)
        assert self.readq(self.manager+0x30)==1
        assert struct.unpack('<I',self.u.mem_read(self.readq(self.manager+0x40),4))[0]==1
        return self.apply()

rows=[]
for entry,kind,expected_mid,expected_end in [(0x412520,2,['Root','Motor','Game','Strategy','Save'],['Root','Motor','Game','Strategy']),
                                           (0x2DF990,0,['Root','Motor','Game','Strategy','User','Save'],['Root','Motor','Game','Strategy','User'])]:
    h=Harness();initial=h.stack_names();assert h.queue(entry)==kind
    middle=h.apply();assert middle==expected_mid,(hex(entry),middle)
    final=h.complete();assert final==expected_end,(hex(entry),final)
    user_destroyed=any(row['state']=='User' and row['method']=='destroy' for row in h.callbacks)
    assert user_destroyed==(kind==2)
    assert any(row['state']==('User' if kind==0 else 'Strategy') and row['method']=='resume' for row in h.callbacks)
    assert struct.unpack('<I',h.u.mem_read(h.user+0x470,4))[0]==2
    rows.append({'entry_rva':hex(entry),'command_kind':kind,'initial':initial,'after_apply':middle,'after_native_save_cleanup_and_pop':final,
                 'user_destroyed':user_destroyed,'user_preserved':kind==0,'user_phase2_retained_under_stub_callbacks':True,
                 'native_dispatch_instructions':len(h.visits),'callbacks':h.callbacks,'frees':h.frees,'result':'PASS'})
stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f');path=ROOT/('private_checkpoint_save_apply_regression_'+stamp+'.json')
report={'result':'PASS','cases':rows,'game_access':False,'live_execution_allowed':False,'native_export_success':False,
        'executed_native_paths':['412520 replacement queue','2DF990 push queue and empty callback carrier helpers','509EC0 name copy','509FE0 event/apply switch fragments','1479B0 null growth branch','465C10 save completion','10A60 pop queue'],
        'stubbed':['state allocation and constructor','heap allocation/free','temporary stack-list operations','temporary vector allocation','all state lifecycle/UI callbacks','cache invalidation'],
        'limits':['Synthetic worker success flag; serializer and worker are not run','Actual User pause/resume/selection callback side effects are unproved','5-to-6-to-5 structural preservation does not establish a legal identical checkpoint','No new live launcher or re-enabled old profile']}
with path.open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
print(json.dumps({'result':'PASS','cases':len(rows),'evidence':str(path),'game_access':False,'native_export_success':False}))
