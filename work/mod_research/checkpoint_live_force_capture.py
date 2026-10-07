"""Read-only memory projection using an already-open caller-supplied reader.

No process constructor/discovery, writes, native call, file IO or CLI. This
projects current memory through the proven v92 field layout; no native stream
version, transform flag or save-file contents are observed or assumed.
"""
from copy import deepcopy
import hashlib
import re
import struct

from checkpoint_world_next_table_schema import (GAME_SHA256, SCHEMA as LAYOUT_SCHEMA,
    FIELD_LAYOUT, SLOT_COUNT, ROOT_OFFSET, RECORD_SIZE, SERIALIZED_OFFSETS,
    ForceTablePayload, compare_payloads)

SCHEMA='san14.live-force-layout-projection.v1'
ROOT_POINTER_RVA=0x1FCA1E0
ROOT_VTABLE_RVA=0x12AA6B0
WORLD_VTABLE_RVA=0x12AA638
FORCE_VTABLE_RVA=0x129FE58
SERIALIZER_RVA=0x214EC0
START,END=0x10,0x195
STACK=('CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState')
CODE_RANGES=(
    (0x214EC0,1581,'4885406358f0ae5580e366a5b7dd80db3a514ea5adfae2338ce03d9bac886823'),
    (0x1FF730,116,'5956d4c273ea433cc515df5422d2a949a8233b2fbba9e6a086fcc664172c959e'),
    (0x2003C0,308,'fecb260c54f48c40f5f19e338b22a9f311482484250308175fd687154b1ca839'),
    (0x1FFBB0,117,'6fc10a8687379092545f5d5affd0fa6262a4f25432edbda4d5ae99f29e8c0769'),
    (0x2FA970,339,'45577ed508eb93e61f36132659bd5ac53f1b6d97c9bbae195884326f27483b03'),
    (0x1FEF60,92,'ed12f0f136cf9662ef67ff248c1a3cae3b46bfd36d79519042012ddb24cc0d6f'),
    (0x1E39E0,116,'0f255f84c250b2136b6681524dca9742678759da53a2f3bed39a9da5a278b182'),
    (0x1FF930,116,'997485ca0507db0fbbd1402abb9686bcb72bce62e59bca68a41e28930fc1a99a'))


class ForceCaptureError(RuntimeError):pass


def require(ok,reason):
    if not ok:raise ForceCaptureError(reason)


def _ptr(value):
    require(type(value) is int and 0x10000<=value<0x7FFFFFFFFFFF and value%8==0,'invalid_pointer')
    return value


def _read(reader,address,size):
    require(type(address) is int and type(size) is int and 0<size<=0x1000 and
        0x10000<=address<0x7FFFFFFFFFFF-size,'invalid_read_extent')
    try:raw=reader.memory.read(address,size)
    except Exception as exc:raise ForceCaptureError('memory_read_failed') from exc
    require(type(raw) is bytes and len(raw)==size,'short_or_invalid_memory_read')
    return raw


def _q(reader,address):return struct.unpack('<Q',_read(reader,address,8))[0]


def _context(reader):
    require(reader.sha256==GAME_SHA256,'unsupported_build')
    m=reader.memory;base=_ptr(m.base)
    require(type(m.image_size) is int and m.image_size>ROOT_POINTER_RVA+8,'module_extent_too_small')
    require(type(reader.pid) is int and reader.pid>0,'invalid_caller_reader_pid')
    snapshot=deepcopy(reader.snapshot());states=deepcopy(reader.state_objects())
    require(type(snapshot) is dict and snapshot.get('exe_sha256')==GAME_SHA256 and
        snapshot.get('pid')==reader.pid and snapshot.get('state_stack')==list(STACK) and
        snapshot.get('in_player_strategy') is True,'not_stable_planning_context')
    require(type(states) in (list,tuple) and len(states)==5 and
        tuple(row[0] for row in states)==STACK,'unexpected_state_objects')
    addresses=tuple(_ptr(row[1]) for row in states)
    require(len(set(addresses))==5,'duplicate_state_objects')
    root=_ptr(_q(reader,base+ROOT_POINTER_RVA));world=_ptr(_q(reader,root+0x85130))
    require(_q(reader,root)==base+ROOT_VTABLE_RVA,'root_vtable_mismatch')
    require(_q(reader,world)==base+WORLD_VTABLE_RVA,'world_vtable_mismatch')
    date_bytes=_read(reader,world+0x34,8)
    year,month,day=struct.unpack_from('<HBB',date_bytes)
    date=snapshot.get('date',{});player=snapshot.get('player',{})
    require(1<=year<=9999 and 1<=month<=12 and 1<=day<=30 and date_bytes[6]<=51 and
        (date.get('year'),date.get('month'),date.get('day'))==(year,month,day) and
        player.get('force_id')==date_bytes[6],'world_snapshot_context_disagrees')
    phase=struct.unpack('<I',_read(reader,addresses[-1]+0x470,4))[0]
    mode=struct.unpack('<I',_read(reader,world+0x40,4))[0]
    busy=struct.unpack('<I',_read(reader,world+0x16A8,4))[0]
    require(phase==2 and mode==1 and not busy&0x100,'planning_phase_or_world_mode_busy')
    require(_q(reader,base+FORCE_VTABLE_RVA+0x28)==base+SERIALIZER_RVA,'force_serializer_vtable_changed')
    for rva,size,expected in CODE_RANGES:
        require(hashlib.sha256(_read(reader,base+rva,size)).hexdigest()==expected,
                'force_serializer_code_changed_'+hex(rva))
    return dict(snapshot=snapshot,pid=reader.pid,base=hex(base),image_size=m.image_size,
        root=hex(root),world=hex(world),state_objects=[dict(name=n,address=hex(a)) for n,a in states],
        user_phase=phase,world_mode=mode,world_busy_word=busy,date_context_hex=date_bytes.hex())


def _table(reader,context):
    base=int(context['base'],16);root=int(context['root'],16)
    require(_q(reader,base+ROOT_POINTER_RVA)==root,'root_changed')
    raw=_read(reader,root+ROOT_OFFSET,SLOT_COUNT*8)
    pointers=struct.unpack('<52Q',raw)
    for pointer in pointers:_ptr(pointer)
    require(len(set(pointers))==SLOT_COUNT,'aliased_force_slots')
    ordered=sorted(pointers)
    require(all(a+END<=b for a,b in zip(ordered,ordered[1:])),'overlapping_force_records')
    for pointer in pointers:
        require(_q(reader,pointer)==base+FORCE_VTABLE_RVA,'force_slot_vtable_mismatch')
    return pointers


def capture(reader):
    """Return a JSON-safe two-pass sample or raise; never retries or owns reader."""
    try:
        first=_context(reader);pointers=_table(reader,first)
        raw1=tuple(_read(reader,p+START,END-START) for p in pointers)
        middle=_context(reader);pointers2=_table(reader,middle)
        require(first==middle and pointers==pointers2,'context_or_table_changed_between_passes')
        raw2=tuple(_read(reader,p+START,END-START) for p in pointers2)
        final=_context(reader);pointers3=_table(reader,final)
        require(middle==final and pointers2==pointers3 and raw1==raw2,'memory_changed_during_sampling')
    except ForceCaptureError:raise
    except Exception as exc:raise ForceCaptureError('caller_reader_context_failed') from exc
    projected=tuple(b''.join(raw[o-START:o-START+n] for o,n in FIELD_LAYOUT) for raw in raw1)
    # This constructor describes already-projected bytes only. Do NOT call a
    # stream decoder with invented version/transform evidence for live memory.
    payload=ForceTablePayload(b''.join(projected))
    return dict(schema=SCHEMA,result='REPEATED_READS_STABLE',exe_sha256=GAME_SHA256,
        source='CALLER_SUPPLIED_MEMORY_READER',context=first,
        projection=dict(layout_schema=LAYOUT_SCHEMA,layout_archive_version=92,
            actual_stream_version_observed=None,actual_stream_auxiliary_flag_observed=None,
            actual_stream_transform_flag_observed=None,actual_stream_observed=False,
            native_serialization_executed=False,record_bytes=RECORD_SIZE,physical_slots=SLOT_COUNT),
        records={f'force_slot:{i}':row.hex() for i,row in enumerate(projected)},
        ordered_payload_hex=payload.ordered_payload.hex(),projection_sha256=payload.digest,
        pointer_diagnostics=dict(root=first['root'],world=first['world'],
            force_vtable=hex(int(first['base'],16)+FORCE_VTABLE_RVA),
            physical_slot_pointers=[hex(p) for p in pointers]),
        raw_memory=dict(start_offset=START,end_offset_exclusive=END,
            records={f'force_slot:{i}':row.hex() for i,row in enumerate(raw1)},
            nonprojected_offsets=[p for p in range(START,END) if p not in SERIALIZED_OFFSETS],
            nonprojected_bytes_irrelevant_to_gameplay_proven=False),
        stability=dict(payload_passes=2,context_samples=3,pointer_samples=3,atomic_snapshot=False,
            process_paused=False,can_miss_change_then_restore=True),
        game_writes=0,process_opened_by_helper=False,full_world_verified=False,
        native_load_authorized=False,scope='Current memory projected through proven v92 CForceData layout; not an observed native stream or full world.')


def _decode_sample(sample):
    require(type(sample) is dict and sample.get('schema')==SCHEMA and
        sample.get('result')=='REPEATED_READS_STABLE' and sample.get('exe_sha256')==GAME_SHA256,
        'unsupported_capture')
    keys={f'force_slot:{i}' for i in range(SLOT_COUNT)}
    def rows(values,width):
        require(type(values) is dict and set(values)==keys,'missing_or_extra_sample_slots')
        require(all(type(v) is str and re.fullmatch('[0-9a-f]{%d}'%(width*2),v) for v in values.values()),
                'invalid_sample_bytes')
        return tuple(bytes.fromhex(values[f'force_slot:{i}']) for i in range(SLOT_COUNT))
    projected=rows(sample.get('records'),RECORD_SIZE)
    raw_meta=sample.get('raw_memory',{})
    require(raw_meta.get('start_offset')==START and raw_meta.get('end_offset_exclusive')==END,'wrong_raw_extent')
    raw=rows(raw_meta.get('records'),END-START)
    require(all(b''.join(row[o-START:o-START+n] for o,n in FIELD_LAYOUT)==projected[i]
        for i,row in enumerate(raw)),'raw_projection_disagrees')
    payload=ForceTablePayload(b''.join(projected))
    require(sample.get('ordered_payload_hex')==payload.ordered_payload.hex() and
        sample.get('projection_sha256')==payload.digest,'projection_digest_mismatch')
    projection=sample.get('projection',{})
    require(projection.get('layout_schema')==LAYOUT_SCHEMA and projection.get('layout_archive_version')==92 and
        projection.get('actual_stream_observed') is False and projection.get('native_serialization_executed') is False and
        all(projection.get(k) is None for k in ('actual_stream_version_observed','actual_stream_auxiliary_flag_observed','actual_stream_transform_flag_observed')),
        'capture_must_not_claim_stream_observation')
    return payload,raw


def compare(before,after):
    """All-slot projection + retained nonprojected bytes; no permission outcome."""
    a,raw_a=_decode_sample(before);b,raw_b=_decode_sample(after)
    result=compare_payloads(a,b)
    nonprojected=[]
    for slot in range(SLOT_COUNT):
        for offset in range(START,END):
            if offset not in SERIALIZED_OFFSETS and raw_a[slot][offset-START]!=raw_b[slot][offset-START]:
                nonprojected.append(dict(physical_slot=slot,object_offset=offset,
                    before=raw_a[slot][offset-START],after=raw_b[slot][offset-START]))
    result.update(schema='san14.live-force-layout-comparison.v1',
        projection_only=True,actual_native_stream_compared=False,
        sampled_context_equal=before.get('context')==after.get('context'),
        pointer_diagnostics_equal=before.get('pointer_diagnostics')==after.get('pointer_diagnostics'),
        nonprojected_current_memory_equal=not nonprojected,nonprojected_memory_changes=nonprojected,
        nonprojected_bytes_irrelevant_to_gameplay_proven=False,atomic_snapshot=False)
    return result
