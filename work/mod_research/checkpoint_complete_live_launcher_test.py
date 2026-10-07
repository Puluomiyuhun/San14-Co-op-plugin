"""Launcher lifetime/claim failures in an isolated Python process; no game access."""
import copy,ctypes as C,hashlib,json,sys,tempfile,types
from contextlib import ExitStack,redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import checkpoint_complete_live_start as app
import checkpoint_complete_live_owner_contract as contract

P=Path(__file__).resolve().parent
seed=json.loads((P/'checkpoint_complete_live_preflights/20261007-151255-462729.json').read_text('utf8'))

def bindings():
    before=copy.deepcopy(seed);s=before['storage']
    s['storageModules'].append(dict(s['storageModules'][0],base=0x70000000,path=str(P/'fixture.dll')))
    s['storageModuleCount']=3;s['ownedReadBridge']=dict(address=0x70004000,moduleIndex=2,first32='00'*32)
    return before

def case(mode):
    with tempfile.TemporaryDirectory(prefix='san14-launcher-test-') as temp:
        folder=Path(temp);b=bindings();planning=b['planning'];base=planning['base'];module=0x70000000
        dll=folder/'checkpoint_complete_live_owner.dll';dll.write_bytes(b'fixture-only')
        handoff=folder/'checkpoint_complete_live_owner_handoff.json';handoff.write_text('{}')
        abi=folder/'checkpoint_complete_live_owner_contract.py';abi.write_text('fixture-only')
        acceptance=folder/'checkpoint_complete_live_acceptance.py';acceptance.write_text('fixture-only')
        archive=folder/'archive.s14';archive.write_bytes(b'target')
        names=app.EXPORTS;offsets=dict(zip(names,range(0x1000,0x6000,0x1000)))
        desc=dict(module=module,dispatchBridge=[module+0x10000+i*0x100 for i in range(4)],
            workerBridge=module+0x11000,readBridge=module+0x12000,authorizedForward=module+0x13000)
        class PE:
            def __init__(self,*args,**kwargs):
                self.DIRECTORY_ENTRY_EXPORT=types.SimpleNamespace(symbols=[types.SimpleNamespace(name=n.encode(),address=o) for n,o in offsets.items()])
                self.OPTIONAL_HEADER=types.SimpleNamespace(SizeOfImage=0x20000)
            def get_data(self,rva,size):return bytes(size)
            def close(self):pass
        reader=types.SimpleNamespace(pid=planning['pid'],memory=types.SimpleNamespace(base=base,read=lambda a,n:bytes(n)))
        class Api:
            def load_library_address(self):return 0x12345
            def modules(self):return [(module,next((folder/'checkpoint_complete_live_runs').glob('*/checkpoint_complete_live_owner.dll')))]
        calls=[];sample_calls=[]
        def snapshot(*args,**kwargs):
            sample_calls.append(kwargs)
            context=copy.deepcopy(planning['context'])
            if len(sample_calls)>1:context['snapshot']['player'].update(force_id=2 if mode!='wrong_final_player' else 12,ruler_id=952)
            return dict(context=context,save_files={'unchanged':'hash'})
        def invoke(api,address,data=None,output_size=0):
            calls.append(address)
            if address==0x12345:return 0,None
            if address==module+offsets[names[0]]:return 0,bytes(C.sizeof(contract.Description))
            if address==module+offsets[names[1]]:
                if mode in ('install_unknown','install_completed_error'):
                    raise app.RemoteCallError('fixture timeout',completed=mode=='install_completed_error',
                        may_have_started=True,thread_id=7,cleanup_errors=[])
                return (9 if mode in ('install_rejected','cleanup_unknown') else 0),None
            if address==module+offsets[names[2]]:
                if mode=='report_unknown':raise app.RemoteCallError('fixture timeout',completed=False,may_have_started=True,thread_id=8,cleanup_errors=[])
                return 0,bytes(C.sizeof(contract.Report))
            if address==module+offsets[names[3]]:
                if mode=='cleanup_unknown':raise app.RemoteCallError('fixture cleanup timeout',completed=False,may_have_started=True,thread_id=9,cleanup_errors=[])
                return 0,None
            raise AssertionError('Unexpected native operation')
        def report(raw):
            claim=json.loads((folder/'once.json').read_text())
            return dict(attempt=claim['attempt'],epoch=claim['epoch'],bridges=[],**{k:int(k=='OwnerError' and mode=='report_rejected')
                for k in ('OwnerError','SessionError','ControllerError','QueueError','BytesError','LifecycleError',
                    'IdentityError','PlanningError','HardwareError','StorageError','GuardError',
                    'ActiveDispatch','ActiveWorker','ActiveRead','ControllerActive','BytesActiveWorker',
                    'BytesActiveRead','LifecycleInFlight','IdentityActive','PlanningInFlight')})
        def accept(row,**kwargs):
            if mode=='report_rejected':raise ValueError('fixture incomplete proof')
            return {'frozen_key':'fixture_only'}
        fake_acceptance=types.SimpleNamespace(validate_report=accept)
        if mode=='existing_claim':(folder/'once.json').write_text('{}')
        with ExitStack() as stack:
            for name,value in dict(P=folder,CLAIM=folder/'once.json',ARCHIVE=archive,
                    APPROVED_DLL=app.sha(dll),APPROVED_HANDOFF=app.sha(handoff),APPROVED_CONTRACT=app.sha(abi),
                    APPROVED_ACCEPTANCE=app.sha(acceptance),
                    TARGET_SHA=app.sha(archive),known_snapshot=snapshot,storage_bindings=lambda *a,**k:b['storage'],
                    planning_bindings=lambda *a:planning,target_files=lambda:{},invoke=invoke,
                    live_hook_evidence=lambda *a,**k:[],
                    check_stopped_health=lambda *a:None,
                    process_birth=lambda r:planning['birth']).items():stack.enter_context(patch.object(app,name,value))
            stack.enter_context(patch.dict(sys.modules,{'checkpoint_complete_live_acceptance':fake_acceptance}))
            stack.enter_context(patch('run_autonomous_pilot.pefile.PE',PE))
            stack.enter_context(patch('checkpoint_complete_live_capture.readable',lambda *a,**k:None))
            stack.enter_context(patch.object(contract,'decode_description',lambda raw:desc))
            stack.enter_context(patch.object(contract,'decode_report',report))
            with redirect_stdout(StringIO()):
                try:app.execute(reader,Api(),b)
                except (SystemExit,RuntimeError):pass
        reports=list((folder/'checkpoint_complete_live_runs').glob('*/result.json')) if (folder/'checkpoint_complete_live_runs').exists() else []
        result=json.loads(reports[0].read_text()) if reports else None
        stop=module+offsets[names[3]];install=module+offsets[names[1]]
        assert calls.count(install)<=1 and module+offsets[names[4]] not in calls
        if mode=='existing_claim':assert not calls and not reports
        elif mode in ('install_unknown','report_unknown'):
            assert stop not in calls and result['control_lifetime_uncertain'] and result['result']=='INCOMPLETE'
        elif mode=='cleanup_unknown':
            assert calls.count(stop)==1 and result['control_lifetime_uncertain'] and not result['cleanup_control_completed']
        elif mode in ('install_completed_error','install_rejected','report_rejected','wrong_final_player'):
            assert calls.count(stop)==1 and result['result']=='INCOMPLETE'
        else:assert result['result']=='PASS_NATIVE_LOAD_IDENTITY_PLANNING' and calls.count(stop)==1
        assert (folder/'once.json').exists()
        return dict(case=mode,passed=True,remote_calls_simulated=len(calls),game_access=False)

def main():
    results=[case(m) for m in ('existing_claim','install_unknown','install_completed_error','install_rejected',
        'report_unknown','report_rejected','wrong_final_player','completed_model','cleanup_unknown')]
    with tempfile.TemporaryDirectory(prefix='san14-config-test-')as temp:
        b=bindings();kwargs=dict(folder=Path(temp),target=Path(temp)/'svdexccSC03.s14',attempt=19,epoch=29,
            attachment_hex='11'*32,owner_binding_hex='22'*32)
        cfg=app.build_config(b['planning'],b['storage'],**kwargs)
        assert cfg.generation==19 and cfg.epoch==29 and list(cfg.states)==b['planning']['states']
        assert cfg.storageModules[2].base==b['storage']['storageModules'][2]['base']
        assert cfg.read.address==b['storage']['read']['address'] and bytes(cfg.contextCode).hex()==b['storage']['contextCode']
        assert cfg.gameSha256[:]==list(bytes.fromhex(app.GAME_SHA))
        for name,value in (('expectedMode',1),('queue',123),('queueCapacity',64)):
            bad=copy.deepcopy(b['planning']);bad[name]=value
            try:app.build_config(bad,b['storage'],**kwargs)
            except RuntimeError:pass
            else:raise AssertionError('Unsupported config accepted: '+name)
        results.append(dict(case='config_roundtrip_and_unsupported_modes',passed=True))
    health=dict.fromkeys(contract.VALUE_NAMES,0)
    health.update(attempt=1,epoch=2,StopRequested=1,planningAttempt=1,planningEpoch=2,
        planningIdentityCall=3,planningCompletedCall=4,planningUser=5,requestReadSha='11'*32,
        bridges=[dict(started=1,returned=1,abnormal=0,beforeFaults=0,afterFaults=0,cleanupFaults=0)])
    for family,keys in (('bytes','token load title workerCall readCall requested returned sha256'),
            ('lifecycle','token load title completedCall'),('identity','token historicalLoad title completionCall workerCall root world target')):
        health[family]=dict.fromkeys(keys.split(),1)
    accepted=copy.deepcopy(health);app.check_stopped_health(health,accepted)
    for key in ('GuardError','IdentityError','ReadyAuthorized','planningIdentityCall'):
        bad=copy.deepcopy(health);bad[key]+=1
        try:app.check_stopped_health(bad,accepted)
        except RuntimeError:pass
        else:raise AssertionError('Late fault/receipt drift accepted: '+key)
    results.append(dict(case='post_stop_late_fault_and_receipt_drift',passed=True))
    out=P/'checkpoint_complete_live_launcher_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    evidence=dict(result='PASS',scope='Python launcher mocked controls and data-only config; no production load evidence',
        cases=results,source_sha256=hashlib.sha256((P/'checkpoint_complete_live_start.py').read_bytes()).hexdigest())
    (out/'result.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
    print(json.dumps(dict(result='PASS',cases=len(results),path=str(out/'result.json'))))

if __name__=='__main__':main()
