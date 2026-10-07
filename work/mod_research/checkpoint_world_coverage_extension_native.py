"""Actual archived x64 table/stream instructions in isolated Unicorn memory.

No GameReader, live imports, native storage, windows or game files. Original
3A9330/3A93E0/memcpy run without stubs in preallocated ordinary stream buffers.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P / 'python_deps'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_PROT_READ, UC_PROT_EXEC
from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RBX, UC_X86_REG_RSI, UC_X86_REG_RSP
from checkpoint_world_coverage_extension_schema import *

BASE = 0x7FF749440000
MEM = 0x300000000
STREAM = MEM + 0x1000
OBJECTS = MEM + 0x10000
BUFFER = MEM + 0x40000
SP = MEM + 0x9FFE8
ROOT = MEM + 0x100000
TABLE = ROOT + ROOT_OFFSET
VTABLE_RVA = 0x129FDF0
SERIALIZER = 0x216140
PARENT_START, PARENT_END = 0x2E7EFC, 0x2E7F1B
WRAPPER, LOOP = 0x2E1C00, 0x2E0660
q = lambda value: struct.pack('<Q', value)


def source_records():
    # Distinct payloads at every physical slot; arbitrary raw words are valid
    # for byte-symmetry testing and are not claimed legal gameplay values.
    return {i: struct.pack('<HBBHBB', i, (i*7)&255, (i*13)&255,
            (65535-i*17)&65535, (i*19)&255, (i*29)&255) for i in range(SLOT_COUNT)}


def machine(image, mode, payload=None, auxiliary=0):
    u = Uc(UC_ARCH_X86, UC_MODE_64)
    image_extent = (len(image)+4095)&~4095
    u.mem_map(BASE, image_extent); u.mem_write(BASE, image)
    u.mem_map(MEM, 0x200000)
    u.mem_write(BASE+0x1FCA1E0, q(ROOT))
    u.mem_protect(BASE, image_extent, UC_PROT_READ | UC_PROT_EXEC)
    records = source_records()
    raw = bytearray(b'\xA5'*(SLOT_COUNT*0x20))
    for i in range(SLOT_COUNT):
        raw[i*0x20:i*0x20+8] = q(BASE+VTABLE_RVA)
        raw[i*0x20+0x10:i*0x20+0x18] = records[i] if mode == 0 else b'\xCC'*8
    u.mem_write(OBJECTS, bytes(raw))
    u.mem_write(TABLE, b''.join(q(OBJECTS+i*0x20) for i in range(SLOT_COUNT)))
    u.mem_write(STREAM+0x20, struct.pack('<I', mode))
    u.mem_write(STREAM+0x30, q(BUFFER)+q(BUFFER+(len(payload) if mode == 1 else 0x10000)))
    u.mem_write(STREAM+0x88, struct.pack('<I',92)+bytes([auxiliary,0,0,0]))
    if payload is not None: u.mem_write(BUFFER,payload)
    u.reg_write(UC_X86_REG_RSP, SP)
    u.reg_write(UC_X86_REG_RBX, STREAM)
    u.reg_write(UC_X86_REG_RSI, MEM+0x800)
    events = {'serializer_calls':0, 'stream_reads':0, 'stream_writes':0, 'auxiliary_calls':0,
              'table_pointer_overrun':False}
    visited_fields = []
    def hit(uc,address,size,_):
        if address == BASE+SERIALIZER: events['serializer_calls'] += 1
        elif address == BASE+0x3A9330: events['stream_reads'] += 1
        elif address == BASE+0x3A93E0: events['stream_writes'] += 1
        elif address == BASE+0x3A6250:
            events['auxiliary_calls'] += 1
            uc.emu_stop()  # Explicitly unsupported path, never fake its behavior.
    for at in (SERIALIZER,0x3A9330,0x3A93E0,0x3A6250):
        u.hook_add(UC_HOOK_CODE,hit,begin=BASE+at,end=BASE+at)
    def overrun(uc,access,address,size,value,_):
        events['table_pointer_overrun']=True; uc.emu_stop()
    u.hook_add(UC_HOOK_MEM_READ,overrun,begin=TABLE+SLOT_COUNT*8,end=TABLE+SLOT_COUNT*8+7)
    u.emu_start(BASE+PARENT_START,BASE+PARENT_END,count=3000000)
    from unicorn.x86_const import UC_X86_REG_RIP
    stopped_at=u.reg_read(UC_X86_REG_RIP)-BASE
    after=bytes(u.mem_read(OBJECTS,len(raw)))
    changed_outside=[]
    for i in range(len(raw)):
        if not 0x10 <= i%0x20 <0x18 and raw[i]!=after[i]:changed_outside.append(i)
    cursor=struct.unpack('<Q',u.mem_read(STREAM+0x30,8))[0]-BUFFER
    status=struct.unpack('<I',u.mem_read(STREAM+0x50,4))[0]
    extracted={i:after[i*0x20+0x10:i*0x20+0x18] for i in range(SLOT_COUNT)}
    out=bytes(u.mem_read(BUFFER,cursor)) if mode==0 else None
    report={**events,'mode':mode,'auxiliary_flag':auxiliary,'native_return_al':u.reg_read(UC_X86_REG_RAX)&255,
        'stream_error':status,'buffer_bytes_consumed':cursor,'reached_parent_next_callsite':stopped_at==PARENT_END,
        'changed_nonpayload_object_bytes':changed_outside,'external_stubs':[],
        'input_buffer_unchanged':payload is None or bytes(u.mem_read(BUFFER,len(payload)))==payload}
    return report,out,extracted


def audit(image):
    require(hashlib.sha256(image).hexdigest()==IMAGE_SHA256,'captured_image_hash_changed')
    decoder=Cs(CS_ARCH_X86,CS_MODE_64)
    expected={0x2E7EFC:'mov r9, qword ptr [rip + 0x1ce22dd]',0x2E7F03:'mov r8d, 8',
        0x2E7F09:'add r9, 0x6d808',0x2E7F16:'call 0x2e1c00',0x2E1C13:'call 0x2e0660',
        0x2E0677:'mov dword ptr [rsp + 0x38], 0xbb9',0x2E06D9:'call qword ptr [rax + 0x28]',
        0x2E0709:'call qword ptr [rax + 0x28]',0x21614F:'cmp byte ptr [rdx + 0x8c], 0',
        0x216174:'lea rdx, [rdi + 0x10]',0x2161B0:'lea rdx, [rdi + 0x12]',
        0x2161EA:'lea rdx, [rdi + 0x13]',0x216222:'lea rdx, [rdi + 0x14]',
        0x21624C:'lea rdx, [rdi + 0x16]',0x216265:'add rdi, 0x17',
        0x216183:'call 0x3a9330',0x21618A:'call 0x3a93e0',
        0x2161BD:'call 0x3a9330',0x2161C4:'call 0x3a93e0',
        0x2161F7:'call 0x3a9330',0x2161FE:'call 0x3a93e0',
        0x216231:'call 0x3a9330',0x216238:'call 0x3a93e0',
        0x216259:'call 0x3a9330',0x216260:'call 0x3a93e0',
        0x216295:'call 0x3a9330',0x21629C:'call 0x3a93e0'}
    anchors=[]
    for at,wanted in expected.items():
        i=next(decoder.disasm(image[at:at+15],at))
        require(i.mnemonic+' '+i.op_str==wanted,'native_anchor_changed_'+hex(at))
        anchors.append({'rva':hex(at),'bytes':i.bytes.hex(),'instruction':wanted})
    # The exact captured vtable carries this serializer at virtual+28.
    require(struct.unpack_from('<Q',image,VTABLE_RVA+0x28)[0]==BASE+SERIALIZER,'captured_vtable_mismatch')
    return anchors


def main():
    image=(P/'game-runtime-image.bin').read_bytes();anchors=audit(image)
    cases=[];expected=validate_payload_records(source_records(),game_build_sha256=GAME_SHA256)
    write,frame,_=machine(image,0)
    require(frame==expected.frame() and write['native_return_al']==1 and not write['stream_error']
        and write['serializer_calls']==3001 and write['stream_writes']==18008
        and write['reached_parent_next_callsite'] and not write['changed_nonpayload_object_bytes'], 'native_write_mismatch')
    cases.append({'case':'all_3001_slots_actual_native_write','passed':True,**write})
    read,_,records=machine(image,1,frame)
    actual=validate_payload_records(records,game_build_sha256=GAME_SHA256,archive_mode=1)
    require(actual==expected and read['native_return_al']==1 and not read['stream_error']
        and read['stream_reads']==18008 and read['serializer_calls']==3001
        and read['input_buffer_unchanged'] and not read['changed_nonpayload_object_bytes'], 'native_read_roundtrip_mismatch')
    cases.append({'case':'all_3001_slots_actual_native_read','passed':True,**read})
    # Counterexample: native loop trusts zero count, wrapper tag alone returns1.
    zero,_,_=machine(image,1,struct.pack('<II',0,TABLE_TAG))
    require(zero['native_return_al']==1 and zero['stream_error']==0 and zero['serializer_calls']==0,
            'zero_count_counterexample_changed')
    cases.append({'case':'native_zero_count_is_not_complete_table','passed':True,**zero})
    # Counterexample: truncated final tag keeps the initialized expected tag;
    # native wrapper's AL alone can stay1, while stream error correctly records failure.
    short,_,_=machine(image,1,frame[:-1])
    require(short['stream_error']>0 and short['native_return_al']==1,
            'truncated_footer_counterexample_changed')
    cases.append({'case':'truncated_tag_requires_stream_error_check','passed':True,**short})
    large,_,_=machine(image,1,struct.pack('<I',SLOT_COUNT+1)+frame[4:-4]+bytes(8)+struct.pack('<I',TABLE_TAG))
    require(large['table_pointer_overrun'] and large['serializer_calls']==SLOT_COUNT,
            'oversized_count_counterexample_changed')
    cases.append({'case':'native_oversized_count_reaches_extra_table_pointer','passed':True,**large})
    aux,_,_=machine(image,0,auxiliary=1)
    require(aux['auxiliary_calls']==1 and not aux['reached_parent_next_callsite'],'auxiliary_path_not_rejected')
    cases.append({'case':'auxiliary_mode_explicitly_unsupported','passed':True,**aux})
    folder=P/'checkpoint_world_coverage_extension_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True,exist_ok=False);(folder/'synthetic-table-frame.bin').write_bytes(frame)
    report={'schema':'san14.cobjectdata.native-replay.v1','result':'PASS','cases':cases,'anchors':anchors,
        'payload_schema':expected.evidence(),'full_world_verified':False,'actual_game_table_captured':False,
        'game_access':False,'steam_access':False,'native_machine_code_replayed':True,
        'synthetic_object_records':True,'native_stream_functions_stubbed':False,
        'whole_world_deserializer_executed':False,'whole_archive_body_decoded':False,
        'native_table_frame_bytes':len(frame),'native_table_frame_sha256':hashlib.sha256(frame).hexdigest(),
        'source_sha256':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in (
            'game-runtime-image.bin','native-checkpoint-inventory.json','checkpoint-coverage-audit.json',
            'checkpoint_world_coverage_extension_native.py','checkpoint_world_coverage_extension_schema.py')},
        'limits':['Ordinary stream+8C=0/+8F=0, write mode0 and read mode1 with preallocated buffer only.',
                  'Table payload offsets are memory/isolated-stream offsets, never global .s14 offsets.',
                  'Offset14 durability meaning has separate historical evidence; other bytes remain opaque.',
                  'Native scalar field coverage does not certify post-load rebuilds, object legality or all world state.']}
    path=folder/'result.json';path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'result':'PASS','cases':len(cases),'path':str(path),'payload_bytes':TABLE_PAYLOAD_SIZE}))


if __name__=='__main__':main()
