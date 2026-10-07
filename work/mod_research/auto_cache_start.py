"""Native directory-cache initialization pilot. Default read-only; --dry installs an inert one-shot callback.

--execute performs only native 328D20 -> 836EF0 on the user update callback.
It does not submit a load request, replace save files or construct metadata.
"""
import argparse,ctypes as C,hashlib,json,shutil,struct,sys,time
from ctypes import wintypes as W
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent.parent/'outputs/san14-link'))
from battle_observer import BattleObserver
from startup_identity_reader import capture_startup_context
from run_autonomous_pilot import ProcessAPI,pefile
CHECKPOINT=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
CHECKPOINT_SHA='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
JOURNAL=ROOT/'auto_cache_live_once.json'
REPORT=struct.Struct('<22I7Q')
NAMES=('magic version status error active_callbacks accepted installer_thread executor_thread original_calls parameter_calls scanner_calls intent_created intent_flushed scanner_returned parameter_value cached_slots slot_restored protection_restored exception_code world_unchanged slot34_matched reserved base caller state slot original hook manager').split()
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sample(reader,require_empty=True):
    m=reader.memory;ctx=capture_startup_context(reader);reasons=[]
    def need(ok,message):
        if not ok:reasons.append(message)
    k=m.k;k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)];k.CheckRemoteDebuggerPresent.restype=W.BOOL;debugger=W.BOOL()
    need(k.CheckRemoteDebuggerPresent(m.handle,C.byref(debugger)) and not debugger.value,'debugger_present_or_query_failed')
    need(reader.sha256=='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025','unsupported_game_build')
    s=ctx['snapshot'];need(s['player']['force_id']==12 and s['player']['ruler_id']==666,'not_Zhang_Lu')
    need(s['date']=={'year':203,'month':8,'day':11,'period':'中旬'},'not_checkpoint34_date')
    need(s['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],'not_idle_planning')
    need(ctx['state_sample'] is not None and ctx['state_sample']['phase_raw']==2 and ctx['world_mode']==1,'wrong_phase_or_mode')
    need(sha(CHECKPOINT)==CHECKPOINT_SHA,'checkpoint34_changed')
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    for p in load(ROOT/'auto_cache_profile.json')['ranges']:need(m.read(m.base+p['start'],p['end']-p['start'])==image[p['start']:p['end']],'code_mismatch_'+hex(p['start']))
    q=lambda at:struct.unpack('<Q',m.read(at,8))[0]
    i=lambda at:struct.unpack('<i',m.read(at,4))[0]
    manager=q(m.base+0x2025318);mode=i(manager+8);pending=i(manager+0x3EC);list_count=q(manager+0x18);sentinel=q(manager+0x10)
    cache=list(struct.unpack('<120Q',m.read(manager+0x20,120*8)))
    need(mode==0 and pending==-1,'wrong_manager_mode_or_pending')
    if require_empty:
        need(not any(cache),'cache_not_empty');need(list_count==0 and q(sentinel)==q(sentinel+8)==sentinel,'metadata_list_not_empty')
    state_queue=q(m.base+0x19E7310+0x30);need(state_queue==0,'pending_state_transition')
    need(q(m.base+0x12CC4A8+0x28)==m.base+0x3F9B00,'existing_user_update_hook')
    root=q(m.base+0x1FCA1E0);world=q(root+0x85130);need(q(root)==m.base+0x12AA6B0,'root_type_mismatch')
    need(ctx==capture_startup_context(reader),'context_changed_during_precheck')
    metadata=[]
    for slot,ptr in enumerate(cache):
        if not ptr:continue
        n=q(ptr+0x138);capacity=q(ptr+0x140);text=q(ptr+0x128) if capacity>=16 else ptr+0x128
        value=m.read(text,n+1).rstrip(b'\0').decode('ascii',errors='replace') if n<=512 and n<=capacity<=32768 else None
        metadata.append({'slot':slot,'pointer':hex(ptr),'filename':value})
    return {'result':'PASS' if not reasons else 'BLOCKED_PRECONDITIONS','reasons':reasons,'pid':reader.pid,'base':hex(m.base),'context':ctx,'manager':hex(manager),'mode':mode,'pending':pending,'list_count':list_count,'metadata':metadata,'hint_indices':{'3e8':i(manager+0x3E8),'3f8':i(manager+0x3F8)},'pending_state_commands':state_queue,'world_blob_sha256':hashlib.sha256(m.read(world,0x2200)).hexdigest(),'checkpoint34_sha256':sha(CHECKPOINT),'game_writes':0,'scope':'Targeted preconditions and CWorld[0..2200) hash, not full-world equality.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group();g.add_argument('--precheck',action='store_true');g.add_argument('--dry',action='store_true');g.add_argument('--execute',action='store_true');p.add_argument('--seconds',type=int,default=30);args=p.parse_args();assert 2<=args.seconds<=60
    reader=BattleObserver();api=None;report_address=None;cancel_address=None;run=None
    try:
        before=sample(reader);save(ROOT/'auto_cache_preflight.json',before)
        if not(args.dry or args.execute) or before['result']!='PASS':print(json.dumps(before,ensure_ascii=False,indent=2));return
        binary=ROOT/'auto_cache_pilot.dll';dll_sha=sha(binary);tests=load(ROOT/'auto_cache_test_results.json')
        assert tests['result']=='PASS' and len(tests['cases'])==20 and tests['dll_sha256']==dll_sha,'Run exact-DLL fixture tests first'
        if args.execute:
            assert not JOURNAL.exists(),'An uncertain cache scan has already consumed this pilot attempt; no automatic retry'
            dry=load(ROOT/'auto_cache_dry_result.json');assert dry['result']=='PASS' and dry['dll_sha256']==dll_sha and dry['before']['pid']==before['pid'] and dry['before']['base']==before['base'],'Need exact-DLL dry result for this attachment'
        run=ROOT/'auto_cache_traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
        save(run/'before.json',before);business_before=reader.capture();save(run/'business-before.json',business_before)
        dll=run/f'auto-cache-{run.name}.dll';shutil.copyfile(binary,dll);pe=pefile.PE(str(dll));exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name};pe.close()
        assert all(name in exports for name in ('InstallAutoCache','CancelAutoCache','AutoCacheReport'))
        api=ProcessAPI(reader);api.call_adapter(api.load_library_address(),str(dll).encode('utf-16le')+b'\0\0')
        modules=[base for base,path in api.modules() if str(path).lower()==str(dll).lower()];assert len(modules)==1
        module=modules[0];report_address=module+exports['AutoCacheReport'];cancel_address=module+exports['CancelAutoCache']
        def report():
            value=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))));assert value['magic']==0x1414EC01 and value['version']==1;return value
        intent=str(JOURNAL).encode('utf-16le')+b'\0\0';assert len(intent)<=1024
        config=struct.pack('<QII',0x53414E1443414331,1,int(args.execute))+intent.ljust(1024,b'\0')
        code=api.call_adapter(module+exports['InstallAutoCache'],config)
        deadline=time.monotonic()+args.seconds;value=report()
        while time.monotonic()<deadline and (value['status']<3 or value['active_callbacks']):time.sleep(.05);value=report()
        if value['status']==1:api.call_adapter(cancel_address);value=report()
        completed=not value['active_callbacks'] and value['status'] in (3,4,5,6,7)
        after=sample(reader,require_empty=not args.execute) if completed else None
        business_after=reader.capture() if completed else None
        if after is not None:save(run/'after.json',after);save(run/'business-after.json',business_after)
        expected=4 if args.execute else 3
        passed=code==0 and value['status']==expected and not value['active_callbacks'] and value['slot_restored']==value['protection_restored']==1 and value['parameter_calls']==value['scanner_calls']==int(args.execute) and value['caller']==int(before['base'],0)+0x50B785 and value['installer_thread']!=value['executor_thread'] and after is not None and after['result']=='PASS' and business_before==business_after
        if args.execute:passed=passed and value['scanner_returned']==value['world_unchanged']==value['slot34_matched']==1
        result={'result':'PASS' if passed else 'NOT_COMPLETED_NO_AUTO_RETRY','execute':args.execute,'dll_sha256':dll_sha,'directory':str(run),'before':before,'after':after,'adapter':value,'install_exit':code,'sampled_business_unchanged':business_before==business_after,'once_journal':str(JOURNAL),'full_world_sync_proven':False,'inert_module_remains_until_exit':True}
        save(run/'result.json',result)
        if args.dry and passed:save(ROOT/'auto_cache_dry_result.json',result)
        if args.execute:save(ROOT/'auto_cache_live_result.json',result)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception:
        if api and report_address and cancel_address:
            try:
                value=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
                if value['status']==1:api.call_adapter(cancel_address)
                if run:save(run/'failure-adapter.json',value)
            except Exception:pass
        raise
    finally:
        if api:api.close()
        reader.close()
if __name__=='__main__':main()
