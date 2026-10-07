"""Offline native SaveLoad push/init/cancel/pop with real User callbacks.

Only isolated Unicorn memory; never opens a process, Steam, or a save for write.
UI/service/allocator/storage primitives are explicit test doubles. Native
directory scan, header parser, list ownership and state dispatcher do execute.
"""
from datetime import datetime
import hashlib,json,struct
from checkpoint_push_native_chain import ChainHarness,ROOT,BASE,MEM,STOP
from unicorn.x86_const import *

class LoadModeHarness(ChainHarness):
    def __init__(self, capacity=0, file_present=False, init_after=False):
        super().__init__(1,0,capacity,False,False)
        self.names[self.save]='SaveLoad';self.file_present=file_present
        self.dialog=MEM+0x200000;self.list=MEM+0x202000;self.child=MEM+0x204000
        self.fakevt=MEM+0x206000;self.childvt=MEM+0x208000
        self.node_next=MEM+0x220000;self.storage=MEM+0x250000;self.storagevt=MEM+0x251000
        self.holder=MEM+0x252000;self.filename=MEM+0x253000;self.text=MEM+0x254000
        self.u.mem_map(MEM+0x200000,0x100000)
        self.init_observations=[];self.init_return=0;self.wrapper=MEM+0x270000;self.wrapper_end=self.wrapper
        self.cancel_inside_init=init_after
        if init_after:
            # Transparent synthetic AFTER wrapper is machine code, not a stub
            # of native Init or the dispatcher. It preserves original RAX and
            # invokes the actual cancel method only on native EAX==1.
            code=bytes.fromhex('53 48 83 ec 30 48 89 cb 48 b8')+struct.pack('<Q',BASE+0x4A27A0)
            code+=bytes.fromhex('ff d0 48 89 44 24 20 83 f8 01 75 0f 48 89 d9 48 b8')+struct.pack('<Q',BASE+0x4D4AA0)
            code+=bytes.fromhex('ff d0 48 8b 44 24 20 48 83 c4 30 5b c3')
            self.u.mem_write(self.wrapper,code);self.wrapper_end+=len(code)
            self.putq(BASE+0x12DB4C0+8,self.wrapper)
        self.scans=[];self.scan_reads=[];self.registered_ui=[];self.native_updates=0
        self.stream_cursor={};self.freed_ui=[];self.allocated_nodes=[]
        self.payload=(ROOT/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14').read_bytes()
        assert hashlib.sha256(self.payload).hexdigest()=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
        # Native category lists are distinct owners from cache+10 main list.
        for group in range(4):
            head=self.cache_head+0x100+group*0x100
            self.putq(self.cache+0x400+group*0x10,head);self.putq(head,head);self.putq(head+8,head)
        for obj,vt in ((self.dialog,self.fakevt),(self.child,self.childvt)):
            self.putq(obj,vt)
            for offset in (0,0x28,0x38,0x40,0x70,0xC0,0x180):
                self.stub(vt,offset,lambda offset=offset:self.ui_boundary(offset),'menu_ui')
        self.stubs[BASE+0x3A5820]=self.allocate_ui
        self.stubs[BASE+0x763F70]=lambda:self.boundary('window_ctor',self.dialog)
        self.stubs[BASE+0x426290]=lambda:self.boundary('category_widget_ctor',self.child)
        self.stubs[BASE+0x7772A0]=lambda:self.boundary('list_base_ctor',self.reg(UC_X86_REG_RCX))
        self.stubs[BASE+0x281890]=lambda:self.boundary('UI_manager',self.text)
        self.stubs[BASE+0x2D7160]=lambda:self.boundary('localized_text',self.text)
        self.stubs[BASE+0x767650]=lambda:self.boundary('foreground_ui',self.text)
        self.stubs[BASE+0x82E490]=lambda:self.boundary('category_control_lookup',self.text)
        for rva in (0x76C320,0x776320,0x7723E0,0x776380,0x781CE0,0x509C70,
                    0x77C820,0x480920,0x77F310,0x78E010,0x77AFB0,0x775240,
                    0x76E1D0,0x76E2F0,0x76E510,0x76E780):
            self.stubs[BASE+rva]=lambda rva=rva:self.boundary('UI_service_'+hex(rva),1)
        self.stubs[BASE+0x195190]=self.register_ui
        self.stubs[BASE+0x328D20]=lambda:self.boundary('native_filename_variant_provider',0)
        self.stubs[BASE+0x2F1650]=self.format_filename
        # Actual scanner calls the captured Steam ABI; these are isolated fake
        # storage objects. Existing SC00 uses archived bytes only in this VM.
        self.putq(self.holder,self.storage);self.putq(self.storage,self.storagevt)
        context_stub=MEM+0x255000;exists_stub=MEM+0x256000
        self.putq(BASE+0x123CB28,context_stub);self.putq(self.storagevt+0x68,exists_stub)
        self.stubs[context_stub]=lambda:self.boundary('fake_storage_context',self.holder)
        self.stubs[exists_stub]=self.file_exists
        self.stubs[BASE+0x3A5120]=lambda:self.boundary('archive_aux_ctor',self.reg(UC_X86_REG_RCX))
        self.stubs[BASE+0x3A4FC0]=self.stream_ctor
        self.stubs[BASE+0x3A90C0]=self.stream_open
        self.stubs[BASE+0x3A9330]=self.stream_read
        for rva in (0x3A55D0,0x3A56A0,0x3A6340):
            self.stubs[BASE+rva]=lambda rva=rva:self.boundary('archive_teardown_'+hex(rva),0)
        for rva in (0x3A52C0,0x3A5270,0x3A5910,0x3A5930):
            self.stubs[BASE+rva]=lambda rva=rva:self.date_metadata(rva)
        self.stubs[BASE+0xF30D80]=self.strcmp
        self.stubs[BASE+0x3A58B0]=self.free_node
        self.stubs[BASE+0xEF97B4]=self.delete_memory
        # Keep world date and RNG explicit; never run world worker/deserializer.
        self.u.mem_write(self.world+0x34,struct.pack('<HBB',203,8,11))
        self.request_globals=(bytes(self.u.mem_read(BASE+0x201ECD0,0x38)),bytes(self.u.mem_read(BASE+0x201ED10,0x50)))
    def hook(self,u,address,size,data):
        if address==BASE+0x4A27A0:
            self.init_return=self.readq(self.reg(UC_X86_REG_RSP))
            self.init_observations.append({'event':'native_init_enter','args':[hex(self.reg(r)) for r in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9)],
                'return_address':hex(self.init_return),'stack':self.stack_names(),'pending':self.readq(self.manager+0x30)})
        if self.init_return and address==self.init_return:
            self.init_observations.append({'event':'native_init_return','rax':hex(self.reg(UC_X86_REG_RAX)),'stack':self.stack_names(),'pending':self.readq(self.manager+0x30)})
            self.init_return=0
        if address==BASE+0x4D4AA0:
            self.init_observations.append({'event':'native_cancel_enter','self':hex(self.reg(UC_X86_REG_RCX)),'stack':self.stack_names(),'pending':self.readq(self.manager+0x30)})
        if self.wrapper<=address<self.wrapper_end:return
        super().hook(u,address,size,data)
    def allocate_ui(self):
        size=self.reg(UC_X86_REG_RCX)
        table={0x188:MEM+0x50000,0x178:self.dialog,0x1D0:self.list,0x260:self.child}
        if size==0x160:
            target=self.node_next;self.node_next+=0x1000;self.allocated_nodes.append(target)
        else:target=table[size]
        self.boundary('allocate_'+hex(size),target)
    def ui_boundary(self,offset):
        self.boundaries.append({'phase':self.phase,'label':'menu_ui_virtual_'+hex(offset),'this':hex(self.reg(UC_X86_REG_RCX))})
        if offset==0:self.freed_ui.append(self.reg(UC_X86_REG_RCX))
        self.ret(1)
    def delete_memory(self):
        address=self.reg(UC_X86_REG_RCX);self.freed_ui.append(address)
        if address==self.save:self.frees.append('SaveLoad')
        self.boundary('native_delete_stub',0)
    def register_ui(self):
        ptr=self.reg(UC_X86_REG_R8)
        self.registered_ui.append({'event':self.reg(UC_X86_REG_RDX),'vtable':hex(self.readq(ptr)-BASE),'owner':hex(self.readq(ptr+8))})
        self.boundary('UI_event_registration',0)
    def format_filename(self):
        index=self.reg(UC_X86_REG_RCX)&0xffffffff
        name=f'svdexSC{index:02d}.s14'.encode()+b'\0';self.u.mem_write(self.filename,name)
        self.boundary('native_filename_formatter_stub',self.filename)
    def cstring(self,p):return bytes(self.u.mem_read(p,64)).split(b'\0',1)[0].decode('ascii')
    def file_exists(self):
        name=self.cstring(self.reg(UC_X86_REG_RDX));self.scans.append(name)
        self.ret(int(self.file_present and name=='svdexSC00.s14'))
    def stream_ctor(self):
        p=self.reg(UC_X86_REG_RCX);self.u.mem_write(p,bytes(0x98));self.ret(p)
    def stream_open(self):
        p=self.reg(UC_X86_REG_RCX);name=self.read_sso(self.reg(UC_X86_REG_RDX))
        assert self.file_present and name=='svdexSC00.s14' and self.reg(UC_X86_REG_R8)==1
        self.put32(p+0x20,1);self.stream_cursor[p]=0;self.boundary('fake_full_archive_open',1)
    def stream_read(self):
        p=self.reg(UC_X86_REG_RCX);dst=self.reg(UC_X86_REG_RDX);count=self.reg(UC_X86_REG_R8)
        at=self.stream_cursor[p];raw=self.payload[at:at+count];assert len(raw)==count
        self.u.mem_write(dst,raw);self.stream_cursor[p]+=count;self.scan_reads.append({'offset':at,'size':count});self.ret(p)
    def date_metadata(self,rva):
        dst=self.reg(UC_X86_REG_RCX)
        if rva!=0x3A5930:self.u.mem_write(dst,bytes(0x24))
        self.boundary('header_timestamp_helper_'+hex(rva),0 if rva==0x3A5930 else dst)
    def strcmp(self):
        a=self.cstring(self.reg(UC_X86_REG_RCX));b=self.cstring(self.reg(UC_X86_REG_RDX));self.ret(0 if a==b else 1)
    def free_node(self):
        self.boundaries.append({'phase':self.phase,'label':'native_node_free_stub','address':hex(self.reg(UC_X86_REG_RCX))});self.ret(0)
    def run_chain(self,cancel='method'):
        before=self.snapshot();world=bytes(self.u.mem_read(self.world,0x2200))
        self.u.mem_write(self.request,bytes(8));self.phase='queue_load_mode'
        self.run(0x411980,args=(self.manager,BASE+0x12DD6E0,self.request,self.carrier))
        assert self.readq(self.manager+0x30)==1 and self.read32(self.readq(self.manager+0x40))==0
        assert self.readq(self.save)==BASE+0x12DB4C0 and self.readq(self.save+0x48)==0
        assert self.read32(self.cache+8)==0 and self.read32(self.cache+0x3F0)==0 and self.read32(self.cache+0x3EC)==0xffffffff
        self.phase='push_initialize';self.apply();initialized=self.snapshot()
        assert initialized['stack']==before['stack']+['SaveLoad'] and initialized['user_phase']==2
        assert initialized['control_pause']==1 and initialized['cursor_enabled']==0
        assert self.readq(self.save+0x470)==self.list and self.readq(self.save+0x478)==self.dialog
        assert self.read32(self.list+0x170)==0xffffffff and self.readq(self.manager+0x30)==(1 if self.cancel_inside_init else 0)
        assert 0x4AA200 not in self.visits # no selection update before programmatic cancel
        self.phase='cancel_after_native_initialize'
        if cancel=='init_after':assert self.cancel_inside_init
        elif cancel=='method':self.run(0x4D4AA0,args=(self.save,))
        else:
            callback=self.request+0x100;event=self.request+0x200;eventptr=self.request+0x300
            self.putq(callback,BASE+0x12EA2D8);self.putq(callback+8,self.save)
            self.putq(eventptr,event);self.put32(event+0x80,1)
            self.run(0x4FC970,args=(callback,eventptr))
        assert self.readq(self.manager+0x30)==1 and self.read32(self.readq(self.manager+0x40))==1
        assert self.stack_names()==before['stack']+['SaveLoad'] # cancel only queued, not synchronous destroy
        self.phase='pop_finalize';self.apply();after=self.snapshot()
        # Actual User resume re-registers two UI callback carriers. Those local
        # UI bindings may change from the fixture's initial empty containers.
        assert {k:v for k,v in after.items() if not k.startswith('callback_')}=={k:v for k,v in before.items() if not k.startswith('callback_')},(before,after)
        assert [self.readq(self.stack+i*8) for i in range(5)]==self.states
        assert self.read32(self.cache+8)==0 and self.read32(self.cache+0x3F0)==0 and self.read32(self.cache+0x3EC)==0xffffffff
        assert self.readq(self.manager+0x30)==0 and self.readq(self.save+0x470)==self.readq(self.save+0x478)==0
        assert 'User' not in self.frees and self.frees.count('SaveLoad')==1
        assert bytes(self.u.mem_read(self.world,0x2200))==world and self.read32(BASE+0x18EB8B0)==0x12345678
        assert self.request_globals==(bytes(self.u.mem_read(BASE+0x201ECD0,0x38)),bytes(self.u.mem_read(BASE+0x201ED10,0x50)))
        assert len(self.scans)==50 and self.readq(self.cache+0x18)==0
        group_count=self.readq(self.cache+0x408);table=[self.readq(self.cache+0x20+i*8) for i in range(120)]
        if self.file_present:
            assert group_count==1 and table[0]==self.allocated_nodes[0]+0x10 and not any(table[1:])
            assert self.read_sso(table[0]+0x128)=='svdexSC00.s14'
            assert sum(x['size'] for x in self.scan_reads)==294
        else:assert group_count==0 and not any(table)
        required={0x411980,0x426320,0x509EC0,0x509E10,0x50A150,0x50A7BA,0x835DD0,0x836DF0,
            0x3F5530,0x3F5920,0x3F7710,0x3F7A70,0x4A27A0,0x426220,0x43BDA0,0x4C3700,0x837480,
            0x10A60,0x496580,0x4488E0,0x4E0B00,0x438320,0x438410}
        assert required<=set(self.visits),[hex(v) for v in required-set(self.visits)]
        if self.file_present:assert {0x2FAAD0,0x2E0E80,0x2E32A0}<=set(self.visits)
        assert len([v for v in self.init_observations if v['event']=='native_init_return' and v['rax']=='0x1'])==1
        forbidden={0x4AA200,0x508B40,0x2EE4A0,0x2F76C0,0x2FC750,0x508CA0,0x2EE740,0x3F9B00}
        assert not forbidden&set(self.visits),[hex(v) for v in forbidden&set(self.visits)]
        return {'result':'PASS','cancel':cancel,'file_present_in_fake_storage':self.file_present,'before':before,'initialized':initialized,'after':after,
            'mode_after':0,'secondary_after':0,'pending_after':-1,'native_init_returned_before_cancel':True,'cancel_only_queued_pop':True,
            'read_update_executed':False,'load_or_save_worker_executed':False,'original_user_same_object':True,'world_prefix_date_rng_unchanged':True,
            'cache_main_list_count':0,'cache_group0_count':group_count,'nonzero_table_slots':[i for i,p in enumerate(table) if p],
            'metadata_survives_menu_cancel':bool(group_count),'header_bytes_consumed':sum(x['size'] for x in self.scan_reads),
            'required_native_entries':[hex(v) for v in sorted(required)],'instructions':len(self.visits),'boundaries':self.boundaries,
            'ui_handlers_registered':self.registered_ui,'init_observations':self.init_observations,
            'native_field_writes':self.writes,'peripheral_user_calls':self.ui_calls}

def main():
    rows=[]
    for capacity in (0,64):
        for present in (False,True):
            for cancel in ('method','window_callback'):
                h=LoadModeHarness(capacity,present);row=h.run_chain(cancel);row['initial_pending_capacity']=capacity;rows.append(row)
    for present in (False,True):
        h=LoadModeHarness(0,present,True);row=h.run_chain('init_after');row['initial_pending_capacity']=0;rows.append(row)
    result={'schema':'san14.checkpoint-load-mode-native-chain.v1','result':'PASS','cases':rows,'game_access':False,'live_execution_eligible':False,
        'scope':'Actual type0 push ctor, native queue consumption, four actual User lifecycle callbacks, complete SaveLoad initialize/finalize/destructor, real grouped scanner/header/node-copy, native cancel and type1 pop. Two cases additionally run an explicit synthetic transparent x64 after-Init wrapper during actual dispatcher consumption.',
        'entry':{'rva':'0x411980','args':['stateManager','base+0x12DD6E0','pointer to DWORD[2]{0,0}','pointer to zeroed64-byte callback carrier'],'pending_kind':0},
        'cancel':{'initialize':'vtable12DB4C0+8 => 4A27A0; RCX=self, native return EAX=1; retain incoming register/return ABI in any wrapper',
            'after_boundary':'This partial harness stops dispatcher consumption at50B396. At Init return the official stack still has5 entries; SaveLoad is appended later. Init-after cancellation is an explored partial-chain variant, not the production design and not evidence that same-frame Update is skipped.',
            'method':'vtable+70 =>4D4AA0(self), tailcalls10A60(f690()) and queues type1; does not synchronously destroy.',
            'window_callback':'4FC970(callback,eventPointerPointer), event+80==1 also queues10A60; no prior status-field mutation.',
            'fields':'Neither cancellation method resets mode/pending/worker or selected slot. Native finalize reads list+168 as returncode, destroys its UI, then empty return callback means no caller action.'},
        'limits':['UI windows, rendering, event registration/dispatch and many UI services are test doubles. This does not prove their transitive world purity or flicker-free real behavior.',
            'Storage is fake. Present SC00 maps to the archived A file only in VM; no real save or Steam API is accessed. Native scanner/header/parser ownership logic executes.',
            'Timestamp helpers and filename variant/formatter are peripheral stubs; directory scan FileExists is fake and stream primitives read fixture bytes.',
            'World prefix/date/RNG invariants are VM assertions, not full world equivalence. No gameplay update/simulation is run.',
            'Full same-frame Update behavior is covered separately by checkpoint_load_mode_dispatch_audit.py. It proves a queued cancel at Init does not inherently suppress Update and native exit input may enqueue a second pop.',
            'The production candidate therefore guards the first real SaveLoad Update before and after original execution, then cancels only if its queue remains empty; it preserves raw native arguments/result and waits for the same User instance to resume.',
            'Cancel can leave grouped metadata owners atcache+400..430 with120table pointers; metadata core must validate all native owners or separately use a proven cleanup lifecycle.'],
        'source_sha256':hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest()}
    path=ROOT/('checkpoint_load_mode_native_chain_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'path':str(path),'game_access':False}))
if __name__=='__main__':main()
