"""Read-only observation contract for one bounded native Save/army scope pack.

This module never attaches, patches, starts or advances a game. An observer
must establish its own process/code identity and safe debugger lifecycle.
These records and analyses are diagnostics, never a save/export permission.
"""
import hashlib
import json

SCHEMA = 'san14.a-save-native-coordination.events.v1'
ARCHIVE_SHA256 = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
GAME_SHA256 = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
ARMY_MANAGER_RVA = 0x1A24CF0
EVENTS = (
    dict(event='save_scope_enter', rva=0x2F7C28,
         bytes16='e80301ffff488b4b10837950007414b8', instruction='call 0x2e7d30',
         capture=('rsp','rcx','rdx','archive_stream'),
         identity='rcx=archive; rdx=stream; read QWORD[archive+0x10] as archive_stream; require equality'),
    dict(event='save_scope_return', rva=0x2F7C2D,
         bytes16='488b4b10837950007414b8bdfeffffba', instruction='mov rcx, qword ptr [rbx + 0x10]',
         capture=('rsp','rbx'), identity='same tid/rsp as Save enter; rbx retains that archive'),
    dict(event='army_worker_enter', rva=0x16C1A0,
         bytes16='48895c2410564883ec20488b5108488b', instruction='mov qword ptr [rsp + 0x10], rbx',
         capture=('rsp','rcx','stack_return'),
         identity='rcx=base+0x1A24CF0; read QWORD[rsp] as stack_return'),
    dict(event='army_worker_return', rva=0x16C2B7,
         bytes16='c3cccccccccccccccc4883ec28e8174f', instruction='ret',
         capture=('rsp','stack_return'),
         identity='before ret: same tid/rsp and QWORD[rsp] as army enter; native epilogue already balanced'),
)
BY_EVENT = {e['event']: e for e in EVENTS}
PROFILE_ID = hashlib.sha256(json.dumps(dict(schema=SCHEMA, events=EVENTS,
    archive_sha256=ARCHIVE_SHA256, game_sha256=GAME_SHA256), sort_keys=True,
    separators=(',', ':')).encode('ascii')).hexdigest()


def contract():
    """Serializable profile. Four execution sites fit one HW breakpoint pack."""
    return dict(schema=SCHEMA, profile_id=PROFILE_ID, events=EVENTS,
        game_sha256=GAME_SHA256, archive_sha256=ARCHIVE_SHA256,
        header_required=('pid','birth','base','run_id','capture_complete'),
        record_required=('seq','event','rva','thread','rsp'),
        event_record_fields=dict(save_scope_enter=('archive','stream','archive_stream'),
            save_scope_return=('rbx',),army_worker_enter=('manager','return_pc'),
            army_worker_return=('return_pc',)),
        optional_context=('date','state_names','save_state','save_phase','root','world',
                          'army_active','pending_count','working_count','timestamp_ns'),
        rules=[
            'Records use contiguous debugger-delivery seq values starting at 1; seq is shared by all observed threads. Nonzero lost_events is incomplete evidence.',
            'All four anchors must be validated in the currently attached supported process; archive bytes do not prove a live module identity.',
            'Capture pre-instruction register state. Hardware execution hits are not after-instruction events.',
            'Save rsp is before the CALL and after its return. QWORD[rsp] is a local-frame value here, not the Save caller return address.',
            'Army rsp is at function entry and immediately before RET. Record QWORD[rsp] at both sites.',
            'A read failure is explicit snapshot_error; never replace an unreadable pointer with zero or discard that event.',
            'capture_complete describes the observer lifecycle only. It does not prove whole-game exclusion or absence of uninstrumented writers.',
            'Attach-time already-running scopes, missing returns, exceptions, event drops or lost threads remain incomplete evidence.',
            'An overlapping function span is not a demonstrated simultaneous field read/write or corrupted native save.',
        ], production_permit=False, automatically_save_or_advance=False)


def validate_archive(image):
    if hashlib.sha256(image).hexdigest()!=ARCHIVE_SHA256:
        raise ValueError('unsupported fixed archive')
    for e in EVENTS:
        if image[e['rva']:e['rva']+16].hex()!=e['bytes16']:
            raise ValueError('anchor mismatch: '+e['event'])
    return contract()


def _number(value):
    if isinstance(value, bool) or not isinstance(value,(int,str)): raise ValueError('nonintegral address/identity')
    return int(value,0) if isinstance(value,str) else int(value)


def _analyze_trace(trace):
    """Pair raw observer records without granting a coordination/drain permit.

    Inputs may use decimal integers or 0x-prefixed strings for registers. Header
    PID/birth/base is the observer's immutable attachment identity. This is an
    offline parser, so it reports the declared binding, not independently
    verified debugger instrumentation or runtime source provenance.
    """
    issues=[];saves=[];workers=[];active_save={};active_worker={};counts={k:0 for k in BY_EVENT}
    def issue(reason,seq=None):issues.append(dict(reason=reason,seq=seq))
    try:
        if trace.get('schema')!=SCHEMA or trace.get('profile_id')!=PROFILE_ID:raise ValueError('schema/profile mismatch')
        pid,birth,base=(_number(trace[k]) for k in ('pid','birth','base'))
        if pid<=0 or birth<=0 or base<0x10000 or base>0x7fffffffffff-0x2400000:raise ValueError('invalid attachment identity')
    except (KeyError,ValueError,TypeError,OverflowError) as exc:
        return dict(classification='INVALID_CAPTURE',issues=[dict(reason=str(exc))],production_permit=False,full_writer_exclusion=False)
    if trace.get('capture_complete') is not True:issue('capture lifecycle incomplete')
    for error in trace.get('capture_errors',[]):issue('observer error: '+str(error))
    previous=0
    for row in trace.get('events',[]):
        seq=None
        try:
            seq=_number(row['seq']);tid=_number(row['tid']);name=row['event'];spec=BY_EVENT[name]
            if seq!=previous+1 or tid<=0:raise ValueError('noncontiguous sequence or invalid tid')
            previous=seq
            if _number(row.get('lost_events',0))!=0:raise ValueError('observer declared lost events')
            if _number(row['rip'])!=base+spec['rva']:raise ValueError('event source address mismatch')
            if row.get('snapshot_error'):raise ValueError('snapshot failed: '+str(row['snapshot_error']))
            rsp=_number(row['rsp'])
            if rsp<0x10000 or rsp%8 or rsp>0x7fffffffffff:raise ValueError('invalid stack address')
            values={k:_number(row[k]) for k in spec['capture']}
            counts[name]+=1
            if name=='save_scope_enter':
                if tid in active_save:raise ValueError('nested/repeated Save entry on same thread')
                if values['rcx']<0x10000 or values['rdx']<0x10000 or values['rdx']!=values['archive_stream']:
                    raise ValueError('Save archive/stream binding differs')
                active_save[tid]=dict(tid=tid,enter_seq=seq,rsp=rsp,archive=values['rcx'],stream=values['rdx'])
            elif name=='save_scope_return':
                start=active_save.get(tid)
                if not start:raise ValueError('unmatched Save return')
                if rsp!=start['rsp'] or values['rbx']!=start['archive']:raise ValueError('Save return stack/archive differs')
                saves.append(dict(start,return_seq=seq));del active_save[tid]
            elif name=='army_worker_enter':
                if tid in active_worker:raise ValueError('nested/repeated army entry on same thread')
                if values['rcx']!=base+ARMY_MANAGER_RVA or values['stack_return']<0x10000:
                    raise ValueError('army manager/caller binding differs')
                active_worker[tid]=dict(tid=tid,enter_seq=seq,rsp=rsp,stack_return=values['stack_return'])
            else:
                start=active_worker.get(tid)
                if not start:raise ValueError('unmatched army return; possible scope active before attach')
                if rsp!=start['rsp'] or values['stack_return']!=start['stack_return']:raise ValueError('army return stack/caller differs')
                workers.append(dict(start,return_seq=seq));del active_worker[tid]
        except (KeyError,ValueError,TypeError,OverflowError) as exc:issue(str(exc),seq)
    for kind,active in (('Save',active_save),('army',active_worker)):
        for value in active.values():issue(kind+' entry has no matched return',value['enter_seq'])
    overlaps=[]
    for save in saves:
        for worker in workers:
            if max(save['enter_seq'],worker['enter_seq'])<min(save['return_seq'],worker['return_seq']):
                overlaps.append(dict(save_enter=save['enter_seq'],save_return=save['return_seq'],
                    worker_enter=worker['enter_seq'],worker_return=worker['return_seq'],
                    different_threads=save['tid']!=worker['tid']))
    if issues:classification='INCOMPLETE_OR_INCONSISTENT_CAPTURE'
    elif not saves:classification='INCONCLUSIVE'
    elif overlaps:classification='WORKER_SCOPE_OVERLAP_OBSERVED'
    else:classification='NO_WORKER_SCOPE_OVERLAP_OBSERVED'
    return dict(classification=classification,declared_attachment=dict(pid=pid,birth=birth,base=base),
        counts=counts,save_scopes=saves,worker_scopes=workers,overlaps=overlaps,issues=issues,
        original_events_preserved=True,production_permit=False,full_writer_exclusion=False,
        actual_read_write_race_proved=False,native_save_corruption_proved=False,
        limit='Observation of paired scopes only; no overlap observed is not exclusion, and overlapping spans are not a proven field-access race.')


def analyze(rows, metadata):
    """Observer API: rows:list[dict], metadata with pid/birth/base/run_id.

    Record fields follow contract().event_record_fields. Per-record attachment
    fields are optional when the metadata event is fixed; any supplied value
    must match. No record is silently dropped. `capture_complete` and
    `capture_errors` are observer lifecycle evidence, not native idle/drain flags.
    """
    errors=[];normalized=[]
    try:
        if not isinstance(rows,list) or not isinstance(metadata,dict):raise ValueError('rows/metadata shape')
        pid,birth,base=(_number(metadata[k]) for k in ('pid','birth','base'))
        run_id=metadata['run_id']
        if not isinstance(run_id,str) or not run_id or len(run_id)>512:raise ValueError('invalid run_id')
        if metadata.get('profile_id',PROFILE_ID)!=PROFILE_ID:raise ValueError('declared profile differs')
        capture_errors=metadata.get('capture_errors',[])
        if not isinstance(capture_errors,list):raise ValueError('capture_errors must be a list')
    except (KeyError,TypeError,ValueError) as exc:
        return dict(classification='INVALID_CAPTURE',issues=[dict(reason=str(exc))],production_permit=False,full_writer_exclusion=False)
    for index,row in enumerate(rows):
        try:
            for key,value in (('pid',pid),('birth',birth),('base',base),('run_id',run_id)):
                if key in row and (row[key] if key=='run_id' else _number(row[key]))!=value:
                    raise ValueError('record attachment differs: '+key)
            item=dict(row);item['tid']=row['thread'];item['rip']=base+_number(row['rva'])
            if row['event']=='save_scope_enter':item.update(rcx=row['archive'],rdx=row['stream'])
            if row['event']=='army_worker_enter':item.update(rcx=row['manager'],stack_return=row['return_pc'])
            if row['event']=='army_worker_return':item.update(stack_return=row['return_pc'])
            normalized.append(item)
        except (KeyError,TypeError,ValueError) as exc:
            errors.append('record index '+str(index)+': '+str(exc))
    trace=dict(schema=SCHEMA,profile_id=PROFILE_ID,pid=pid,birth=birth,base=base,
        capture_complete=metadata.get('capture_complete',False),
        capture_errors=capture_errors+errors,events=normalized)
    result=_analyze_trace(trace);result['run_id']=run_id;result['input_record_count']=len(rows)
    result['decoded_record_count']=len(normalized)
    return result
