"""Exact copied parser/copy/allocator-wrapper lifecycle; no game process access."""
from pathlib import Path
from datetime import datetime
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)]
from checkpoint_push_archive import isolated_definitions
n=isolated_definitions('private_checkpoint_load_shadow.py','target_native_lifecycle')
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
import capstone
sha=lambda b:hashlib.sha256(b).hexdigest()
PROFILE_VISITS=set()

def rip_target(pc):
    ins=next(n.d.decoder.disasm(n.d.image[pc:pc+15],pc))
    operands=[op for op in ins.operands if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP]
    assert len(operands)==1
    return {'instruction_rva':pc,'instruction':f'{ins.mnemonic} {ins.op_str}','bytes':bytes(ins.bytes).hex(),'target_rva':ins.address+ins.size+operands[0].mem.disp}

def allocator_bindings():
    # All RIP references consumed by the production guard are derived from the
    # captured instruction, not from manually added address/displacement text.
    sites={'TlsIndex':0x3AA594,'Epoch':0x3AA5AF,'Root':0x3AA64C,
           'Backing':0x3AA619,'Lock':0x3AA620,'OomCallback':0x3A587E,
           'HeapError':0x838926,'Vtable':0x8384B0}
    refs={name:rip_target(pc) for name,pc in sites.items()}
    assert refs['Epoch']['target_rva']==rip_target(0x3AA5BB)['target_rva']==rip_target(0x3AA5C7)['target_rva']==rip_target(0x3AA63B)['target_rva']
    assert refs['Root']['target_rva']==rip_target(0x3AA5D0)['target_rva']
    assert refs['HeapError']['target_rva']==rip_target(0x8389A4)['target_rva']==rip_target(0x8389C9)['target_rva']
    assert refs['Backing']['target_rva']==refs['Root']['target_rva']+0x60
    assert refs['Lock']['target_rva']==refs['Root']['target_rva']+0x68
    vt=refs['Vtable']['target_rva']
    refs['Allocate']={'vtable_offset':0x28,'target_rva':struct.unpack_from('<Q',n.d.image,vt+0x28)[0]-n.BASE}
    refs['Free']={'vtable_offset':0x58,'target_rva':struct.unpack_from('<Q',n.d.image,vt+0x58)[0]-n.BASE}
    refs['NoopOom']={'target_rva':struct.unpack_from('<Q',n.d.image,refs['OomCallback']['target_rva'])[0]-n.BASE}
    assert n.d.image[refs['NoopOom']['target_rva']:refs['NoopOom']['target_rva']+3]==bytes.fromhex('33c0c3')
    return refs

def parser(payload,expected):
    u=n.new();header=n.MEM+0x1000;stream=n.MEM+0x2000;source=n.MEM+0x50000
    u.mem_map(source,0x50000);u.mem_write(source,payload)
    u.mem_write(stream+0x20,struct.pack('<I',1));u.mem_write(stream+0x30,n.q(source+4)+n.q(source+len(payload)));u.mem_write(stream+0x88,payload[:4])
    stream_reads=set();stream_writes=set();image_writes=[];source_writes=[];forbidden=[]
    def read(uc,access,address,size,value,data):
        if stream<=address<stream+0x98:stream_reads.update(range(address-stream,address-stream+size))
    def write(uc,access,address,size,value,data):
        if stream<=address<stream+0x98:stream_writes.update(range(address-stream,address-stream+size))
        if n.BASE<=address<n.BASE+len(n.d.image):image_writes.append((address-n.BASE,size))
        if source<=address<source+len(payload):source_writes.append((address-source,size))
    def code(uc,address,size,data):
        if address-n.BASE in (0x3A5820,0x3A58B0,0x3A90C0,0x3A6340,0x3A55D0,0x3A4FC0,0x3A6570):forbidden.append(hex(address-n.BASE))
    hooks=[u.hook_add(UC_HOOK_MEM_READ,read),u.hook_add(UC_HOOK_MEM_WRITE,write),u.hook_add(UC_HOOK_CODE,code)]
    for rva,args in [(0x2E32A0,(header,)),(0x2FAAD0,(header,stream))]:
        r=n.execute(u,rva,args);PROFILE_VISITS.update(r['visited'])
    ok=bool(u.reg_read(UC_X86_REG_RAX)&255);parsed=bytes(u.mem_read(header,0x150));error=n.i32(u,stream+0x50)
    assert ok==(len(payload)>=294) and bool(error)!=(len(payload)>=294)
    if ok:assert parsed==expected and n.u64(u,stream+0x30)==source+294
    r=n.execute(u,0x50D20,(header+0x128,));PROFILE_VISITS.update(r['visited'])
    for hook in hooks:u.hook_del(hook)
    assert not image_writes and not source_writes and not forbidden
    assert n.u64(u,stream+0x40)==0 and n.u64(u,header+0x138)==0 and n.u64(u,header+0x140)==15
    assert bytes(u.mem_read(source,len(payload)))==payload
    return {'case':f'borrowed_parser_{len(payload)}','passed':True,'stream_read_offsets':[hex(x) for x in sorted(stream_reads)],'stream_write_offsets':[hex(x) for x in sorted(stream_writes)],'owning_stream_calls':forbidden,'image_writes':image_writes,'source_writes':source_writes,'stream_error':error,'header_sso_destroyed_without_heap_free':True}

def allocation_case(header_bytes,split,initial_fill=0,oom=False):
    u=n.new();source=n.MEM+0x1000;node=n.MEM+0x8000;head=n.MEM+0x2000;tail=n.MEM+0x2100;heap=n.MEM+0x3000;vt=n.MEM+0x3100
    provider_alloc=n.MEM+0x3200;provider_free=n.MEM+0x3210;lock=n.MEM+0x3220
    u.mem_write(source,header_bytes);u.mem_write(node,bytes([initial_fill])*0x160);u.mem_write(heap,n.q(vt));u.mem_write(vt+0x28,n.q(provider_alloc));u.mem_write(vt+0x58,n.q(provider_free))
    # Captured global contains the exact no-op328D20. Keep that legitimate
    # function for OOM proof: it returns zero and never enters game logic.
    # Actual3A5820/3A58B0 wrappers execute; only heap singleton lookup, virtual
    # provider allocate/free, and OS critical-section functions are substituted.
    for a,b in ((0x3A5820,0x3A58AC),(0x3A58B0,0x3A5908)):
        for i in n.d.decoder.disasm(n.d.image[a:b],a):
            if i.mnemonic in ('call','jmp') and i.operands[0].type==capstone.x86.X86_OP_MEM:
                op=i.operands[0]
                if op.mem.base==capstone.x86.X86_REG_RIP:u.mem_write(n.BASE+i.address+i.size+op.mem.disp,n.q(lock))
    allocations=[];frees=[];published=[];writes=set()
    def alloc(uc):
        assert uc.reg_read(UC_X86_REG_RCX)==heap and uc.reg_read(UC_X86_REG_RDX)==0x160
        allocations.append(0x160);n.ret(uc,0 if oom else node)
    def free(uc):
        assert uc.reg_read(UC_X86_REG_RCX)==heap;frees.append(uc.reg_read(UC_X86_REG_RDX));n.ret(uc)
    def watch(uc,access,address,size,value,data):
        if node+16<=address<node+0x160:writes.update(range(address-node-16,address-node-16+size))
    stubs={n.BASE+0x3AA580:lambda uc:n.ret(uc,heap),provider_alloc:alloc,provider_free:free,lock:lambda uc:n.ret(uc)}
    hw=u.hook_add(UC_HOOK_MEM_WRITE,watch)
    if split:
        r=n.execute(u,0x3A5820,(0x160,),stubs);PROFILE_VISITS.update(r['visited'])
        if oom:
            assert u.reg_read(UC_X86_REG_RAX)==0 and 0x3A588D in r['visited'] and 0x328D20 in r['visited'] and allocations==[0x160] and not frees
            u.hook_del(hw)
            return {'case':'allocator_null_with_exact_noop_oom_callback','passed':True,'allocation_sizes':allocations,'exact_noop_callback_rva':'0x328d20','callback_bytes':'33c0c3','payload_copy_called':False,'free_called':False,'native_2FD150_throw_path_called':False}
        assert u.reg_read(UC_X86_REG_RAX)==node
        published.append({'node':node,'ticket':77,'before_copy':True})
        u.mem_write(node,bytes(0x160));u.mem_write(node,n.q(head)+n.q(tail))
        r=n.execute(u,0x2E2A40,(node+16,source),stubs);PROFILE_VISITS.update(r['visited'])
    else:
        r=n.execute(u,0x2E0E80,(n.MEM+0x4000,head,tail,source),stubs);PROFILE_VISITS.update(r['visited']);assert u.reg_read(UC_X86_REG_RAX)==node
    u.hook_del(hw);payload=bytes(u.mem_read(node+16,0x150));before=bytes(u.mem_read(source,0x150))
    assert n.u64(u,node)==head and n.u64(u,node+8)==tail and allocations==[0x160] and not frees and before==header_bytes
    if not initial_fill or split:assert payload==header_bytes
    holes=[x for x in range(0x150) if x not in writes]
    if initial_fill and not split:assert all(payload[x]==initial_fill for x in holes)
    for rva,args in ((0x50D20,(node+0x138,)),(0x3A58B0,(node,))):
        r=n.execute(u,rva,args,stubs);PROFILE_VISITS.update(r['visited'])
    assert frees==[node]
    return {'case':('split' if split else 'original')+f'_copy_fill_{initial_fill}','passed':True,'allocation_sizes':allocations,'node_frees':len(frees),'source_unchanged':True,'allocator_wrappers_executed':True,'ticket_before_copy':bool(published),'payload_sha256':sha(payload),'native_copy_unwritten_offsets':[hex(x) for x in holes]}

def allocator_fast_path():
    refs=allocator_bindings()
    u=n.new();gs=n.MEM+0x10000;tls=n.MEM+0x11000;local=n.MEM+0x12000
    u.reg_write(UC_X86_REG_GS_BASE,gs);u.mem_write(gs+0x58,n.q(tls));u.mem_write(tls+8,n.q(local))
    u.mem_write(n.BASE+refs['TlsIndex']['target_rva'],struct.pack('<I',1));u.mem_write(local+0x10,struct.pack('<i',-2147483000));u.mem_write(n.BASE+refs['Epoch']['target_rva'],struct.pack('<i',-2147483100))
    r=n.execute(u,0x3AA580);PROFILE_VISITS.update(r['visited'])
    assert u.reg_read(UC_X86_REG_RAX)==n.BASE+refs['Root']['target_rva'] and 0x3AA5C2 not in r['visited'] and 0x3AA5DA not in r['visited']
    return {'case':'allocator_tls_initialized_fast_path','passed':True,'native_global_init_entered':False,'crt_init_header_entered':False,'returned_root_rva':hex(refs['Root']['target_rva']),'tls_index_rva':hex(refs['TlsIndex']['target_rva']),'global_epoch_rva':hex(refs['Epoch']['target_rva'])}

def anchors():
    # Full unwind fragments for every actually visited native body, including
    # helpers/memcpy/security-cookie checking; fixed data constants are added.
    from bisect import bisect_right
    ranges=set()
    for pc in PROFILE_VISITS:
        idx=bisect_right(n.d.starts,pc)-1
        if idx>=0 and pc<n.d.entries[idx][1]:
            root=n.d.primary(n.d.entries[idx]);ranges.update((a,z) for a,z,_ in n.d.groups[root]+[root])
        else:
            # A leaf can lack unwind metadata: bind each visited instruction.
            ins=next(n.d.decoder.disasm(n.d.image[pc:pc+15],pc));ranges.add((pc,pc+ins.size))
    # Bind original wrapper decomposition and allocator-singleton entry too.
    ranges.update(((0x2FD150,0x2FD1AD),(0x2E0E80,0x2E0ECE),(0x3AA580,0x3AA65E),
                   (0x2E32A0,0x2E336E),(0x50D20,0x50DA1),(0x838910,0x838AFD),(0x838CC0,0x838E5E),(0x8384B0,0x8384C6)))
    merged=[]
    for a,z in sorted(ranges):
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(z,merged[-1][1]))
        else:merged.append((a,z))
    return [{'rva':a,'bytes':n.d.image[a:z].hex()} for a,z in merged]

def main():
    archive=ROOT/'checkpoint_push_archives/20261006-204306-581930';a=json.loads((archive/'result.json').read_text());payload=(archive/'mppush01.s14').read_bytes();header=bytes.fromhex(a['parsed_header_hex'])
    assert sha(payload)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    prepared=bytearray(header);prepared[0x128:0x135]=b'mppush01.s14\0';struct.pack_into('<Q',prepared,0x138,12)
    cases=[parser(payload,header),parser(payload[:293],header)]
    for split,fill in ((False,0),(False,0xA5),(True,0),(True,0xA5)):cases.append(allocation_case(bytes(prepared),split,fill))
    cases += [allocation_case(bytes(prepared),True,oom=True),allocator_fast_path()]
    profile={'schema':'san14.checkpoint-target-metadata-native-anchors.v1','captured_image_sha256':sha(n.d.image),'exe_sha256':'42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025','anchors':anchors(),'allocator_bindings':allocator_bindings(),'native_adapter_live_verified':False}
    (ROOT/'checkpoint_target_metadata_native_profile.json').write_text(json.dumps(profile,indent=2)+'\n')
    lines=['// Generated by checkpoint_target_metadata_native_shadow.py after all VM cases pass.','struct Anchor { unsigned rva; const unsigned char* bytes; size_t size; };']
    for name,ref in profile['allocator_bindings'].items():lines.append(f'constexpr unsigned kAllocator{name}Rva=0x{ref["target_rva"]:X};')
    for index,anchor in enumerate(profile['anchors']):lines.append('static const unsigned char anchor_%d[]={%s};'%(index,','.join('0x'+anchor['bytes'][i:i+2] for i in range(0,len(anchor['bytes']),2))))
    lines.append('static const Anchor anchors[]={'+','.join('{0x%X,anchor_%d,sizeof(anchor_%d)}'%(anchor['rva'],index,index) for index,anchor in enumerate(profile['anchors']))+'};')
    (ROOT/'checkpoint_target_metadata_native_anchors.inc').write_text('\n'.join(lines)+'\n')
    out=ROOT/f'checkpoint_target_metadata_native_shadow_{datetime.now():%Y%m%d-%H%M%S-%f}.json'
    result={'schema':'san14.checkpoint-target-metadata-native-shadow.v1','result':'PASS','cases':cases,'profile_sha256':sha((ROOT/'checkpoint_target_metadata_native_profile.json').read_bytes()),'script_sha256':sha(Path(__file__).read_bytes()),'game_access':False,'limits':['Fixed version92/hash/header path only. The borrowed POD is not opened/closed/destructed as an owning stream.','Actual allocator/free wrappers execute against emulated provider and OS lock stubs. Real heap/thread/fence remain external prerequisites.','Native copy leaves padding unwritten; adapter zeroes its newly allocated private block before constructing the payload.']}
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':'PASS','cases':len(cases),'anchors':len(profile['anchors']),'anchor_bytes':sum(len(x['bytes'])//2 for x in profile['anchors']),'report':str(out)}))
if __name__=='__main__':main()
