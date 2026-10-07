"""Offline worker filename/mode propagation and cache-mode read audit."""
from datetime import datetime
import bisect, json, struct
from checkpoint_push_native_chain import ChainHarness, ROOT, BASE, MEM, q
from save_return_shadow_base import d
from unicorn.x86_const import *
from capstone.x86_const import X86_OP_MEM, X86_REG_RIP

def function(at):
    e=d.entries[bisect.bisect_right(d.starts,at)-1]
    return [i for a,z,_ in sorted(set(d.groups[d.primary(e)])) for i in d.decoder.disasm(d.image[a:z],a)]

def worker_case(mode,secondary,storage_ok=True):
    h=ChainHarness(mode,secondary);h.binder();h.phase='worker'
    archive=MEM+0x1A0000;stream=archive+0x1000;backing=archive+0x2000
    h.putq(h.root+0x85198,7)
    opens=[]
    def allocate():
        size=h.reg(UC_X86_REG_RCX)
        assert size in (0x70,0x98,0x38),hex(size)
        h.boundary('worker_allocate_'+hex(size),{0x70:archive,0x98:stream,0x38:backing}[size])
    h.stubs[BASE+0x3A5820]=allocate
    # Actual archive constructor, work-table reset, native explicit-name logic.
    for i,(ptr,count) in enumerate(((0x1FCA330,0x1FCA338),(0x1FCA340,0x1FCA348))):
        head=MEM+0x1B0000+i*0x100;h.putq(BASE+ptr,head)
        h.u.mem_write(head,q(head)*3);h.u.mem_write(head+0x19,b'\1');h.putq(BASE+count,0)
    def rawctor():
        obj=h.reg(UC_X86_REG_RCX);vt=MEM+0x1B2000
        h.putq(obj,vt)
        if h.readq(vt)==0:
            for offset in (0,0x78):h.stub(vt,offset,lambda:h.boundary('backing_destroy',0),'backing_destroy')
        h.boundary('stream_or_backing_ctor',obj)
    h.stubs[BASE+0x3A5120]=rawctor;h.stubs[BASE+0x3A4FC0]=rawctor
    def open_stream():
        sp=h.reg(UC_X86_REG_RSP)
        opens.append({'filename':h.read_sso(h.reg(UC_X86_REG_RDX)),
                      'mode':h.reg(UC_X86_REG_R8),'flags':h.reg(UC_X86_REG_R9),
                      'arg5':h.read32(sp+0x28),'arg6':h.read32(sp+0x30),'arg7':h.read32(sp+0x38)})
        h.boundary('storage_open',1)
    h.stubs[BASE+0x3A90C0]=open_stream
    def serialize():
        assert h.reg(UC_X86_REG_RCX)==archive
        h.boundary('full_world_serializer',0)
    h.stubs[BASE+0x2F7B50]=serialize
    for rva,label,result in ((0x3A50D0,'lock_enter',0),(0x3A5680,'lock_leave',0),
      (0x3A6A10,'storage_commit',int(storage_ok)),(0x3A83D0,'stream_transform',1),
      (0x3A55D0,'stream_destroy',0),(0x2EE0B0,'error_text_write',0),
      (0x39C260,'config_getter',MEM+0x1B4000),(0x3A0690,'config_sidecar',0),
      (0x39C440,'profile_getter',MEM+0x1B5000),(0x39D500,'profile_sidecar',0)):
        h.stubs[BASE+rva]=lambda label=label,result=result:h.boundary(label,result)
    # Archive destructor follows its real constructor-installed vtable;
    # stream/backing destruction and underlying frees remain explicit stubs.
    try:h.run(0x508CA0,args=(0,))
    except Exception:
        print('debug',hex(h.reg(UC_X86_REG_RIP)),[hex(i) for i in h.visits[-25:]],h.boundaries)
        raise
    assert len(opens)==1 and opens[0]['filename']=='mppush01.s14' and opens[0]['mode']==0
    assert h.read32(BASE+0x201EC2C)==int(storage_ok)
    assert h.read32(h.cache+8)==mode and h.read32(h.cache+0x3F0)==secondary
    assert not h.cache_mode_reads and not h.cache_mode_writes
    expected={0x508CA0,0x2EE740,0x2E24B0,0x2F4B20,0x2F7A10,0x2FCE40}
    assert expected<=set(h.visits),[hex(i) for i in expected-set(h.visits)]
    return {'result':'PASS','cache_mode':mode,'cache_secondary':secondary,'storage_ok':storage_ok,
      'opens':opens,'cache_mode_reads':h.cache_mode_reads,'cache_mode_writes':h.cache_mode_writes,
      'native_instructions':len(h.visits),'native_functions':[hex(i) for i in sorted(expected)],'boundaries':h.boundaries}

def main():
    rows=[worker_case(mode,secondary,ok) for mode in (0,1) for secondary in (0,1) for ok in (True,False)]
    functions=(0x426320,0x43BDA0,0x4AA200,0x508CA0,0x2EE740,0x2E24B0,0x2F7A10,0x2FCE40,0x465C10,0x835DD0,0x836DF0)
    listing={hex(at):[f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in function(at)] for at in functions}
    cache_pointer_xrefs={hex(at):[f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in function(at)
      if any(o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP and i.address+i.size+o.mem.disp==0x2025318 for o in i.operands)] for at in functions}
    report={'schema':'san14.checkpoint-push-native-worker-modes.v1','result':'PASS','cases':rows,
      'game_access':False,'save_files_written':False,'native_export_ready':False,
      'cache_pointer_xrefs':cache_pointer_xrefs,'static_instructions':listing,
      'scope':'Actual worker -> archive preparation/constructor -> explicit filename stream open branch -> finalizer. Underlying stream constructors, world serialization, storage, locks, sidecars and error text are explicit stubs.',
      'findings':['2F7A10 independently supplies stream mode0 (write); cache manager+8 is menu selection mode, not this stream mode.',
                  'Mode0/1 and secondary0/1 all produce the same bound explicit filename/write-open request in the tested path.',
                  '465C10 cleanup clears cache but does not reset mode+8 or secondary+3F0.',
                  'This is not proof that full world/sidecar/UI callees never inspect these fields; those transitive dependencies remain bounded explicitly.']}
    path=ROOT/('checkpoint_push_native_chain_modes_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'path':str(path)}))

if __name__=='__main__':main()
