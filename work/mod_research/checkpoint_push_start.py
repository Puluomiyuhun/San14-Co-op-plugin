"""Separate type0 push/export pilot for mppush01.s14. Default: read-only precheck.

--dry temporarily hooks/restores an inert callback and queries native FileExists.
--execute requires exact-DLL fixture and dry evidence; creates one durable intent,
queues native CSaveState and observes that exact state's worker/join/completion.
It issues no load or time-advance request. Return to the same planning state
must be observed; uncertain attempts are not retried.
"""
from pathlib import Path
from datetime import datetime
import argparse,ctypes as C,hashlib,json,os,shutil,struct,sys,time
from ctypes import wintypes as W
ROOT=Path(__file__).resolve().parent
REMOTE=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote')
TARGET=REMOTE/'mppush01.s14';SOURCE=REMOTE/'svdexSC34.s14'
SOURCE_SHA='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
INTENT=ROOT/'checkpoint_push_once.intent'
DLL=ROOT/'checkpoint_push_pilot.dll'
from checkpoint_push_contract import REPORT,decode,dry_ok,native_lifecycle_ok,complete_ok,completion_evidence,compare_known_coverage,read_std_string,pending_vector_valid
def load(path):return json.loads(Path(path).read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    with Path(path).open('x',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def process_birth(reader):
    k=reader.memory.k;ft=(W.FILETIME*4)();k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.GetProcessTimes.restype=W.BOOL
    assert k.GetProcessTimes(reader.memory.handle,*[C.byref(ft[i]) for i in range(4)]),'Cannot bind PID to process creation time'
    return (ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime
def file_sample(path):
    a=path.stat();data=path.read_bytes();b=path.stat()
    assert a.st_size==b.st_size==len(data) and a.st_mtime_ns==b.st_mtime_ns,'File changed while hashing'
    return {'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'mtime_ns':b.st_mtime_ns}
def existing_files():
    values={}
    for p in sorted(REMOTE.iterdir()):
        if p.name==TARGET.name:continue
        assert p.is_file() and not p.is_symlink(),'Unexpected non-file in remote save directory'
        value=file_sample(p);values[p.name]={'size':value['size'],'sha256':value['sha256']}
    return values

class MemoryPage(C.Structure):
    _fields_=[('BaseAddress',C.c_void_p),('AllocationBase',C.c_void_p),('AllocationProtect',W.DWORD),
              ('PartitionId',W.WORD),('RegionSize',C.c_size_t),('State',W.DWORD),('Protect',W.DWORD),('Type',W.DWORD)]
assert C.sizeof(MemoryPage)==48

def hook_pages(reader):
    k=reader.memory.k
    k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(MemoryPage),C.c_size_t]
    k.VirtualQueryEx.restype=C.c_size_t
    result={}
    for name,rva in (('user',0x12CC4A8+0x28),('save',0x12DC5F8+0x28)):
        info=MemoryPage()
        assert k.VirtualQueryEx(reader.memory.handle,reader.memory.base+rva,C.byref(info),C.sizeof(info))==C.sizeof(info)
        result[name]={'protect':info.Protect,'allocation_protect':info.AllocationProtect,'state':info.State,'type':info.Type}
    return result
def sample(reader,allow_target=False):
    from startup_identity_reader import capture_startup_context
    m=reader.memory;ctx=capture_startup_context(reader);business=reader.capture();reasons=[]
    def need(ok,reason):
        if not ok:reasons.append(reason)
    q=lambda p:struct.unpack('<Q',m.read(p,8))[0]
    i=lambda p:struct.unpack('<i',m.read(p,4))[0]
    k=m.k;k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)];k.CheckRemoteDebuggerPresent.restype=W.BOOL;debugger=W.BOOL()
    need(k.CheckRemoteDebuggerPresent(m.handle,C.byref(debugger)) and not debugger.value,'debugger_present_or_query_failed')
    need(reader.sha256=='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025','unsupported_exe')
    need(SOURCE.is_file() and sha(SOURCE)==SOURCE_SHA,'source34_changed')
    if not allow_target:need(not os.path.lexists(TARGET),'private_target_already_exists');need(not os.path.lexists(INTENT),'once_intent_already_exists')
    s=ctx['snapshot'];need(s['date']=={'year':203,'month':8,'day':11,'period':'中旬'},'not_checkpoint34_date')
    need(s['player']['force_id']==12 and s['player']['ruler_id']==666,'not_Zhang_Lu')
    need(s['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],'not_original_planning_stack')
    st=ctx['state_sample'];need(st is not None and st['phase_raw']==2 and st['ui_478_present'] and st['panel_618_present'],'not_ready_user_state')
    critical=business['critical_state'];need(critical['city']['garrison']==15204 and critical['district']['id']==11 and critical['district']['force_id']==12 and critical['district']['action_points']==18,'resources_differ')
    need(len(business['all_active_units'])==56 and not critical['officer_units'],'troops_differ')
    root=q(m.base+0x1FCA1E0);world=q(root+0x85130)
    need(q(root)==m.base+0x12AA6B0 and q(world)==m.base+0x12AA638,'root_world_type')
    need((i(world+0x16A8)&0x100)==0,'world_busy_flag')
    need(i(world+0x40)==1,'world_mode')
    cache=q(m.base+0x2025318);need(cache!=0 and i(cache+8) in (0,1) and i(cache+0x3EC)==-1 and i(cache+0x3F0)==0 and q(cache+0x18)==0,'cache_mode_or_pending_load')
    head=q(cache+0x10)
    cache_slots=struct.unpack('<120Q',m.read(cache+0x20,960))
    cache_entries=[index for index,pointer in enumerate(cache_slots) if pointer]
    need(head and q(head)==head and q(head+8)==head and cache_entries in ([],list(range(50))),'cache_not_supported_empty_list_shape')
    if cache_entries:
        need(i(cache+8)==1 and all(cache_slots[index]==cache_slots[0]+index*0x1e0 for index in range(50)),'cache_residue_stride_or_mode')
    state_manager=m.base+0x19E7310;pending=[q(state_manager+offset) for offset in (0x30,0x38,0x40)]
    need(pending_vector_valid(*pending),'pending_state_vector_invalid')
    allocators=[q(state_manager+offset) for offset in (0,0x28)];allocator_details=[]
    for allocator in allocators:
        valid=0x10000<=allocator<=0x00007FFFFFFFFFF7
        vtable=q(allocator) if valid else 0;need(valid and vtable==m.base+0x1283498,'state_allocator_type')
        allocator_details.append({'object':hex(allocator),'vtable':hex(vtable)})
    for offset,rva in ((0x28,0x12C840),(0x38,0x12C290),(0x40,0x8388D0),(0x48,0x1479B0)):
        need(q(m.base+0x1283498+offset)==m.base+rva,'state_allocator_method_'+hex(offset))
    need(q(m.base+0x12CC4A8+0x28)==m.base+0x3F9B00,'user_update_hook_present')
    need(q(m.base+0x12DC5F8+0x28)==m.base+0x4AA650,'save_update_hook_present')
    need(i(m.base+0x201ED10)==-1,'save_request_slot_busy')
    request_strings=[]
    for at in (m.base+0x201ED18,m.base+0x201ED38):
        try:
            value=read_std_string(m.read,at);request_strings.append(value);need(value['text']=='','save_request_string_busy')
        except ValueError as error:need(False,'save_request_string_invalid_'+str(error))
    for a in load(ROOT/'checkpoint_push_profile.json')['anchors']:
        data=bytes.fromhex(a['bytes']);need(m.read(m.base+a['rva'],len(data))==data,'code_anchor_'+hex(a['rva']))
    stack=q(state_manager+0x20);user=q(stack+32);game=q(stack+16)
    toolbar=q(user+0x478);panel=q(game+0x480);special=q(m.base+0x201EC70)
    need(i(toolbar+0x88)==-1 and i(game+0x47C)==0 and panel and i(panel+0x1B0)==0,'pending_menu_or_advance')
    need(all(q(user+o)==0 for o in (0x4A8,0x4B0,0x4B8)),'selection_not_empty')
    need(not special or i(special)==0,'special_context_active')
    need(i(m.base+0x1A38EC8+0x28)==0 and i(m.base+0x19E7510+0x13C)==1,'controls_not_resumed')
    for off,rva in ((0x18,0x3F5530),(0x20,0x3F5920),(0x58,0x3F7710),(0x60,0x3F7A70)):
        need(q(m.base+0x12CC4A8+off)==m.base+rva,'User_lifecycle_hook_present')
    need(ctx==capture_startup_context(reader) and business==reader.capture(),'sampling_changed')
    return {'result':'PASS' if not reasons else 'BLOCKED_PRECONDITIONS','reasons':reasons,'pid':reader.pid,'process_birth':process_birth(reader),'base':hex(m.base),
            'context':ctx,'business':business,'request_strings':request_strings,'pending_vector':{'count':pending[0],'capacity':pending[1],'pointer':hex(pending[2]),'allocators':allocator_details},'source34_sha256':sha(SOURCE),'target':str(TARGET),'intent':str(INTENT),
            'pinned_user':hex(user),'pinned_game':hex(game),'pinned_world':hex(world),'cache_mode':i(cache+8),'global_rng':i(m.base+0x18EB8B0)&0xffffffff,
            'hook_pages':hook_pages(reader),'cache_nonzero_indices':cache_entries,'cache_slots':[hex(x) for x in cache_slots],
            'game_writes':0,'scope':'Strict sampled source34 planning guard; not full-world equality.'}


def gate_evidence(path,dll_sha):
    from checkpoint_push_test import CASES,fingerprint
    value=load(path)
    assert value['result']=='PASS' and value['schema']=='san14.checkpoint-push-fixtures.v2'
    assert value['dll_sha256']==dll_sha and value['fixture_dll_sha256']==sha(ROOT/'checkpoint_push_fixture.dll')
    assert value['source_fingerprints']==fingerprint(),'Candidate sources differ from guard fixture evidence'
    assert [row['case'] for row in value['cases']]==list(CASES) and all(row['passed'] for row in value['cases'])
    assert value['contract_tests']>=40
    abi=load(ROOT/'checkpoint_push_bridge_fixture.json')
    assert abi['result']=='PASS' and abi['checks']==52 and not abi['game_process_access']
    chain=load(ROOT/'checkpoint_push_native_chain_contract_20261006-200959-178059.json')
    assert chain['classification']=='OFFLINE_NATIVE_CHAIN_VERIFIED_WITH_EXPLICIT_BOUNDARIES' and not chain['game_access']
    for row in chain['evidence']:
        p=ROOT/row['name'];assert sha(p)==row['sha256']
        proof=load(p);assert proof['result']=='PASS' and len(proof['cases'])==row['cases']
    residue=load(ROOT/'checkpoint_push_native_chain_cache_residue_20261006-202706-258698.json')
    assert residue['result']=='PASS' and len(residue['cases'])==9 and not residue['game_access']
    return sha(path)

def stop_observers(api,reader,report_address,stop_address):
    api.call_adapter(stop_address)
    deadline=time.monotonic()+10
    while True:
        value=decode(reader.memory.read(report_address,REPORT.size))
        if (not value['active_callbacks'] and not value['save_active_callbacks']) or time.monotonic()>=deadline:break
        time.sleep(.05)
    # A committed callback could publish the Save hook after the first Stop.
    # An abnormal native exit can leave unmatched pilot counters; never erase them.
    api.call_adapter(stop_address)
    return decode(reader.memory.read(report_address,REPORT.size))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--precheck',action='store_true');mode.add_argument('--dry',action='store_true');mode.add_argument('--execute',action='store_true')
    parser.add_argument('--fixture-evidence',type=Path);parser.add_argument('--dry-evidence',type=Path)
    parser.add_argument('--seconds',type=int,default=60)
    args=parser.parse_args();assert 3<=args.seconds<=120
    sys.path[:0]=[str(ROOT.parents[1]/'outputs/san14-link'),str(ROOT/'python_deps')]
    from battle_observer import BattleObserver
    from run_autonomous_pilot import ProcessAPI,pefile
    from checkpoint_live_capture import sample as capture_known
    run=ROOT/'checkpoint_push_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True,exist_ok=False)
    reader=api=None;report_address=cancel_address=stop_address=None;value=None
    try:
        reader=BattleObserver();before=sample(reader);save(run/'before.json',before)
        if not(args.dry or args.execute) or before['result']!='PASS':
            save(run/'result.json',before)
            print(json.dumps({'result':before['result'],'reasons':before['reasons'],'evidence':str(run/'result.json'),'game_writes':0},ensure_ascii=False));return
        assert args.fixture_evidence,'Exact binary fixtures required'
        dll_sha=sha(DLL);fixture_sha=gate_evidence(args.fixture_evidence,dll_sha)
        full_before=capture_known();save(run/'known-before.json',full_before)
        assert sample(reader)==before,'Planning changed before install'
        if args.execute:
            assert args.dry_evidence,'Need successful dry for the same binary and process lifetime'
            dry=load(args.dry_evidence)
            assert dry['result']=='PASS' and dry['mode']=='dry' and dry_ok(dry['adapter'])
            assert dry['dll_sha256']==dll_sha and dry['fixture_evidence_sha256']==fixture_sha
            for key in ('pid','process_birth','base','pinned_user','pinned_game','pinned_world','cache_mode','global_rng','cache_slots'):
                assert dry['before'][key]==before[key],('Dry attachment changed',key)
            dry_full=load(Path(args.dry_evidence).parent/'known-after.json')
            assert dry_full['objects']['records']==full_before['objects']['records']
            assert dry_full['objects']['global_rng']==full_before['objects']['global_rng']
            assert dry_full['objects']['world_rng_fields_hex']==full_before['objects']['world_rng_fields_hex']
            assert dry_full['tiles']['ordered_payload_hex']==full_before['tiles']['ordered_payload_hex']
            assert not os.path.lexists(INTENT) and not os.path.lexists(TARGET)
        copied=run/'checkpoint_push_pilot.dll';shutil.copyfile(DLL,copied);assert sha(copied)==dll_sha
        pe=pefile.PE(str(copied));exports={symbol.name.decode():symbol.address for symbol in pe.DIRECTORY_ENTRY_EXPORT.symbols if symbol.name};pe.close()
        assert all(name in exports for name in ('InstallCheckpointPush','CancelCheckpointPush','StopCheckpointPushObserver','CheckpointPushReport'))
        api=ProcessAPI(reader)
        api.call_adapter(api.load_library_address(),str(copied).encode('utf-16le')+b'\0\0')
        matches=[base for base,path in api.modules() if str(path).lower()==str(copied).lower()]
        assert len(matches)==1;module=matches[0]
        report_address=module+exports['CheckpointPushReport']
        cancel_address=module+exports['CancelCheckpointPush'];stop_address=module+exports['StopCheckpointPushObserver']
        def read_report():
            return decode(reader.memory.read(report_address,REPORT.size))
        def wide(path):
            data=str(path).encode('utf-16le')+b'\0\0';assert len(data)<=1024
            return data.ljust(1024,b'\0')
        config=struct.pack('<QIIII',0x53414E1450534832,2,int(args.execute),0xffffffff,0)+wide(INTENT)+wide(TARGET)
        assert len(config)==2072
        installed=api.call_adapter(module+exports['InstallCheckpointPush'],config)
        deadline=time.monotonic()+args.seconds;file_evidence={};last_file=None;same_since=None;samples=0;previous=None
        with (run/'trace.jsonl').open('x',encoding='utf8') as trace:
            while time.monotonic()<deadline:
                value=read_report();now=time.monotonic()
                if value!=previous:
                    trace.write(json.dumps({'elapsed':args.seconds-(deadline-now),'adapter':value})+'\n');trace.flush();previous=value
                if installed or value['status'] in (5,6,7) or value['save_observation_error']:break
                if args.dry and value['status']==3 and not value['active_callbacks']:break
                if args.execute and value['queue_calls'] and TARGET.is_file():
                    try:
                        current=file_sample(TARGET)
                        if current==last_file:samples+=1
                        else:last_file=current;same_since=now;samples=1
                        span=now-same_since
                        file_evidence={**current,'stable':samples>=3 and span>=1,'samples':samples,'span_seconds':span,'first_seen_after_queue':True}
                    except (OSError,AssertionError):last_file=None;samples=0;same_since=None;file_evidence={}
                if args.execute and value['status']==8 and not value['active_callbacks']:
                    if not native_lifecycle_ok(value) or file_evidence.get('stable'):break
                time.sleep(.05)
        value=read_report()
        # Restore observation on any timeout/failure, without cancelling a native
        # transaction past its atomic commitment. Never unload a pinned module.
        finished=(dry_ok(value) if args.dry else native_lifecycle_ok(value))
        if not finished:
            if value['status']==1:api.call_adapter(cancel_address)
            value=stop_observers(api,reader,report_address,stop_address)
        pages_after=hook_pages(reader)
        slots_after={name:struct.unpack('<Q',reader.memory.read(reader.memory.base+rva,8))[0]
                     for name,rva in (('user',0x12CC4A8+0x28),('save',0x12DC5F8+0x28))}
        hooks_restored=(pages_after==before['hook_pages'] and slots_after=={'user':reader.memory.base+0x3F9B00,'save':reader.memory.base+0x4AA650})
        after=full_after=None;capture_error=None
        if not value['active_callbacks'] and not value['save_active_callbacks']:
            try:
                after=sample(reader,allow_target=args.execute);save(run/'after.json',after)
                if after['result']=='PASS':
                    full_after=capture_known();save(run/'known-after.json',full_after)
            except BaseException as error:
                capture_error=str(error);save(run/'after-error.json',{'error':capture_error})
        identity_ok=(value['caller']==int(before['base'],0)+0x50B785 and value['state']==int(before['pinned_user'],0)
                     and value['pinned_world']==int(before['pinned_world'],0))
        details=None
        if args.execute:
            details=completion_evidence(value,after,file_evidence,full_before,full_after)
            passed=installed==0 and identity_ok and hooks_restored and INTENT.is_file() and complete_ok(value,after,file_evidence,full_before,full_after)
        else:
            passed=(installed==0 and identity_ok and hooks_restored and dry_ok(value) and after is not None and after['result']=='PASS'
                    and compare_known_coverage(full_before,full_after)['matched']
                    and full_before['save_files']==full_after['save_files']
                    and not os.path.lexists(TARGET) and not os.path.lexists(INTENT))
        result={'schema':'san14.checkpoint-push-result.v2','result':'PASS' if passed else 'INCOMPLETE_OR_UNCERTAIN_NO_AUTO_RETRY',
            'mode':'execute' if args.execute else 'dry','dll_sha256':dll_sha,'fixture_evidence':str(args.fixture_evidence),
            'fixture_evidence_sha256':fixture_sha,'before':before,'after':after,'adapter':value,'install_exit':installed,
            'file':file_evidence,'completion_evidence':details,'intent':str(INTENT),
            'native_save_complete':bool(passed and args.execute),'full_world_sync_proven':False,
            'inert_module_remains_until_exit':True,'load_performed':False,'native_worker_directly_called':False,
            'old_pilot_reenabled':False,'capture_error':capture_error}
        result.update(hooks_restored_from_memory=hooks_restored,hook_pages_after=pages_after,hook_slots_after=slots_after)
        save(run/'result.json',result)
        print(json.dumps({'result':result['result'],'mode':result['mode'],'evidence':str(run/'result.json'),
                          'native_save_complete':result['native_save_complete'],'adapter_status':value['status'],
                          'adapter_error':value['error'],'file':file_evidence},ensure_ascii=False))
    except BaseException as error:
        if api and report_address:
            try:
                value=stop_observers(api,reader,report_address,stop_address)
                save(run/'failure-adapter.json',value)
            except BaseException:pass
        if not (run/'result.json').exists():
            save(run/'result.json',{'result':'EXCEPTION_UNCERTAIN_NO_AUTO_RETRY','error':str(error),'adapter':value,'native_save_complete':False})
        raise
    finally:
        if api:api.close()
        if reader:reader.close()


if __name__=='__main__':main()
