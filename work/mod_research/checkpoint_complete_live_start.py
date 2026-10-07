"""One fixed native CC03 load: default read-only preflight; --execute never retries.

The full owner is retained after any possible request. No post-CAS detach,
thread termination, save/advance command, or multiplayer-ready assertion.
"""
import argparse,ctypes as C
from datetime import datetime
import hashlib,json,os,secrets,shutil,struct,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
from checkpoint_live_prefetch_start import invoke,RemoteCallError
from checkpoint_complete_live_capture import (planning_bindings,storage_bindings,known_snapshot,
    GAME_SHA,SOURCE,SOURCE_SHA,TARGET,TARGET_SHA,TARGET_SIZE,require)
from checkpoint_push_start import file_sample,process_birth
APPROVED_DLL='984e3fbf763557d70f6bdaecd1823acc2a6e46795a285162a36cdadd2c2c0c9c'
APPROVED_HANDOFF='06e3ca650080027743ff9cf7f6dd9a20d583b9229d951a8f0a464cb707010314'
APPROVED_CONTRACT='14579f196fb927e7e055735eeafccb4b11cd4e8688bb7105b1055fc29da67d5a'
APPROVED_ACCEPTANCE='42bfdbd4b8516c9591493880e2f7c5c27db58e340c2df98c7311631f80de2453'
CLAIM=P/'checkpoint_complete_live_once.json'
ARCHIVE=P/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
EXPORTS=('DescribeCheckpointCompleteLiveOwner','InstallCheckpointCompleteLiveOwner',
    'GetCheckpointCompleteLiveOwnerReport','StopCheckpointCompleteLiveOwner',
    'RestoreCheckpointCompleteLiveOwnerBeforeCommit')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf8',newline='\n')as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

def target_files():
    found={str(path):file_sample(path) for path in (SOURCE,TARGET,ARCHIVE)}
    require(found[str(SOURCE)]['sha256']==SOURCE_SHA,'Source slot34 changed')
    for path in (TARGET,ARCHIVE):
        require(found[str(path)]['sha256']==TARGET_SHA and found[str(path)]['size']==TARGET_SIZE,
            'Fixed target checkpoint differs')
    return found

def preflight(reader,api):
    from checkpoint_manual_reload_observe_start import precheck
    base=precheck();require(base['result']=='PASS','Initial idle planning checks failed')
    require(reader.pid==base['pid'] and process_birth(reader)==base['process_birth'],
        'Game attachment changed')
    planning=planning_bindings(reader);storage=storage_bindings(reader,api.modules())
    return dict(result='PASS_READ_ONLY_PREFLIGHT',planning=planning,storage=storage,
        files=target_files(),game_writes=0,native_calls=0,authorize_install=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    from battle_observer import BattleObserver
    from run_autonomous_pilot import ProcessAPI
    reader=BattleObserver();api=None
    try:
        api=ProcessAPI(reader)
        before=preflight(reader,api)
        if not args.execute:
            folder=P/'checkpoint_complete_live_preflights';folder.mkdir(exist_ok=True)
            path=folder/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json');save(path,before)
            print(json.dumps(dict(result=before['result'],path=str(path),pid=reader.pid,
                date=before['planning']['context']['snapshot']['date'],load_requested=False)))
            return
        execute(reader,api,before)
    finally:
        if api:api.close()
        reader.close()

def execute(reader,api,before):
    from checkpoint_complete_live_owner_contract import Config,Report,Description,decode_report,decode_description
    from checkpoint_complete_live_acceptance import validate_report
    from checkpoint_complete_live_capture import readable
    from run_autonomous_pilot import pefile
    require(not CLAIM.exists(),'Complete load already claimed; inspect the existing attempt, never retry automatically')
    dll=P/'checkpoint_complete_live_owner.dll'
    handoff=P/'checkpoint_complete_live_owner_handoff.json'
    for path,expected in ((dll,APPROVED_DLL),(handoff,APPROVED_HANDOFF),
            (P/'checkpoint_complete_live_owner_contract.py',APPROVED_CONTRACT),
            (P/'checkpoint_complete_live_acceptance.py',APPROVED_ACCEPTANCE)):
        require(expected!='UNREVIEWED' and sha(path)==expected,'Unreviewed owner artifact: '+path.name)
    folder=P/'checkpoint_complete_live_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    result=dict(schema='san14.complete-live-load.v1',result='INCOMPLETE',
        full_world_verified=False,ready_authorized=False,map_cover_tested=False,
        module_retained=True,install_completed=False,post_cas_detach_allowed=False,
        automatic_retry_allowed=False,dll_sha256=APPROVED_DLL)
    trace=[];install_completed=False;control_uncertain=False;stop_address=None
    base=reader.memory.base;attempt=secrets.randbits(64) or 1;epoch=secrets.randbits(64) or 1
    attachment=secrets.token_hex(32);owner_binding=secrets.token_hex(32)
    try:
        known_before=known_snapshot(reader,expected_user_hook=base+0x3f9b00)
        save(folder/'known-before.json',known_before)
        target=folder/TARGET.name;shutil.copyfile(ARCHIVE,target)
        require(sha(target)==TARGET_SHA,'Private target copy changed')
        copied=folder/dll.name;shutil.copyfile(dll,copied)
        require(sha(copied)==APPROVED_DLL,'Private DLL copy changed')
        pe=pefile.PE(str(copied))
        try:
            exports={s.name.decode('ascii'):s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
            image_size=pe.OPTIONAL_HEADER.SizeOfImage
            require(all(name in exports and 0<exports[name]<image_size for name in EXPORTS),'Missing/outside owner export')
        finally:pe.close()
        claim=dict(run=str(folder),pid=reader.pid,birth=before['planning']['birth'],base=base,
            attempt=attempt,epoch=epoch,generation=attempt,attachment=attachment,owner_binding=owner_binding,
            dll_sha256=APPROVED_DLL,target_sha256=TARGET_SHA,target=str(target),
            description_is_authorization=False,automatic_retry_allowed=False)
        save(CLAIM,claim);result.update(claim)
        # Persist the attempt before the first remote call, including uncertain LoadLibrary outcomes.
        invoke(api,api.load_library_address(),str(copied).encode('utf-16le')+b'\0\0')
        modules=[a for a,p in api.modules() if str(p).casefold()==str(copied).casefold()]
        require(len(modules)==1,'Loaded owner module identity differs');module=modules[0]
        addresses={name:module+exports[name] for name in EXPORTS}
        stop_address=addresses[EXPORTS[3]]
        code,raw=invoke(api,addresses[EXPORTS[0]],output_size=C.sizeof(Description))
        require(code==0,'Owner description rejected');description=decode_description(raw)
        require(description['module']==module,'Described owner module differs')
        bridges=description['dispatchBridge']+[description['workerBridge'],description['readBridge'],description['authorizedForward']]
        require(len(set(bridges))==7,'Duplicate owner bridge address')
        pe=pefile.PE(str(copied),fast_load=True)
        try:
            for address in bridges+list(addresses.values()):
                require(module<=address and address+32<=module+image_size,'Owner code outside approved module')
                readable(reader,address,32,allocation=module,execute=True)
                require(reader.memory.read(address,32)==pe.get_data(address-module,32),'Owner code differs from approved disk image')
        finally:pe.close()
        save(folder/'description.json',description)
        storage=storage_bindings(reader,api.modules(),owner_module=module,owner_path=copied,
            owner_sha=APPROVED_DLL,read_bridge=description['readBridge'])
        target_files()
        planning=planning_bindings(reader)
        require(planning['pid']==claim['pid'] and planning['birth']==claim['birth'] and planning['base']==base,
            'Game attachment changed before installation')
        hook_before=live_hook_evidence(reader,planning,storage)
        save(folder/'hook-before.json',hook_before)
        config=build_config(planning,storage,folder=folder,target=target,attempt=attempt,epoch=epoch,
            attachment_hex=attachment,owner_binding_hex=owner_binding)
        config_raw=bytes(config)
        save(folder/'bindings.json',dict(planning=planning,storage=storage,config_sha256=hashlib.sha256(config_raw).hexdigest()))
        (folder/'config.bin').write_bytes(config_raw)
        try:
            code,_=invoke(api,addresses[EXPORTS[1]],config_raw)
        except RemoteCallError as exc:
            install_completed=exc.completed;control_uncertain=not exc.completed and exc.may_have_started
            result.update(install_completed=install_completed,install_may_have_started=exc.may_have_started,
                control_cleanup_errors=exc.cleanup_errors)
            raise
        install_completed=True;result.update(install_completed=True,install_exit=code)
        require(code==0,'Owner rejected installation; no second attempt')
        deadline=time.monotonic()+90;previous=None;accepted=None;last_rejection=None
        while time.monotonic()<deadline:
            try:code,raw=invoke(api,addresses[EXPORTS[2]],output_size=C.sizeof(Report))
            except RemoteCallError as exc:
                control_uncertain=not exc.completed and exc.may_have_started
                raise
            require(code==0,'Owner report rejected')
            row=decode_report(raw);trace.append(row)
            require((row['attempt'],row['epoch'])==(attempt,epoch),'Owner report attempt differs')
            (folder/'latest-report.bin').write_bytes(raw)
            try:
                critical=validate_report(row,base=base,attempt=attempt,epoch=epoch,generation=attempt,
                    attachment_hex=attachment,description=description,planning=planning,storage=storage)
            except (ValueError,RuntimeError,AssertionError) as exc:
                last_rejection=str(exc);previous=None
                if any(row[key] for key in ('OwnerError','SessionError','ControllerError','QueueError',
                        'BytesError','LifecycleError','IdentityError','PlanningError','HardwareError','StorageError','GuardError')):
                    break
            else:
                if previous==critical:accepted=row;break
                previous=critical
            time.sleep(.15)
        result['last_validation_rejection']=last_rejection
        require(accepted is not None,'Native completion proof incomplete: '+str(last_rejection))
        # These are two quiescent samples, not a global scheduler fence.
        result.update(two_consistent_receipt_samples=True,scheduler_fence_proven=False,report=accepted)
        known_after=known_snapshot(reader,expected_user_hook=description['dispatchBridge'][0])
        save(folder/'known-after.json',known_after)
        require(known_before['save_files']==known_after['save_files'],'Existing save files changed')
        snapshot=known_after['context']['snapshot']
        require(snapshot['date']==planning['context']['snapshot']['date'] and
            snapshot['player']['force_id']==2 and snapshot['player']['ruler_id']==952,
            'Fresh planning date/player differs from the required B view')
        require(process_birth(reader)==claim['birth'],'Game attachment changed after completion')
        target_files()
        owned=description['dispatchBridge']+[description['workerBridge'],description['readBridge']]
        hook_after=live_hook_evidence(reader,planning,storage,expected=owned,baseline=hook_before)
        save(folder/'hook-after.json',hook_after)
        code,_=invoke(api,stop_address);require(code==0,'Could not close further admission')
        result.update(stop_completed=True,stop_exit=code)
        stopped_report=None;stop_deadline=time.monotonic()+2
        while time.monotonic()<stop_deadline:
            code,raw=invoke(api,addresses[EXPORTS[2]],output_size=C.sizeof(Report))
            require(code==0,'Post-stop report rejected');row=decode_report(raw);trace.append(row)
            check_stopped_health(row,accepted)
            if all(row[k]==0 for k in ('ActiveDispatch','ActiveWorker','ActiveRead','ControllerActive',
                    'BytesActiveWorker','BytesActiveRead','LifecycleInFlight','IdentityActive','PlanningInFlight')) and all(
                    bridge['started']==bridge['returned'] for bridge in row['bridges']):
                stopped_report=row;break
            time.sleep(.1)
        require(stopped_report is not None,'Retained observers did not settle after closing admission')
        result['post_stop_report']=stopped_report
        hook_stopped=live_hook_evidence(reader,planning,storage,expected=owned,baseline=hook_before)
        save(folder/'hook-stopped.json',hook_stopped)
        result.update(stop_completed=True,stop_exit=code,existing_save_files_unchanged=True,
            result='PASS_NATIVE_LOAD_IDENTITY_PLANNING')
    except BaseException as exc:
        result['error']=repr(exc)
        if isinstance(exc,RemoteCallError) and not exc.completed and exc.may_have_started:
            control_uncertain=True
        # No restore/detach: even a partial report may miss a request already published.
        if install_completed and stop_address and not control_uncertain and not result.get('stop_completed'):
            try:
                code,_=invoke(api,stop_address);result.update(cleanup_stop_exit=code,stop_completed=code==0)
            except BaseException as cleanup:
                result['cleanup_error']=repr(cleanup)
                if isinstance(cleanup,RemoteCallError):
                    result['cleanup_control_completed']=cleanup.completed
                    result['cleanup_control_may_have_started']=cleanup.may_have_started
                    if not cleanup.completed and cleanup.may_have_started:control_uncertain=True
        result['control_lifetime_uncertain']=control_uncertain
    finally:
        result['control_lifetime_uncertain']=control_uncertain
        save(folder/'trace.json',trace);save(folder/'result.json',result)
    print(json.dumps(dict(result=result['result'],path=str(folder/'result.json'),error=result.get('error')),
        ensure_ascii=False))
    if result['result']!='PASS_NATIVE_LOAD_IDENTITY_PLANNING':raise SystemExit(1)


def check_stopped_health(row,accepted):
    require((row['attempt'],row['epoch'])==(accepted['attempt'],accepted['epoch']),'Post-stop attempt differs')
    require(row['StopRequested']==1,'Further admission remains open')
    zero=('OwnerError SessionError SessionException OwnerException OsError DispatchUnpaired QueueError '
        'ControllerError ControllerAbnormal RequestOsError RequestException BytesError BytesWorkerAbnormal '
        'BytesReadAbnormal LifecycleError IdentityError IdentityAbnormal PlanningError PlanningException '
        'PlanningSessionError HardwareError HardwareRestoreUncertain StorageError StorageInvalidated '
        'GuardError GuardException InputExclusionProven FullWorldVerified PixelPresentationProven ReadyAuthorized').split()
    require(all(row[k]==0 for k in zero),'Late error or unsupported readiness claim after admission closed')
    require(all(all(b[k]==0 for k in ('abnormal','beforeFaults','afterFaults','cleanupFaults'))
        for b in row['bridges']),'Late bridge fault after admission closed')
    for key in ('CasPublished','LifecycleReady','IdentityReady','PlanningObserved','planningAttempt','planningEpoch',
            'planningIdentityCall','planningCompletedCall','planningUser','requestReadSha'):
        require(row[key]==accepted[key],'Completed receipt changed after admission closed: '+key)
    for family,keys in (
            ('bytes','token load title workerCall readCall requested returned sha256'),
            ('lifecycle','token load title completedCall'),
            ('identity','token historicalLoad title completionCall workerCall root world target')):
        require(all(row[family][key]==accepted[family][key] for key in keys.split()),
            'Nested completion proof changed after admission closed: '+family)


def live_hook_evidence(reader,planning,storage,*,expected=None,baseline=None):
    """Fresh slot/page observations; HookSet's publication cache is insufficient."""
    from ctypes import wintypes as W
    from checkpoint_push_start import MemoryPage
    from checkpoint_complete_live_capture import readable
    rows=list(planning['nativeSlots'])+[(storage['storageVtable']+8,storage['read']['address'])]
    values=expected if expected is not None else [original for _,original in rows]
    require(len(values)==len(rows)==6,'Wrong hook set size')
    result=[];k=reader.memory.k
    k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(MemoryPage),C.c_size_t]
    k.VirtualQueryEx.restype=C.c_size_t
    for i,((slot,original),wanted) in enumerate(zip(rows,values)):
        allocation=planning['base'] if i<5 else storage['storageModules'][storage['vtableModuleIndex']]['base']
        readable(reader,slot,8,allocation=allocation)
        page=MemoryPage()
        require(k.VirtualQueryEx(reader.memory.handle,slot,C.byref(page),C.sizeof(page))==C.sizeof(page),'Cannot inspect hook page')
        actual=struct.unpack('<Q',reader.memory.read(slot,8))[0]
        require(actual==wanted,'Actual hook slot differs at index '+str(i))
        row=dict(slot=slot,original=original,observed=actual,protection=page.Protect,allocation=page.AllocationBase)
        if baseline is not None:
            require(all(row[key]==baseline[i][key] for key in ('slot','original','protection','allocation')),
                'Actual hook page binding/protection changed at index '+str(i))
        result.append(row)
    return result


def build_config(planning,storage,*,folder,target,attempt,epoch,attachment_hex,owner_binding_hex):
    """Data-only construction; native guards remain the installation authority."""
    from checkpoint_complete_live_owner_contract import Config
    cfg=Config()
    for name in ('pid','birth','base','root','world','cache','keyboard','toolbar','panel','stack',
            'stackCapacity','queue','queueCapacity','rng','expectedMode'):
        setattr(cfg,name,planning[name])
    require(cfg.expectedMode==0 and cfg.queue==cfg.queueCapacity==0,'Only exact observed empty queue/mode0 supported')
    cfg.states[:]=planning['states'];cfg.attempt=attempt;cfg.epoch=epoch;cfg.generation=attempt
    for name,value in (('attachment',attachment_hex),('ownerBinding',owner_binding_hex),
            ('nonce',secrets.token_hex(32)),('gameSha256',GAME_SHA)):
        raw=bytes.fromhex(value);require(len(raw)==32,'Token/digest size differs');getattr(cfg,name)[:]=raw
    for name,path in (('localPath',target),('installIntent',folder/'install.intent'),
            ('requestIntent',folder/'request.intent'),('identityIntent',folder/'identity.intent')):
        path=Path(path).resolve();require(len(str(path))<512 and path.is_absolute(),'Owner path too long/nonabsolute')
        if name!='localPath':require(not path.exists(),'Intent path already exists')
        setattr(cfg,name,str(path))
    require(Path(cfg.localPath).name=='svdexccSC03.s14','Wrong target leaf')
    require(storage['storageModuleCount']==3 and len(storage['storageModules'])==3,'Need exact three approved modules')
    for i,row in enumerate(storage['storageModules']):
        dst=cfg.storageModules[i]
        for name,value in row.items():
            if name in ('fileSha256','headerSha256'):getattr(dst,name)[:]=bytes.fromhex(value)
            else:setattr(dst,name,value)
    for name in ('storageModuleCount','vtableModuleIndex','counterModuleIndex','storage','storageVtable','storageCounter','cachedGeneration'):
        setattr(cfg,name,storage[name])
    for name in ('contextInit','exists','fileSize','read','ownedReadBridge'):
        src=storage[name];dst=getattr(cfg,name);dst.address=src['address'];dst.moduleIndex=src['moduleIndex']
        dst.first32[:]=bytes.fromhex(src['first32'])
    cfg.contextCode[:]=bytes.fromhex(storage['contextCode'])
    return cfg

if __name__=='__main__':main()
