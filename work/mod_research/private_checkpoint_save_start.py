"""Fixed mpckpt01.s14 export pilot. Default: read-only precheck.

--dry temporarily hooks/restores an inert callback and queries native FileExists.
--execute requires exact-DLL fixture and dry evidence; creates one durable intent,
queues native CSaveState and observes that exact state's worker/join/completion.
It does not load a file, replace an ordinary save, advance a date or retry.
"""
from pathlib import Path
from datetime import datetime
import argparse,ctypes as C,hashlib,json,os,shutil,struct,sys,time
from ctypes import wintypes as W
ROOT=Path(__file__).resolve().parent
REMOTE=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote')
TARGET=REMOTE/'mpckpt01.s14';SOURCE=REMOTE/'svdexSC34.s14'
SOURCE_SHA='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
INTENT=ROOT/'private_checkpoint_save_once.intent'
DLL=ROOT/'private_checkpoint_save_pilot.dll'
from private_checkpoint_save_contract import REPORT,decode,dry_ok,native_lifecycle_ok,complete_ok,read_std_string,pending_vector_valid
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
    cache=q(m.base+0x2025318);need(cache!=0 and i(cache+8)==0 and i(cache+0x3EC)==-1,'cache_mode_or_pending_load')
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
    for a in load(ROOT/'private_checkpoint_save_profile.json')['anchors']:
        data=bytes.fromhex(a['bytes']);need(m.read(m.base+a['rva'],len(data))==data,'code_anchor_'+hex(a['rva']))
    need(ctx==capture_startup_context(reader) and business==reader.capture(),'sampling_changed')
    return {'result':'PASS' if not reasons else 'BLOCKED_PRECONDITIONS','reasons':reasons,'pid':reader.pid,'process_birth':process_birth(reader),'base':hex(m.base),
            'context':ctx,'business':business,'request_strings':request_strings,'pending_vector':{'count':pending[0],'capacity':pending[1],'pointer':hex(pending[2]),'allocators':allocator_details},'source34_sha256':sha(SOURCE),'target':str(TARGET),'intent':str(INTENT),
            'game_writes':0,'scope':'Strict sampled source34 planning guard; not full-world equality.'}
def gate_evidence(path,dll_sha):
    from private_checkpoint_save_test import CASES,fingerprint
    evidence=load(path)
    assert evidence['result']=='PASS' and evidence['schema']=='san14.private-checkpoint-save-fixtures.v1'
    assert evidence['dll_sha256']==dll_sha and evidence['fixture_dll_sha256']==sha(ROOT/'private_checkpoint_save_fixture.dll'),'Binary differs from tested fixture evidence'
    assert evidence['source_fingerprints']==fingerprint(),'Source/profile/launcher changed since tests'
    assert [r['case'] for r in evidence['cases']]==list(CASES) and all(r['passed'] for r in evidence['cases'])
    assert evidence['contract_tests']>=22
    return sha(path)
def main():
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group();mode.add_argument('--precheck',action='store_true');mode.add_argument('--dry',action='store_true');mode.add_argument('--execute',action='store_true')
    p.add_argument('--fixture-evidence',type=Path);p.add_argument('--dry-evidence',type=Path);p.add_argument('--seconds',type=int,default=45);args=p.parse_args()
    # Permanent retirement after native type2 replacement advanced the game.
    # Deliberately before opening a process, creating a run, or loading any DLL.
    print(json.dumps({'result':'RETIRED_UNSAFE_STATE_ENTRY','game_access':False,
                      'reason':'412520 replaces the player state; the old pilot advanced the game. No mode is executable. Preserve all prior evidence and do not retry.',
                      'retirement':str(ROOT/'private_checkpoint_save_RETIRED.json')}))
    return
    assert 3<=args.seconds<=120
    sys.path[:0]=[str(ROOT.parent.parent/'outputs/san14-link'),str(ROOT/'python_deps')]
    from battle_observer import BattleObserver
    from run_autonomous_pilot import ProcessAPI,pefile
    run=ROOT/'private_checkpoint_save_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True,exist_ok=False)
    reader=None;api=None;report_address=None;cancel_address=None;stop_address=None;result_written=False;value=None
    try:
        reader=BattleObserver();before=sample(reader);save(run/'before.json',before)
        if not(args.dry or args.execute) or before['result']!='PASS':
            save(run/'result.json',before);result_written=True;print(json.dumps({'result':before['result'],'evidence':str(run/'result.json'),'reasons':before['reasons']},ensure_ascii=False));return
        assert args.fixture_evidence,'--dry/--execute requires exact-DLL fixture evidence'
        dll_sha=sha(DLL);fixture_sha=gate_evidence(args.fixture_evidence,dll_sha)
        if args.execute:
            assert args.dry_evidence,'--execute requires successful --dry evidence for this process and exact binary'
            dry=load(args.dry_evidence)
            assert dry['result']=='PASS' and dry['mode']=='dry' and dry['dll_sha256']==dll_sha and dry['fixture_evidence_sha256']==fixture_sha
            assert all(dry['before'][k]==before[k] for k in ('pid','process_birth','base')),'Dry evidence from another process lifetime'
            assert dry_ok(dry['adapter']) and dry['before']['business']==before['business'] and not os.path.lexists(INTENT)
        previous_files=existing_files();save(run/'existing-files-before.json',previous_files)
        copied=run/'private_checkpoint_save_pilot.dll';shutil.copyfile(DLL,copied);assert sha(copied)==dll_sha
        pe=pefile.PE(str(copied));exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name};pe.close()
        assert all(n in exports for n in ('InstallPrivateCheckpointSave','CancelPrivateCheckpointSave','StopPrivateCheckpointSaveObserver','PrivateCheckpointSaveReport'))
        api=ProcessAPI(reader);api.call_adapter(api.load_library_address(),str(copied).encode('utf-16le')+b'\0\0')
        modules=[base for base,path in api.modules() if str(path).lower()==str(copied).lower()];assert len(modules)==1;module=modules[0]
        report_address=module+exports['PrivateCheckpointSaveReport'];cancel_address=module+exports['CancelPrivateCheckpointSave'];stop_address=module+exports['StopPrivateCheckpointSaveObserver']
        def report():return decode(reader.memory.read(report_address,REPORT.size))
        def wide(path):
            data=str(path).encode('utf-16le')+b'\0\0';assert len(data)<=1024;return data.ljust(1024,b'\0')
        config=struct.pack('<QIIII',0x53414E1450535631,1,int(args.execute),0xffffffff,0)+wide(INTENT)+wide(TARGET);assert len(config)==2072
        install_exit=api.call_adapter(module+exports['InstallPrivateCheckpointSave'],config)
        deadline=time.monotonic()+args.seconds;file_evidence={};last_file=None;same_since=None;stable_count=0;last_report=None
        trace=(run/'trace.jsonl').open('x',encoding='utf8')
        try:
            while time.monotonic()<deadline:
                value=report();now=time.monotonic()
                if value!=last_report:trace.write(json.dumps({'elapsed':args.seconds-(deadline-now),'adapter':value})+'\n');trace.flush();last_report=value
                if value['status'] in (5,6,7):break
                if args.dry and value['status']==3 and not value['active_callbacks']:break
                if args.execute and value['status']==4 and value['save_observation_error']:break
                if args.execute and value['status']==4 and TARGET.is_file():
                    try:
                        current=file_sample(TARGET)
                        if current==last_file:stable_count+=1
                        else:last_file=current;same_since=now;stable_count=1
                        span=now-same_since
                        file_evidence={**current,'stable':stable_count>=3 and span>=1,'samples':stable_count,'span_seconds':span,'first_seen_after_queue':True}
                    except (OSError,AssertionError):last_file=None;stable_count=0;same_since=None;file_evidence={}
                if args.execute and native_lifecycle_ok(value) and file_evidence.get('stable'):
                    try:
                        probe=sample(reader,allow_target=True)
                        if probe['result']=='PASS':break
                    except RuntimeError:pass
                if args.execute and value['save_observation_done'] and not value['save_active_callbacks'] and not native_lifecycle_ok(value):break
                time.sleep(.05)
        finally:trace.close()
        value=report()
        if value['status']==1:api.call_adapter(cancel_address)
        if args.execute and not value['save_observation_done']:api.call_adapter(stop_address)
        value=report();after=None
        if not value['active_callbacks'] and not value['save_active_callbacks']:
            try:after=sample(reader,allow_target=args.execute);save(run/'after.json',after)
            except Exception as error:save(run/'after-error.json',{'error':str(error)})
        files_after=existing_files();save(run/'existing-files-after.json',files_after)
        files_equal=previous_files==files_after;business_equal=after is not None and before['business']==after['business']
        if file_evidence:save(run/'file.json',file_evidence)
        identity_ok=value['caller']==int(before['base'],0)+0x50B785 and value['installer_thread']!=value['executor_thread']
        passed=install_exit==0 and identity_ok and after is not None and after['result']=='PASS' and files_equal and business_equal
        if args.execute:passed=passed and complete_ok(value,after,file_evidence,business_equal,files_equal) and INTENT.is_file()
        else:passed=passed and dry_ok(value) and not os.path.lexists(TARGET) and not os.path.lexists(INTENT)
        result={'schema':'san14.private-checkpoint-save-result.v1','result':'PASS' if passed else 'INCOMPLETE_OR_UNCERTAIN_NO_AUTO_RETRY','mode':'execute' if args.execute else 'dry',
                'dll_sha256':dll_sha,'fixture_evidence':str(args.fixture_evidence),'fixture_evidence_sha256':fixture_sha,
                'before':before,'after':after,'adapter':value,'install_exit':install_exit,'file':file_evidence,
                'sampled_business_unchanged':business_equal,'existing_files_unchanged':files_equal,'intent':str(INTENT),
                'native_save_complete':bool(passed and args.execute),'full_world_sync_proven':False,'inert_module_remains_until_exit':True,
                'load_performed':False,'native_worker_directly_called':False}
        save(run/'result.json',result);result_written=True
        print(json.dumps({'result':result['result'],'evidence':str(run/'result.json'),'native_save_complete':result['native_save_complete'],'file':file_evidence},ensure_ascii=False))
    except BaseException as error:
        if api and report_address:
            try:
                value=decode(reader.memory.read(report_address,REPORT.size))
                if value['status']==1 and cancel_address:api.call_adapter(cancel_address)
                if stop_address:api.call_adapter(stop_address)
                value=decode(reader.memory.read(report_address,REPORT.size));save(run/'failure-adapter.json',value)
            except BaseException:pass
        if not result_written:save(run/'result.json',{'result':'EXCEPTION_UNCERTAIN_NO_AUTO_RETRY','error':str(error),'adapter':value,'native_save_complete':False})
        raise
    finally:
        if api:api.close()
        if reader:reader.close()
if __name__=='__main__':main()
