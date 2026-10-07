"""Actual v014 FileWrite callsite in a private VM; never invokes Steam."""
from pathlib import Path
from datetime import datetime
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)]
from checkpoint_push_archive import isolated_definitions
n=isolated_definitions('private_checkpoint_load_shadow.py','publish_native_abi')
from unicorn.x86_const import *
from native_storage_read_abi_shadow import context_case
sha=lambda b:hashlib.sha256(b).hexdigest()
def case(value):
    u=n.new();stream=n.MEM+0x1000;holder=n.MEM+0x2000;storage=n.MEM+0x3000;vt=n.MEM+0x3100;chunks=n.MEM+0x4000;sizes=n.MEM+0x4100;buffer=n.MEM+0x50000
    context=n.MEM+0x6000;write=n.MEM+0x6100;u.mem_map(buffer,0x50000)
    data=(ROOT/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14').read_bytes();assert len(data)==274880
    assert sha(data)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    u.mem_write(buffer,data);u.mem_write(stream,b'svdexccSC03.s14\0'+n.q(15)+n.q(15));u.mem_write(stream+0x20,struct.pack('<I',2));u.mem_write(stream+0x30,n.q(buffer+len(data)));u.mem_write(stream+0x40,n.q(buffer));u.mem_write(stream+0x58,n.q(chunks));u.mem_write(stream+0x70,n.q(sizes));u.mem_write(chunks,n.q(buffer));u.mem_write(sizes,struct.pack('<I',len(data)))
    u.mem_write(holder,n.q(storage));u.mem_write(storage,n.q(vt));u.mem_write(vt,n.q(write));u.mem_write(n.BASE+0x123CB28,n.q(context))
    calls=[];tokens=[];cleanup=[]
    def getcontext(uc):tokens.append(uc.reg_read(UC_X86_REG_RCX)-n.BASE);assert tokens[-1]==0x18D08B8;n.ret(uc,holder)
    def publish(uc):
        self=uc.reg_read(UC_X86_REG_RCX);name=bytes(uc.mem_read(uc.reg_read(UC_X86_REG_RDX),16)).split(b'\0')[0].decode();pointer=uc.reg_read(UC_X86_REG_R8);amount=uc.reg_read(UC_X86_REG_R9)&0xffffffff
        assert self==storage and name=='svdexccSC03.s14' and pointer==buffer and amount==len(data) and bytes(uc.mem_read(pointer,amount))==data
        calls.append({'name':name,'size':amount,'sha256':sha(bytes(uc.mem_read(pointer,amount))),'return_rax':hex(value)});n.ret(uc,value)
    def close(uc):cleanup.append('stream_cleanup_3A6270');n.ret(uc)
    stubs={context:getcontext,write:publish,n.BASE+0x3A8720:lambda uc:n.ret(uc),n.BASE+0x3A6270:close}
    result=n.execute(u,0x3A6A10,(stream,),stubs);ok=bool(u.reg_read(UC_X86_REG_RAX)&255)
    assert ok==bool(value&255) and len(calls)==1 and len(tokens)==1 and cleanup==['stream_cleanup_3A6270'] and bytes(u.mem_read(buffer,len(data)))==data
    return {'case':'actual_FileWrite_AL_'+hex(value),'passed':True,'write_calls':calls,'native_wrapper_success':ok,'context_tokens':list(map(hex,tokens)),'actual_call_rva':'0x3a6ab2','native_instruction_count':len(result['visited']),'stubs':['ContextInit holder return','Steam v014 FileWrite','already prepared block aggregation3A8720','stream cleanup3A6270'],'file_written':False}
def main():
    cases=[context_case()]+[case(v) for v in (0,1,0x100,0xAA000001)]
    report={'schema':'san14.native-storage-publish-abi.v1','result':'PASS','cases':cases,'game_access':False,'Steam_API_called':False,'file_written':False,'captured_image_sha256':sha(n.d.image),'source_sha256':sha(Path(__file__).read_bytes()),'ABI':{'version':'STEAMREMOTESTORAGE_INTERFACE_VERSION014','context_token_rva':'0x18D08B8','context_init_iat_rva':'0x123CB28','write_vtable_offset':0,'write_call_rva':'0x3A6AB2','RCX':'interface object','RDX':'const char* basename','R8':'const void* complete serialized bytes','R9D':'int32 amount','return':'AL bool; upper bits ignored'},'limits':['Actual storage implementation is stubbed; no Steam publication/visibility is proved.','Game stream aggregation/cleanup are stubbed. Direct FileWrite publishes the already serialized fixed bytes, never repeats the stream serializer.','No native caller fence or file namespace ownership is established by this VM.']}
    out=ROOT/f'native_storage_publish_abi_shadow_{datetime.now():%Y%m%d-%H%M%S-%f}.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'result':'PASS','cases':len(cases),'path':str(out)}))
if __name__=='__main__':main()
