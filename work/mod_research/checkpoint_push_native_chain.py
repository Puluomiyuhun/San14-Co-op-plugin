"""Offline native binder/queue/dispatcher/User/save-return chain.

Runs captured x64 instructions in a private VM. The dispatcher really mutates
the native fixture stack. No game process, native DLL, file save or live entry.
"""
from pathlib import Path
from datetime import datetime
import hashlib, json, struct
from save_return_user_shadow import UserHarness, ROOT, BASE, MEM, STOP
from unicorn import UC_HOOK_MEM_READ
from unicorn.x86_const import *

q=lambda n:struct.pack('<Q',n)
def sso(text):
    b=text.encode('ascii');assert len(b)<=15
    return b.ljust(16,b'\0')+q(len(b))+q(15)

class ChainHarness(UserHarness):
    def __init__(self, mode=1, secondary=0, capacity=0, selected=False, valid=False):
        super().__init__(selected,valid,True,False)
        self.u.mem_map(MEM+0x100000,0x100000)
        self.root=MEM+0x100000;self.world=MEM+0x190000
        self.cache=MEM+0x1C0000;self.cache_head=self.cache+0x1000
        self.save_ui=MEM+0x1D0000;self.save_ui_vt=self.save_ui+0x1000
        self.request=MEM+0x1E0000
        self.boundaries=[];self.cache_mode_reads=[];self.cache_mode_writes=[]
        self.phase='setup';self.mode=mode;self.secondary=secondary
        self.putq(BASE+0x1FCA1E0,self.root);self.putq(self.root+0x85130,self.world)
        self.u.mem_write(self.world,bytes((13*i+7)&255 for i in range(0x2200)))
        self.put32(BASE+0x18EB8B0,0x12345678)
        self.putq(BASE+0x2025318,self.cache);self.put32(self.cache+8,mode)
        self.put32(self.cache+0x3F0,secondary);self.put32(self.cache+0x3EC,0xffffffff)
        self.put32(self.cache+0x3E8,56);self.put32(self.cache+0x3F8,114)
        self.putq(self.cache+0x10,self.cache_head);self.putq(self.cache_head,self.cache_head);self.putq(self.cache_head+8,self.cache_head)
        self.putq(self.manager+0x38,capacity);self.putq(self.manager+0x40,self.pending if capacity else 0)
        # Execute the real Save constructor; its real vtable remains installed.
        del self.stubs[BASE+0x4263C0]
        del self.stubs[BASE+0x835DD0]
        self.putq(self.save_ui,self.save_ui_vt)
        for offset in (0,0x28,0x38,0x40):
            self.stub(self.save_ui_vt,offset,lambda offset=offset:self.boundary('progress_ui_virtual_'+hex(offset),1),'progress_ui')
        self.stubs[BASE+0x3A5820]=self.allocate_ui
        self.stubs[BASE+0x763DD0]=lambda:self.boundary('graphics_context_ctor',MEM+0x50000)
        self.stubs[BASE+0x5D3730]=lambda:self.boundary('progress_ui_ctor',self.save_ui)
        for rva in (0x5D5840,0x5D7940,0x5D7A30):
            self.stubs[BASE+rva]=lambda rva=rva:self.boundary('progress_ui_'+hex(rva),1)
        self.stubs[BASE+0x833440]=lambda:self.boundary('thread_destroy',0)
        self.stubs[BASE+0xEF97B4]=self.delete_memory
        for rva,label,value in ((0x8351F0,'clock',12345),(0x833CB0,'thread_construct',0),
             (0x834B60,'thread_start',0),(0x834460,'thread_done',1),(0x834BC0,'thread_join',0),
             (0x2EFF70,'error_text_getter',MEM+0x1F0000),(0x187C10,'error_context',0),
             (0x9C4F60,'error_text_length',0),(0x1D5170,'error_dialog',0)):
            self.stubs[BASE+rva]=lambda label=label,value=value:self.boundary(label,value)
        self.u.hook_add(UC_HOOK_MEM_READ,self.read_watch)
    def read32(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
    def boundary(self,label,result):
        self.boundaries.append({'phase':self.phase,'label':label});self.ret(result)
    def allocate_ui(self):
        size=self.reg(UC_X86_REG_RCX)
        assert size in (0x168,0x188)
        self.boundary('ui_allocate_'+hex(size),self.save_ui if size==0x168 else MEM+0x50000)
    def delete_memory(self):
        self.boundaries.append({'phase':self.phase,'label':'memory_delete','address':hex(self.reg(UC_X86_REG_RCX))})
        if self.reg(UC_X86_REG_RCX)==self.save:self.frees.append('Save')
        self.ret(0)
    def read_watch(self,u,access,address,size,value,data):
        if any(address<=self.cache+x<address+size for x in (8,0x3F0)):
            self.cache_mode_reads.append({'phase':self.phase,'rva':hex(self.reg(UC_X86_REG_RIP)-BASE),'offset':hex(address-self.cache),'size':size})
    def record_write(self,u,access,address,size,value,data):
        super().record_write(u,access,address,size,value,data)
        if hasattr(self,'cache') and any(address<=self.cache+x<address+size for x in (8,0x3F0)):
            self.cache_mode_writes.append({'phase':self.phase,'rva':hex(self.reg(UC_X86_REG_RIP)-BASE),'offset':hex(address-self.cache),'size':size})
    def read_sso(self,address):
        size=self.readq(address+16);cap=self.readq(address+24)
        assert cap==15 and size<=15
        return bytes(self.u.mem_read(address,size)).decode('ascii')
    def binder(self):
        self.phase='bind'
        self.u.mem_write(self.request,struct.pack('<i',-1)+bytes(4)+sso('mppush01.s14')+sso('fixture'))
        self.run(0x2FC750,args=(self.request,))
        assert self.read32(BASE+0x201ED10)==0xffffffff
        assert self.read_sso(BASE+0x201ED18)=='mppush01.s14' and self.read_sso(BASE+0x201ED38)=='fixture'
        assert self.read_sso(self.request+8)==self.read_sso(self.request+0x28)==''
    def run_chain(self, success=1):
        before=self.snapshot();world=bytes(self.u.mem_read(self.world,0x2200));self.binder()
        self.phase='queue';assert self.queue(0x2DF990)==0
        assert self.readq(self.save)==BASE+0x12DC5F8
        assert self.read32(self.save+0x470)==0 and self.readq(self.save+0x4E8)==0
        assert self.readq(self.save+0x48)==0 and self.readq(self.carrier+0x38)==0
        self.phase='push';self.apply();paused=self.snapshot()
        assert paused['stack']==before['stack']+['Save'] and paused['user_phase']==2
        assert paused['control_pause']==1 and paused['cursor_enabled']==0
        assert self.readq(self.save+0x4E8)==self.save_ui
        self.phase='save_phase0';self.run(0x4AA650,args=(self.save,0,0,0));assert self.read32(self.save+0x470)==1
        self.phase='save_phase1';self.run(0x4AA650,args=(self.save,0,0,0));assert self.read32(self.save+0x470)==2
        assert self.read32(BASE+0x201EC2C)==0
        # The worker has not run: publication below is explicitly synthetic.
        self.put32(BASE+0x201EC2C,success)
        self.phase='save_phase2';self.run(0x4AA650,args=(self.save,0,0,0));assert self.read32(self.save+0x470)==3
        self.phase='save_phase3';self.run(0x4AA650,args=(self.save,0,0,0));assert self.read32(self.save+0x470)==4
        self.phase='save_phase4';self.run(0x4AA650,args=(self.save,0,0,0))
        assert self.readq(self.manager+0x30)==1 and self.read32(self.readq(self.manager+0x40))==1
        self.phase='pop';self.apply();after=self.snapshot()
        assert after['stack']==before['stack'] and after['user_phase']==2
        assert [self.readq(self.stack+i*8) for i in range(5)]==self.states
        assert after['control_pause']==0 and after['cursor_enabled']==1
        assert after['advance_game']==after['advance_panel']==0 and after['pending_menu']==-1
        assert 'User' not in self.frees and self.readq(self.save+0x4E8)==0
        assert self.read32(self.cache+8)==self.mode and self.read32(self.cache+0x3F0)==self.secondary
        assert self.read32(self.cache+0x3EC)==0xffffffff
        assert self.read_sso(BASE+0x201ED18)==self.read_sso(BASE+0x201ED38)==''
        assert bytes(self.u.mem_read(self.world,0x2200))==world and self.read32(BASE+0x18EB8B0)==0x12345678
        required={0x2FC750,0x2DF990,0x4263C0,0x8333D0,0x509EC0,0x509E10,
          0x50A150,0x50A7BA,0x3F5530,0x3F5920,0x3F7710,0x3F7A70,
          0x4A29D0,0x4AA650,0x4DA320,0x4F7050,0x465C10,0x10A60,
          0x497A00,0x438490,0x835DD0,0x836DF0}
        assert required<=set(self.visits),[hex(x) for x in required-set(self.visits)]
        assert not self.cache_mode_reads and not self.cache_mode_writes
        return {'result':'PASS','mode':self.mode,'secondary':self.secondary,'synthetic_worker_success':bool(success),
          'before':before,'paused':paused,'after':after,'native_instructions':len(self.visits),
          'visited_required':[hex(x) for x in sorted(required)],'save_state_finalized':True,'original_user_retained':True,
          'cache_mode_reads':self.cache_mode_reads,'cache_mode_writes':self.cache_mode_writes,
          'world_prefix_and_rng_unchanged':True,'boundaries':self.boundaries,'peripheral_user_calls':self.ui_calls,
          'frees':self.frees}

def main():
    rows=[]
    for mode,secondary in ((0,0),(0,1),(1,0),(1,1)):
        for capacity in (0,64):
            for success in (0,1):
                h=ChainHarness(mode,secondary,capacity)
                row=h.run_chain(success);row['initial_pending_capacity']=capacity;rows.append(row)
    for selected,valid in ((True,False),(True,True)):
        h=ChainHarness(1,0,0,selected,valid);row=h.run_chain(1)
        row.update(selected=selected,selection_valid=valid);rows.append(row)
    result={'schema':'san14.checkpoint-push-native-chain.v1','result':'PASS','cases':rows,
      'game_access':False,'save_files_written':False,'retired_entry_reenabled':False,
      'scope':'Real binder, constructor, queue, event dispatcher and apply switch, four User callbacks, Save initialize/update/finalize/destructor with explicitly stubbed UI/thread/allocator boundaries. Worker publication synthetic.',
      'dispatcher':'Inherited apply executes 0x50A150 event switch and 0x50A7BA pending-copy/kind dispatch/stack mutation. It constructs only the temporary linked-list backend from current fixture stack; it never assigns the resulting state stack by hand.',
      'limits':['Real worker/storage/full serialization are not in this chain; result publication is explicitly synthetic.',
                'Generic temporary linked-list allocation, graphics/UI/services, thread and allocators use fixture stubs.',
                'Empty cache only; native cache cleanup of a populated directory needs separate ownership validation.',
                'World prefix and RNG preservation are fixture assertions, not a complete world equivalence proof.',
                'Cache mode/secondary not read by this chain excludes the synthetic worker and external UI/service callees.']}
    path=ROOT/('checkpoint_push_native_chain_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'path':str(path),'game_access':False}))

if __name__=='__main__':main()
