"""Offline cooperative scheduling proof from captured native instructions.

Windows event/critical-section APIs and the User Update body are explicit test
doubles. Parent dispatcher, payload wrapper, worker completion, and native yield
execute actual archived machine code. No process discovery, native DLL, or game
access exists here.
"""
from pathlib import Path
from datetime import datetime
import hashlib, json, struct, sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)]
sys.argv=sys.argv[:1]
import disasm_chained as d
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *

BASE=0x7ff749440000
MEM=0x300000000
IMAGE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
assert hashlib.sha256(d.image).hexdigest()==IMAGE_SHA
q=lambda x:struct.pack('<Q',x)

class Scheduler:
    def __init__(self):
        self.u=Uc(UC_ARCH_X86,UC_MODE_64)
        self.u.mem_map(BASE,(len(d.image)+4095)&~4095)
        self.u.mem_write(BASE,d.image)
        self.u.mem_map(MEM,0x100000)
        self.manager=MEM+0x1000;self.stack=MEM+0x2000;self.user=MEM+0x3000
        self.pool=MEM+0x5000;self.worker=self.pool+8;self.control=self.worker+8
        self.thread=MEM+0x6000;self.critical=MEM+0x7000
        self.carrier=MEM+0x8000;self.slotbox=MEM+0x9000
        self.user_vt=MEM+0xA000;self.carrier_vt=MEM+0xB000
        self.activation=0x1111;self.completion=0x2222
        self.events={self.activation:False,self.completion:False}
        self.role='parent';self.log=[];self.visits=[];self.paused=None
        self.parent=None;self.worker_context=None;self.user_entered=False
        self.stubs={};self.stop_at=set();self.critical_depth={}
        self.putq(self.manager+0x20,self.stack);self.putq(self.manager+0x10,5)
        self.putq(self.manager+0x48,self.user)
        for n in range(5):self.putq(self.stack+n*8,self.user if n==4 else MEM+0x10000+n*0x1000)
        self.putq(self.user,self.user_vt);self.put32(self.user+0x68,0)
        self.putq(self.worker+8,self.thread);self.putq(self.worker+0x10,self.critical)
        self.putq(self.thread+0x20,self.activation)
        self.putq(self.control+0x60,self.completion)
        self.put32(self.control+0x68,1) # Skip unrelated process worker count init.
        self.putq(self.control+0x48,self.carrier)
        self.putq(self.carrier,self.carrier_vt)
        self.putq(self.carrier_vt+0x10,BASE+0x50B730)
        self.putq(self.carrier+8,self.slotbox);self.putq(self.slotbox,self.stack+32)
        self.putq(BASE+0x2025268,MEM+0xC000)
        self.put32(self.pool+0x208,1)
        self.install_import(0x123C328,'EnterCriticalSection',self.enter)
        self.install_import(0x123C0D8,'LeaveCriticalSection',self.leave)
        self.install_import(0x123C2B8,'ResetEvent',self.reset_event)
        self.install_import(0x123C1D8,'SetEvent',self.set_event)
        self.install_import(0x123C1E0,'WaitForSingleObject',self.wait)
        self.user_entry=MEM+0xD000;self.busy_entry=MEM+0xD100
        self.putq(self.user_vt+0x28,self.user_entry)
        self.putq(self.user_vt+0x30,self.busy_entry)
        self.stubs[self.user_entry]=self.user_callback
        self.stubs[self.busy_entry]=lambda:self.ret(0)
        self.stubs[BASE+0x145B20]=lambda:self.ret(self.pool)
        self.u.hook_add(UC_HOOK_CODE,self.hook)
    def putq(self,p,v):self.u.mem_write(p,q(v))
    def put32(self,p,v):self.u.mem_write(p,struct.pack('<I',v))
    def readq(self,p):return struct.unpack('<Q',self.u.mem_read(p,8))[0]
    def read32(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
    def reg(self,r):return self.u.reg_read(r)
    def ret(self,v=0):
        sp=self.reg(UC_X86_REG_RSP)
        self.u.reg_write(UC_X86_REG_RAX,v)
        self.u.reg_write(UC_X86_REG_RIP,self.readq(sp))
        self.u.reg_write(UC_X86_REG_RSP,sp+8)
    def install_import(self,rva,name,callback):
        address=MEM+0xE000+len(self.stubs)*0x100
        self.putq(BASE+rva,address);self.stubs[address]=callback
    def enter(self):
        p=self.reg(UC_X86_REG_RCX)
        self.critical_depth[p]=self.critical_depth.get(p,0)+1
        self.ret()
    def leave(self):
        p=self.reg(UC_X86_REG_RCX)
        assert self.critical_depth.get(p,0)>0
        self.critical_depth[p]-=1;self.ret()
    def reset_event(self):
        event=self.reg(UC_X86_REG_RCX);assert event in self.events
        self.events[event]=False;self.log.append([self.role,'reset',hex(event)]);self.ret(1)
    def set_event(self):
        event=self.reg(UC_X86_REG_RCX);assert event in self.events
        self.events[event]=True;self.log.append([self.role,'set',hex(event)]);self.ret(1)
    def wait(self):
        event=self.reg(UC_X86_REG_RCX);timeout=self.reg(UC_X86_REG_RDX)&0xffffffff
        assert event in self.events and timeout==0xffffffff
        if not self.events[event]:
            self.paused='blocked_wait';self.log.append([self.role,'wait_blocked',hex(event)]);self.u.emu_stop()
        else:self.log.append([self.role,'wait_returned',hex(event)]);self.ret(0)
    def user_callback(self):
        assert self.reg(UC_X86_REG_RCX)==self.user
        assert self.readq(self.reg(UC_X86_REG_RSP))==BASE+0x50B785
        self.user_entered=True;self.paused='user_after_model'
        self.log.append(['worker','user_callback_model',hex(self.readq(self.user+0x50))])
        self.u.emu_stop()
    def hook(self,u,address,size,data):
        if address in self.stop_at:
            self.paused=hex(address-BASE);u.emu_stop();return
        if address in self.stubs:self.stubs[address]();return
        assert BASE<=address<BASE+len(d.image),hex(address)
        self.visits.append((self.role,address-BASE))
    def execute(self,start=None):
        self.paused=None
        self.u.emu_start(start or self.reg(UC_X86_REG_RIP),MEM+0xF0000,count=50000)
        assert self.paused,'VM instruction limit'
    def setup(self,stack_offset):
        sp=MEM+stack_offset
        self.u.reg_write(UC_X86_REG_RSP,sp);self.u.reg_write(UC_X86_REG_RBP,sp+0x300)
        self.putq(sp,MEM+0xF0000)
        return sp
    def start_parent(self):
        self.role='parent';sp=self.setup(0xEF000)
        self.u.reg_write(UC_X86_REG_R15,self.manager)
        self.u.reg_write(UC_X86_REG_R14,0)
        self.u.reg_write(UC_X86_REG_RDI,self.worker)
        self.putq(sp+0x40,self.stack+32)
        self.stop_at={BASE+0x50B632}
        self.execute(BASE+0x50B58C)
        assert self.paused=='blocked_wait'
        assert self.readq(self.user+0x50)==self.worker and self.read32(self.control+0x50)==0
        self.parent=self.u.context_save()
    def start_worker(self):
        self.role='worker';self.setup(0xDF000)
        self.u.reg_write(UC_X86_REG_RCX,self.thread);self.u.reg_write(UC_X86_REG_RDX,self.control)
        self.stop_at={BASE+0x834DF0}
        self.execute(BASE+0x834D10)
        assert self.paused=='user_after_model'
        self.worker_context=self.u.context_save()
    def poll_parent(self):
        self.role='parent';self.u.context_restore(self.parent);self.stop_at={BASE+0x50B632}
        self.execute();self.parent=self.u.context_save()
        return self.paused
    def finish_worker(self):
        self.role='worker';self.u.context_restore(self.worker_context);self.stop_at={BASE+0x834DF0}
        self.ret(0xFEDCBA9876543210)
        self.execute()
        assert self.paused==hex(0x834DF0) and self.read32(self.control+0x50)==1
        self.worker_context=self.u.context_save()
    def yield_worker(self):
        # Enter actual yield from the suspended User model. Its wait is left
        # blocked; native User/payload/worker completion has NOT returned.
        self.role='worker';self.u.context_restore(self.worker_context)
        sp=self.reg(UC_X86_REG_RSP)-0x200
        self.putq(sp,MEM+0xF0000);self.u.reg_write(UC_X86_REG_RSP,sp)
        self.u.reg_write(UC_X86_REG_RCX,self.user)
        self.events[self.activation]=False
        self.stop_at=set();self.execute(BASE+0x50B690)
        assert self.paused=='blocked_wait' and self.read32(self.worker+0x78)==1
        assert self.read32(self.control+0x50)==0

def case(kind):
    h=Scheduler();h.start_parent();h.start_worker()
    assert h.poll_parent()=='blocked_wait'
    assert h.readq(h.manager+0x48)==h.user
    before=len(h.visits)
    if kind=='normal_completion':
        h.finish_worker();assert h.poll_parent()==hex(0x50B632)
        assert h.readq(h.user+0x50)==0
    elif kind=='cooperative_yield_escape':
        h.yield_worker();assert h.poll_parent()==hex(0x50B632)
        assert h.readq(h.user+0x50)==h.worker
        assert h.read32(h.control+0x50)==0
    else:raise AssertionError(kind)
    required={0x834B60,0x834EF0,0x834460,0x50B730,0x834D10}
    assert required<=set(i for _,i in h.visits)
    return {'case':kind,'result':'PASS','parent_stayed_blocked_during_user_model':True,
        'completion_flag':h.read32(h.control+0x50),'yield_flag':h.read32(h.worker+0x78),
        'state_worker_still_attached':bool(h.readq(h.user+0x50)),
        'advanced_to_dispatcher_tail':True,'trace':h.log,
        'native_entries':[hex(i) for i in sorted(required)],'native_instructions':len(h.visits)}

def main():
    rows=[case('normal_completion'),case('cooperative_yield_escape')]
    output=ROOT/('checkpoint_metadata_boundary_shadow_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    result={'schema':'san14.checkpoint-metadata-boundary-shadow.v1','result':'PASS','cases':rows,
        'game_access':False,'native_image_sha256':IMAGE_SHA,
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'proved':'Actual parent dispatcher waits for native worker completion unless cooperative yield flag+completion event release it early. User wrapper return precedes actual runner completion publication.',
        'not_proved':['Windows scheduling is represented by explicit context switches and Win32 event/critical-section stubs.',
            'User Update body is an explicit callback model, not the real gameplay body; original-return bridge semantics have separate fixtures.',
            'No global cache exclusion, Steam callback purity, or production metadata fence is asserted.',
            'The yield example demonstrates why active call_id and before/after snapshots alone are not exclusive ownership.']}
    with output.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'path':str(output),'game_access':False}))
if __name__=='__main__':main()
