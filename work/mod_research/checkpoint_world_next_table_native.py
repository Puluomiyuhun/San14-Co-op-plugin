"""Archived x64 CForceData table + nested helpers + real streams in Unicorn.

All data are synthetic; the image and provenance are workspace archives only.
No native function is stubbed. No process, window, Steam or game IO exists.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P/'python_deps'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_PROT_READ, UC_PROT_EXEC
from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RBX, UC_X86_REG_RSI, UC_X86_REG_RDI, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_RCX
from checkpoint_world_next_table_schema import *

BASE = 0x7FF749440000
MEM = 0x300000000
STREAM, OBJECTS, BUFFER, ROOT = MEM+0x1000, MEM+0x10000, MEM+0x40000, MEM+0x100000
TABLE = ROOT+ROOT_OFFSET
SP = MEM+0x9FFE8
STRIDE = 0x200  # Own allocation only; not a claim about native allocation size.
VTABLE_RVA, SERIALIZER = 0x129FE58, 0x214EC0
PARENT_START, PARENT_END = 0x2E7E80, 0x2E7E9F
WRAPPER, LOOP = 0x2E1600, 0x2DFD70
HELPERS = (0x1FF730,0x2003C0,0x1FFBB0,0x2FA970,0x1FEF60,0x1E39E0,0x1FF930)
q = lambda n: struct.pack('<Q', n)


def source_objects(seed=0):
    return {slot: bytes(((slot*37 + offset*17 + (offset>>8)*11 + seed*43)&255)
                       for offset in range(STRIDE)) for slot in range(SLOT_COUNT)}


def source_records(seed=0):
    return {slot: b''.join(raw[o:o+n] for o,n in FIELD_LAYOUT)
            for slot,raw in source_objects(seed).items()}


def machine(image, mode, payload=None, *, auxiliary=0, transform=0, version=ARCHIVE_VERSION, seed=0):
    u=Uc(UC_ARCH_X86,UC_MODE_64);extent=(len(image)+4095)&~4095
    u.mem_map(BASE,extent);u.mem_write(BASE,image);u.mem_map(MEM,0x200000)
    u.mem_write(BASE+0x1FCA1E0,q(ROOT));u.mem_protect(BASE,extent,UC_PROT_READ|UC_PROT_EXEC)
    original=bytearray()
    for slot,body in source_objects(seed).items():
        raw=bytearray(body if mode==0 else b'\xCC'*STRIDE)
        raw[:8]=q(BASE+VTABLE_RVA);original.extend(raw)
    u.mem_write(OBJECTS,bytes(original))
    u.mem_write(TABLE,b''.join(q(OBJECTS+i*STRIDE) for i in range(SLOT_COUNT)))
    u.mem_write(STREAM+0x20,struct.pack('<I',mode))
    u.mem_write(STREAM+0x30,q(BUFFER)+q(BUFFER+(len(payload) if mode==1 else 0x10000)))
    u.mem_write(STREAM+0x88,struct.pack('<I',version)+bytes([auxiliary,0,0,transform]))
    if payload is not None:u.mem_write(BUFFER,payload)
    u.reg_write(UC_X86_REG_RSP,SP);u.reg_write(UC_X86_REG_RBX,STREAM);u.reg_write(UC_X86_REG_RSI,MEM+0x800)
    events=dict(serializer_calls=0,stream_reads=0,stream_writes=0,auxiliary_calls=0,transform_calls=0,
                table_pointer_overrun=False,helper_calls={hex(h):0 for h in HELPERS})
    # These four actual date-helper stack copies preserve the corresponding
    # object bytes. Trace them by exact return address, never guess stack data.
    date_returns={0x2FA9BD:(0x4C,2),0x2FA9C4:(0x4C,2),0x2FAA09:(0x4E,1),0x2FAA10:(0x4E,1),
        0x2FAA55:(0x4F,1),0x2FAA5C:(0x4F,1),0x2FAAA1:(0x50,1),0x2FAAA8:(0x50,1)}
    traces={};current=[None];unknown=[]
    def hit(uc,address,size,_):
        at=address-BASE
        if at==SERIALIZER:
            ptr=uc.reg_read(UC_X86_REG_RCX);slot=(ptr-OBJECTS)//STRIDE
            require(ptr==OBJECTS+slot*STRIDE and 0<=slot<SLOT_COUNT,'wrong_serializer_object')
            current[0]=slot;events['serializer_calls']+=1;traces[slot]=[]
        elif at in HELPERS:events['helper_calls'][hex(at)]+=1
        elif at==0x3A6250:
            events['auxiliary_calls']+=1;uc.emu_stop()
        elif at==0x3A6570:
            events['transform_calls']+=1;uc.emu_stop()  # Unsupported transform, never stub success.
        elif at in (0x3A9330,0x3A93E0):
            events['stream_reads' if at==0x3A9330 else 'stream_writes']+=1
            pointer=uc.reg_read(UC_X86_REG_RDX);width=uc.reg_read(UC_X86_REG_R8)
            ret=struct.unpack('<Q',uc.mem_read(uc.reg_read(UC_X86_REG_RSP),8))[0]-BASE
            slot=current[0]
            if slot is not None and OBJECTS+slot*STRIDE<=pointer<OBJECTS+(slot+1)*STRIDE:
                traces[slot].append((pointer-OBJECTS-slot*STRIDE,width))
            elif ret in date_returns:
                field=date_returns[ret]
                require(width==field[1] and uc.reg_read(UC_X86_REG_RDI)==OBJECTS+slot*STRIDE+0x4C,
                        'date_helper_context_changed')
                traces[slot].append(field)
            elif ret not in (0x2DFDBD,0x2DFDC4,0x2E1651,0x2E166A):
                # The version<=91 conversion uses another local temporary,
                # deliberately outside this version-92 schema.
                unknown.append(dict(return_rva=hex(ret),width=width,slot=slot))
    for at in (SERIALIZER,0x3A9330,0x3A93E0,0x3A6250,0x3A6570,*HELPERS):
        u.hook_add(UC_HOOK_CODE,hit,begin=BASE+at,end=BASE+at)
    def overrun(uc,access,address,size,value,_):
        events['table_pointer_overrun']=True;uc.emu_stop()
    u.hook_add(UC_HOOK_MEM_READ,overrun,begin=TABLE+SLOT_COUNT*8,end=TABLE+SLOT_COUNT*8+7)
    u.emu_start(BASE+PARENT_START,BASE+PARENT_END,count=4000000)
    after=bytes(u.mem_read(OBJECTS,len(original)))
    changed_outside=[i for i in range(len(original)) if i%STRIDE not in SERIALIZED_OFFSETS and original[i]!=after[i]]
    cursor=struct.unpack('<Q',u.mem_read(STREAM+0x30,8))[0]-BUFFER
    status=struct.unpack('<I',u.mem_read(STREAM+0x50,4))[0]
    extracted={slot:b''.join(after[slot*STRIDE+o:slot*STRIDE+o+n] for o,n in FIELD_LAYOUT)
               for slot in range(SLOT_COUNT)}
    output=bytes(u.mem_read(BUFFER,cursor)) if mode==0 else None
    report={**events,'mode':mode,'archive_version':version,'auxiliary_flag':auxiliary,'transform_flag':transform,
        'native_return_al':u.reg_read(UC_X86_REG_RAX)&255,'stream_error':status,
        'buffer_bytes_consumed':cursor,'reached_parent_next_callsite':u.reg_read(UC_X86_REG_RIP)==BASE+PARENT_END,
        'changed_nonpayload_object_bytes':changed_outside,'external_stubs':[],
        'input_buffer_unchanged':payload is None or bytes(u.mem_read(BUFFER,len(payload)))==payload,
        'all_field_traces_match_schema':len(traces)==SLOT_COUNT and all(tuple(row)==FIELD_LAYOUT for row in traces.values()),
        'first_record_actual_fields':traces.get(0,[]),'unclassified_stream_calls':unknown}
    return report,output,extracted


def audit(image):
    require(hashlib.sha256(image).hexdigest()==IMAGE_SHA256,'captured_image_hash_changed')
    c=Cs(CS_ARCH_X86,CS_MODE_64)
    anchors={0x2E7E80:'mov r9, qword ptr [rip + 0x1ce2359]',0x2E7E87:'mov r8d, 4',
        0x2E7E8D:'add r9, 0xdca0',0x2E7E9A:'call 0x2e1600',0x2E1613:'call 0x2dfd70',
        0x2DFD87:'mov dword ptr [rsp + 0x38], 0x34',0x2DFDE9:'call qword ptr [rax + 0x28]',
        0x2DFE19:'call qword ptr [rax + 0x28]',0x214F1B:'call 0x1ff730',0x215083:'call 0x2003c0',
        0x215092:'call 0x1ff730',0x2150A1:'call 0x1ffbb0',0x2151D9:'call 0x2fa970',
        0x2003E1:'mov r14d, 5',0x2003F4:'mov esi, 7',0x200446:'mov esi, 7',
        0x2004C8:'add rbp, 0x1e',0x1FFBC5:'mov esi, 0x1f',0x21539E:'cmp dword ptr [rbx + 0x88], 0x5b',
        0x2153A7:'lea rdx, [rdi + 0x179]',0x2153B6:'lea rdx, [rdi + 0x178]',
        0x215413:'mov byte ptr [rdi + 0x178], bpl',0x21545A:'cmp dword ptr [rbx + 0x88], 0x12',
        0x215481:'cmp dword ptr [rbx + 0x88], 0x4a',0x2154B7:'cmp dword ptr [rbx + 0x88], 0x4c',
        0x3A93A1:'cmp byte ptr [rdi + 0x8f], 0',0x3A93B3:'call 0x3a6570',
        0x3A9459:'cmp byte ptr [rbx + 0x8f], r13b',0x3A946C:'call 0x3a6570'}
    result=[]
    for at,wanted in anchors.items():
        i=next(c.disasm(image[at:at+15],at));actual=i.mnemonic+' '+i.op_str
        require(actual==wanted,'native_anchor_changed_'+hex(at))
        result.append(dict(rva=hex(at),bytes=i.bytes.hex(),instruction=actual))
    require(struct.unpack_from('<Q',image,VTABLE_RVA+0x28)[0]==BASE+SERIALIZER,'vtable_serializer_changed')
    return result


def main():
    image=(P/'game-runtime-image.bin').read_bytes();anchors=audit(image)
    archive=json.loads((P/'checkpoint_push_archives/20261006-204306-581930/result.json').read_text(encoding='utf8'))
    require(archive['file_format_version']==ARCHIVE_VERSION,'archive_version_evidence_changed')
    cases=[];frames=[]
    for seed in (0,1):
        expected=validate_payload_records(source_records(seed),game_build_sha256=GAME_SHA256,archive_version=ARCHIVE_VERSION,transform_flag=0)
        write,frame,_=machine(image,0,seed=seed)
        require(frame==expected.frame() and write['native_return_al']==1 and not write['stream_error'] and
            write['serializer_calls']==SLOT_COUNT and write['stream_writes']==SLOT_COUNT*len(FIELD_LAYOUT)+2 and
            write['all_field_traces_match_schema'] and not write['unclassified_stream_calls'] and
            write['reached_parent_next_callsite'] and not write['changed_nonpayload_object_bytes'],'native_write_mismatch')
        cases.append(dict(case=f'all_52_slots_native_write_seed_{seed}',passed=True,**write));frames.append(frame)
        read,_,records=machine(image,1,frame,seed=seed)
        actual=validate_payload_records(records,game_build_sha256=GAME_SHA256,archive_version=ARCHIVE_VERSION,transform_flag=0,archive_mode=1)
        require(actual==expected and read['native_return_al']==1 and not read['stream_error'] and
            read['stream_reads']==SLOT_COUNT*len(FIELD_LAYOUT)+2 and read['all_field_traces_match_schema'] and
            not read['unclassified_stream_calls'] and not read['changed_nonpayload_object_bytes'] and
            read['input_buffer_unchanged'] and read['reached_parent_next_callsite'],'native_read_mismatch')
        cases.append(dict(case=f'all_52_slots_native_read_seed_{seed}',passed=True,**read))
    frame=frames[0]
    # A real old-version branch is non-symmetric for the current in-memory
    # fields. This schema must not silently reuse the same byte interpretation.
    old,old_frame,_=machine(image,0,version=91)
    old_read,_,old_records=machine(image,1,old_frame,version=91)
    changed=[]
    for slot,raw in source_records().items():
        changed += [(slot,SERIALIZED_OFFSETS[i]) for i,b in enumerate(raw) if b!=old_records[slot][i]]
    require(changed and set(offset for _,offset in changed)<={0x178,0x179} and
        not old['all_field_traces_match_schema'] and not old_read['all_field_traces_match_schema'] and
        len(old_frame)==FRAME_SIZE,'version91_counterexample_changed')
    cases.append(dict(case='native_version91_same_size_is_not_v92_schema',passed=True,
        write=old,read=old_read,changed_field_offsets=sorted(set(o for _,o in changed)),changed_bytes=len(changed)))
    zero,_,_=machine(image,1,struct.pack('<II',0,TABLE_TAG))
    require(zero['native_return_al']==1 and zero['stream_error']==0 and zero['serializer_calls']==0,'zero_count_changed')
    cases.append(dict(case='native_zero_count_is_not_complete_table',passed=True,**zero))
    short,_,_=machine(image,1,frame[:-1])
    require(short['native_return_al']==1 and short['stream_error']>0,'short_tag_changed')
    cases.append(dict(case='truncated_footer_al_success_requires_extent_and_error_checks',passed=True,**short))
    large,_,_=machine(image,1,struct.pack('<I',SLOT_COUNT+1)+frame[4:-4]+bytes(RECORD_SIZE)+struct.pack('<I',TABLE_TAG))
    require(large['table_pointer_overrun'] and large['serializer_calls']==SLOT_COUNT,'oversized_count_changed')
    cases.append(dict(case='native_oversized_count_reaches_extra_table_pointer',passed=True,**large))
    aux,_,_=machine(image,0,auxiliary=1)
    require(aux['auxiliary_calls']==1 and not aux['reached_parent_next_callsite'],'auxiliary_not_stopped')
    cases.append(dict(case='auxiliary_mode_explicitly_unsupported',passed=True,**aux))
    for mode in (0,1):
        transformed,_,_=machine(image,mode,frame if mode else None,transform=1)
        require(transformed['transform_calls']==1 and not transformed['reached_parent_next_callsite'],
            'transform_path_not_stopped')
        cases.append(dict(case=f'native_stream_transform_mode_{mode}_explicitly_unsupported',passed=True,**transformed))
    folder=P/'checkpoint_world_next_table_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    (folder/'synthetic-force-table-frame.bin').write_bytes(frame)
    report=dict(schema='san14.cforcedata.native-replay.v1',result='PASS',cases=cases,anchors=anchors,
        payload_schema=validate_payload_records(source_records(),game_build_sha256=GAME_SHA256,
            archive_version=ARCHIVE_VERSION,transform_flag=0).evidence(),game_access=False,steam_access=False,
        native_machine_code_replayed=True,native_functions_stubbed=False,synthetic_object_records=True,
        actual_game_table_captured=False,whole_world_deserializer_executed=False,whole_archive_body_decoded=False,
        full_world_verified=False,native_table_frame_bytes=len(frame),
        native_table_frame_sha256=hashlib.sha256(frame).hexdigest(),
        source_sha256={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in (
            'game-runtime-image.bin','native-checkpoint-inventory.json','checkpoint-coverage-audit.json',
            'checkpoint_push_archives/20261006-204306-581930/result.json',
            'checkpoint_world_next_table_schema.py','checkpoint_world_next_table_native.py')},
        limits=['Only ordinary version92 stream+8C=0/+8F=0, read1/write0, preallocated buffer.',
                'All scalar/array bytes stay opaque; serialization membership does not classify runtime relevance.',
                'Physical slots include0/inactive; no current-world capture or active-order list proof.',
                'Isolated table frame is not a claimed offset or decoder for a compressed .s14 body.'])
    path=folder/'result.json';path.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(dict(result='PASS',cases=len(cases),path=str(path),record_bytes=RECORD_SIZE,
        payload_bytes=TABLE_PAYLOAD_SIZE,stream_calls_per_record=len(FIELD_LAYOUT))))


if __name__=='__main__':main()
