"""Actual copied parser AND raw read over borrowed immutable bytes, offline only.

No game access, storage APIs, native allocations, stream close/destructor or
modification of legacy fixtures. This tests a parser-only borrowed stream shape;
it does NOT establish a supported native stream construction/destruction ABI.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)]
from checkpoint_push_archive import isolated_definitions
n=isolated_definitions('private_checkpoint_load_shadow.py','target_buffer_native')
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_RAX,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8

def sha(b):return hashlib.sha256(b).hexdigest()
def case(payload,valid=True,mutate=False,encrypted=False):
    u=n.new();header=n.MEM+0x1000;stream=n.MEM+0x2000;source=n.MEM+0x50000
    u.mem_map(source,0x50000);u.mem_write(source,payload)
    n.execute(u,0x2E32A0,(header,))
    u.mem_write(stream+0x20,struct.pack('<I',1))
    u.mem_write(stream+0x30,n.q(source+4)+n.q(source+len(payload)))
    u.mem_write(stream+0x88,payload[:4])
    # Open3A90C0 normally owns an allocated buffer at+40. It must remain zero
    # here: this is a borrowed parser stream, never close/destruct as an owner.
    u.mem_write(stream+0x8f,bytes([bool(encrypted)]))
    raw_calls=[];writes=[];source_writes=[];external=[]
    def code(uc,address,size,data):
        rva=address-n.BASE
        if rva==0x3A9330:raw_calls.append((uc.reg_read(UC_X86_REG_RDX),uc.reg_read(UC_X86_REG_R8)))
        if rva in (0x3A90C0,0x3A6340,0x3A55D0,0x3A6570):external.append(hex(rva))
    def write(uc,access,address,size,value,data):
        if n.BASE<=address<n.BASE+len(n.d.image):writes.append((hex(address-n.BASE),size))
        if source<=address<source+len(payload):source_writes.append((address-source,size))
    hc=u.hook_add(UC_HOOK_CODE,code);hw=u.hook_add(UC_HOOK_MEM_WRITE,write)
    # Native memcpy itself executes; no raw read or memcpy replacement.
    result=n.execute(u,0x2FAAD0,(header,stream))
    u.hook_del(hc);u.hook_del(hw)
    parsed=bytes(u.mem_read(header,0x150));cursor=n.u64(u,stream+0x30)-source
    ok=bool(u.reg_read(UC_X86_REG_RAX)&255);error=n.i32(u,stream+0x50)
    assert ok==valid and bool(error)!=valid,(ok,error,cursor)
    assert not writes and not source_writes and not external,(writes,source_writes,external)
    assert bytes(u.mem_read(source,len(payload)))==payload
    if valid:assert (parsed==expected)==(not mutate)
    if valid:assert cursor==294 and len(raw_calls)==189
    return {'case':'mutated_header_same_buffer' if mutate else 'full_verified_archive' if valid else f'truncated_{len(payload)}','passed':True,'parser_ok':ok,'stream_error':error,'consumed':cursor,'raw_read_calls':len(raw_calls),'raw_read_stubbed':False,'memcpy_stubbed':False,'global_writes':writes,'source_writes':source_writes,'file_open_close_calls':external,'parsed_sha256':sha(parsed),'copied_instructions':result['instructions']}

if __name__=='__main__':
    archive=ROOT/'checkpoint_push_archives/20261006-204306-581930'
    report=json.loads((archive/'result.json').read_text());payload=(archive/'mppush01.s14').read_bytes();expected=bytes.fromhex(report['parsed_header_hex'])
    assert len(payload)==274880 and sha(payload)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    cases=[case(payload)]
    changed=bytearray(payload);changed[4]^=1;cases.append(case(bytes(changed),mutate=True))
    for size in (4,64,293):cases.append(case(payload[:size],valid=False))
    out=ROOT/f'checkpoint_target_metadata_buffer_shadow_{datetime.now():%Y%m%d-%H%M%S-%f}.json'
    data={'schema':'san14.checkpoint-target-metadata-buffer-shadow.v1','result':'PASS','cases':cases,'archive_sha256':sha(payload),'source_sha256':sha(Path(__file__).read_bytes()),'captured_image_sha256':sha(n.d.image),'game_access':False,'production_buffer_adapter_implemented':False,'load_authorized':False,'limits':['Native parser2FAAD0 and raw Read3A9330/memcpy execute on a handcrafted borrowed stream in Unicorn. No storage re-open and source unchanged.','No proof yet of native borrowed-stream constructor/cleanup lifetime; production adapter remains absent. Never attach borrowed vector bytes to an owning stream then call its normal close/destructor.','Header identity is not complete world deserialization; later native file reads remain a separate identity boundary.']}
    out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({'result':'PASS','cases':len(cases),'report':str(out)}))
