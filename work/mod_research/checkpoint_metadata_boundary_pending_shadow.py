"""Offline Init scope and private-metadata invalidation before Title binding.

Never imports the older private shadow scripts (which publish legacy results
at import). Only new checkpoint_metadata_boundary_* evidence is produced.
"""
from datetime import datetime
from pathlib import Path
import hashlib,json,struct
from checkpoint_load_mode_native_chain import LoadModeHarness,BASE,MEM,ROOT
from unicorn.x86_const import *

class ScopeHarness(LoadModeHarness):
    def __init__(self):
        super().__init__(0,False,False)
        self.scope_snapshots=[]
    def hook(self,u,address,size,data):
        if self.init_return and address==self.init_return:
            self.scope_snapshots.append({'return_rva':hex(address-BASE),
                'raw_rax':hex(self.reg(UC_X86_REG_RAX)),
                'formal_stack':self.stack_names(),
                'formal_state_workers':[hex(self.readq(p+0x50)) for p in self.states],
                'new_state_worker':hex(self.readq(self.save+0x50)),
                'transition_count':self.readq(self.manager+0x30),
                'cache_mode':self.read32(self.cache+8),
                'cache_pending':self.read32(self.cache+0x3EC),
                'list_selection':self.read32(self.list+0x170),
                'native_scanner_completed':0x837480 in self.visits})
        super().hook(u,address,size,data)

def initialized():
    h=ScopeHarness();h.u.mem_write(h.request,bytes(8))
    h.run(0x411980,args=(h.manager,BASE+0x12DD6E0,h.request,h.carrier));h.apply()
    assert len(h.scope_snapshots)==1
    s=h.scope_snapshots[0]
    assert s['return_rva']=='0x50b2df' and s['raw_rax']=='0x1'
    assert len(s['formal_stack'])==5 and s['formal_state_workers']==['0x0']*5
    assert s['new_state_worker']=='0x0' and s['transition_count']==0
    assert s['cache_mode']==0 and s['cache_pending']==s['list_selection']==0xffffffff
    assert s['native_scanner_completed']
    return h

def game_request():
    h=initialized();h.put32(h.cache+0x3EC,63)
    newgame,title=MEM+0x290000,MEM+0x2A0000
    h.names[newgame]='ReplacementGame';h.names[title]='Title'
    def allocate():
        size=h.reg(UC_X86_REG_RDX);assert size in(0x498,0x13e10)
        h.ret(newgame if size==0x498 else title)
    h.stub(h.allocvt,0x40,allocate,'transition_state_allocation')
    h.stubs[BASE+0x1C1A70]=lambda:h.ret(0)
    title_args=[]
    def title_ctor():
        self=h.reg(UC_X86_REG_RCX);arg=h.reg(UC_X86_REG_RDX)
        title_args.append(h.read32(arg));assert self==title
        # Explicit peripheral constructor stub: this experiment proves actual
        # Game Update + queue construction, not all Title UI initialization.
        h.putq(title,MEM+0x2E0000);h.put32(title+0x4B0,h.read32(arg));h.ret(title)
    h.stubs[BASE+0x426440]=title_ctor
    start=len(h.visits);h.run(0x3F8140,args=(h.states[2],0,0,0))
    pointer=h.readq(h.manager+0x40);count=h.readq(h.manager+0x30)
    commands=[{'kind':h.read32(pointer+i*16),'name':h.cstring(h.readq(pointer+i*16+8)+0x70)} for i in range(count)]
    assert commands==[{'kind':3,'name':'CGameState'},{'kind':2,'name':'CTitleState'}]
    assert title_args==[1]
    assert h.read32(h.states[2]+0x474)==h.read32(h.states[2]+0x478)==1
    assert {0x3F8140,0x3DFB40,0x3E3B90,0x509EC0}<=set(h.visits[start:])
    return {'case':'game_update_consumes_pending_63','result':'PASS','pending_commands':commands,
        'title_constructor_param':title_args[0],'init_scope':h.scope_snapshots[0],
        'limits':'State allocator, optional service getter, and Title ctor are stubs. Actual Game Update and both native queue builders execute. Queue consumption/teardown is not claimed by this case.'}

def rescan_invalidates():
    h=initialized();slot=63;header=MEM+0x280000;name=header+0x400
    h.run(0x2E32A0,args=(header,));h.u.mem_write(name,b'mppush01.s14\0')
    h.run(0x511D0,args=(header+0x128,name,12))
    head=h.readq(h.cache+0x10);tail=h.readq(head+8)
    h.run(0x2E0E80,args=(h.cache+0x10,head,tail,header))
    node=h.reg(UC_X86_REG_RAX)
    # Represent the already-completed Registration's four stores. This is
    # isolated fixture setup, not a live adapter or substitute for its proof.
    h.putq(h.cache+0x18,1);h.putq(head+8,node);h.putq(tail,node);h.putq(h.cache+0x20+8*slot,node+16)
    h.put32(h.cache+0x3EC,slot)
    h.run(0x836710,args=(h.cache,slot));assert h.reg(UC_X86_REG_RAX)==node+16
    h.scans=[];before=len(h.visits)
    # This is the real function unconditionally called at Title Init4A3143.
    h.run(0x836EF0,args=(h.cache,0))
    assert len(h.scans)==120 and h.readq(h.cache+0x20+8*slot)==0
    assert h.readq(h.cache+0x18)==0 and h.readq(head)==h.readq(head+8)==head
    assert h.read32(h.cache+0x3EC)==slot
    assert {0x836EF0,0x836DF0,0x837E80}<=set(h.visits[before:])
    assert any(x.get('address')==hex(node) for x in h.boundaries if x['label']=='native_node_free_stub')
    title=MEM+0x2A0000;h.put32(title+0x47C,0xffffffff)
    bound_before=bytes(h.u.mem_read(BASE+0x201ECD0,0x38));start=len(h.visits)
    h.run(0x4CEAB0,args=(title,0))
    assert 0x836710 in h.visits[start:] and 0x4BF5A0 not in h.visits[start:]
    assert 0x410810 not in h.visits[start:]
    assert h.read32(title+0x47C)==0xffffffff
    assert bytes(h.u.mem_read(BASE+0x201ECD0,0x38))==bound_before
    return {'case':'title_rescan_removes_private_registration','result':'PASS',
        'slot':slot,'private_name':'mppush01.s14','native_node_copy_executed':True,
        'real_rescan_cleared_main_list_and_table':True,'native_scan_file_exists_calls':len(h.scans),
        'private_node_freed_by_native_clear':True,'pending_remains_slot':slot,
        'native_title_lookup_returns_null':True,'native_filename_binder_executed':False,
        'native_load_state_queued':False,
        'limits':'Fake storage has no standard files; formatter/date/storage/free primitives are stubs. The lost private target remains lost with ordinary files present unless its exact slot is recreated by the native scanner. No world worker or live memory is accessed.'}

def main():
    rows=[game_request(),rescan_invalidates()]
    out=ROOT/('checkpoint_metadata_boundary_pending_shadow_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    result={'schema':'san14.checkpoint-metadata-boundary-pending-shadow.v1','result':'PASS',
        'cases':rows,'game_access':False,'eligible_live_register_then_pending':False,
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'conclusion':'SaveLoad Init AFTER is a candidate finite registration boundary. Publishing pending there does not carry private metadata through Title Init: its unconditional native rescan removes that registration before filename binding. Do not execute this combined path.'}
    with out.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'path':str(out),'game_access':False,'eligible_live_register_then_pending':False}))
if __name__=='__main__':main()
