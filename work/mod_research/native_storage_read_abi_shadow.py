"""Replay game's actual stream-open and v014 context factory in a private VM."""
from datetime import datetime
import json,struct,hashlib
from checkpoint_push_native_chain import ChainHarness,ROOT,BASE,MEM,sso,q
from checkpoint_push_native_chain_modes import function
from save_return_shadow_base import d
from unicorn.x86_const import *

def cstring(h,address):
    return bytes(h.u.mem_read(address,96)).split(b'\0',1)[0].decode('ascii')
def context_case():
    h=ChainHarness();holder=MEM+0x1B0000;user=MEM+0x1B1000;factory=MEM+0x1B2000;storage=MEM+0x1B3000
    h.putq(BASE+0x123CB30,user);h.putq(BASE+0x123CB00,factory);observed={}
    h.stubs[user]=lambda:h.ret(731)
    def make():
        observed.update(user=h.reg(UC_X86_REG_RCX),version=cstring(h,h.reg(UC_X86_REG_RDX)));h.ret(storage)
    h.stubs[factory]=make;h.run(0x2FCB90,args=(holder,))
    assert observed=={'user':731,'version':'STEAMREMOTESTORAGE_INTERFACE_VERSION014'}
    assert h.readq(holder)==storage
    return {'case':'native_interface_factory','result':'PASS','observed':observed,'native_instructions':len(h.visits),
      'stubs':['SteamAPI_GetHSteamUser','SteamInternal_FindOrCreateUserInterface']}

def stream_case(read_return,size_value=274880):
    h=ChainHarness();h.u.mem_map(MEM+0x200000,0x80000)
    stream=MEM+0x1A0000;name=MEM+0x1A1000;allocator=MEM+0x1A2000;allocvt=MEM+0x1A3000
    holder=MEM+0x1B0000;storage=MEM+0x1B1000;vt=MEM+0x1B2000
    context_stub=MEM+0x1C1000;size_stub=MEM+0x1C2000;read_stub=MEM+0x1C3000;alloc_stub=MEM+0x1C4000;buffer=MEM+0x200000
    h.u.mem_write(stream,bytes(24)+q(15));h.u.mem_write(name,sso('mppush01.s14'))
    h.putq(allocator,allocvt);h.putq(allocvt+0x28,alloc_stub)
    h.putq(BASE+0x123CB28,context_stub);h.putq(holder,storage);h.putq(storage,vt)
    h.putq(vt+0x78,size_stub);h.putq(vt+8,read_stub)
    contexts=[];sizes=[];reads=[];allocation=[];cleanup=[]
    h.stubs[BASE+0x18FB0]=lambda:h.ret(MEM+0x1B5000)
    h.stubs[BASE+0x838070]=lambda:h.ret(allocator)
    def getcontext():
        contexts.append(hex(h.reg(UC_X86_REG_RCX)-BASE));assert h.reg(UC_X86_REG_RCX)==BASE+0x18D08B8;h.ret(holder)
    def getsize():
        sizes.append({'self':hex(h.reg(UC_X86_REG_RCX)),'filename':cstring(h,h.reg(UC_X86_REG_RDX))})
        assert h.reg(UC_X86_REG_RCX)==storage;h.ret(size_value)
    def allocate():
        amount=h.reg(UC_X86_REG_RDX);allocation.append(amount);assert amount==size_value;h.ret(buffer)
    payload=bytes((i*11+29)&255 for i in range(max(0,size_value)))
    def fileread():
        reads.append({'self':hex(h.reg(UC_X86_REG_RCX)),'filename':cstring(h,h.reg(UC_X86_REG_RDX)),
          'buffer':hex(h.reg(UC_X86_REG_R8)),'bytes_requested':h.reg(UC_X86_REG_R9)&0xffffffff,'return_eax':read_return&0xffffffff})
        assert h.reg(UC_X86_REG_RCX)==storage and h.reg(UC_X86_REG_R8)==buffer and h.reg(UC_X86_REG_R9)==size_value
        if read_return>0:h.u.mem_write(buffer,payload[:min(read_return,size_value)])
        h.ret(read_return&0xffffffff)
    h.stubs.update({context_stub:getcontext,size_stub:getsize,read_stub:fileread,alloc_stub:allocate})
    for rva in (0x3AA730,0x3AA6A0):h.stubs[BASE+rva]=lambda:h.ret(0)
    def close():cleanup.append('3A5B60');h.ret(0)
    h.stubs[BASE+0x3A5B60]=close
    def extra(sp):
        h.putq(sp+0x28,0);h.putq(sp+0x30,0x7D000);h.putq(sp+0x38,0xFFFFFFFF)
    h.run(0x3A90C0,args=(stream,name,1,0),setup=extra)
    native_success=bool(h.reg(UC_X86_REG_RAX)&0xff)
    assert native_success==(size_value!=0 and read_return!=0)
    assert all(row['filename']=='mppush01.s14' for row in sizes+reads)
    assert len(reads)==int(size_value!=0)
    if size_value and read_return==size_value:
        assert bytes(h.u.mem_read(buffer,size_value))==payload
        unchanged=hashlib.sha256(h.u.mem_read(buffer,size_value)).hexdigest()==hashlib.sha256(payload).hexdigest()
    else:unchanged=None
    return {'case':'native_stream_read','result':'PASS','size':size_value,'read_return':read_return,
      'native_wrapper_reports_success':native_success,'full_buffer_unchanged_after_FileRead':unchanged,
      'context_tokens':contexts,'GetFileSize_calls':sizes,'FileRead_calls':reads,'allocations':allocation,'cleanup':cleanup,
      'native_instructions':len(h.visits),'limits':'Actual3A90C0/SSO control; Steam factory/interface, allocator, pointer-wrapper helpers and failure-close are explicit stubs.'}

def main():
    rows=[context_case()]+[stream_case(value) for value in (274880,1,0,-1)]+[stream_case(0,0)]
    report={'schema':'san14.native-storage-read-abi-shadow.v1','result':'PASS','cases':rows,
      'game_access':False,'Steam_API_called':False,'save_files_written':False,
      'captured_image_sha256':hashlib.sha256(d.image).hexdigest(),
      'static_instructions':{hex(at):[f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in function(at)] for at in (0x2FCB90,0x3A90C0)},
      'abi':{'context_token_rva':'0x18D08B8','context_init_iat_rva':'0x123CB28',
        'interface':'STEAMREMOTESTORAGE_INTERFACE_VERSION014','FileExists_vtable_offset':'0x68',
        'GetFileSize':{'vtable_offset':'0x78','call_rva':'0x3A918E','RCX':'interface this','RDX':'const char* filename','EAX':'int32 size'},
        'FileRead':{'vtable_offset':'0x08','call_rva':'0x3A9224','RCX':'interface this','RDX':'const char* filename','R8':'writable buffer','R9D':'int32 capacity','EAX':'int32 bytes returned'}},
      'findings':['Actual image selects v014; method offsets and argument registers are established by native instructions, not guessed from an SDK layout.',
        'The game wrapper only checks nonzero EAX. Its current control flow accepts synthetic short/negative reads. The new core instead requires exact full byte count and full-buffer identity.',
        'After successful FileRead,3A90C0 stores stream+90 and returns; it does not transform the raw FileRead buffer. Later stream/serializer transforms are outside this raw identity test.'],
      'official_semantics_source':'https://partner.steamgames.com/doc/api/ISteamRemoteStorage#FileRead',
      'official_semantics_summary':'FileRead returns an int32 byte count and zero on missing/read failure; it synchronously reads a binary file into the supplied buffer. GetFileSize returns an int32 byte size. This documentation supports count semantics, while the pinned game image establishes the v014 offsets.',
      'limits':['External API methods are explicit VM stubs. This does not prove Steam returned the real exported file.',
        'Synchronous reads may block the calling thread. Two-read equality is observation-time evidence, not atomicity across a subsequent world load.']}
    path=ROOT/('native_storage_read_abi_shadow_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'path':str(path),'game_access':False}))

if __name__=='__main__':main()
