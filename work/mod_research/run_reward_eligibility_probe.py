"""Compare the external reward predicate mirror with the native game predicate.

Only the native eligibility query runs, once per global-list person. No native
reward handler is present in the query adapter. Temporary hook/DLL memory
changes mean this experiment itself is not strictly read-only.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import struct
import time
from run_reward_container_probe import ROOT,REPORT,NAMES,save
from run_autonomous_pilot import ProcessAPI,pefile
from battle_observer import BattleObserver
from reward_eligibility import capture_eligibility
from pilot_evidence import check_checkpoint,check_restored,load_json,require
from prepare_eligibility_fingerprints import RANGES

def main():
    fixtures=load_json(ROOT/'reward-eligibility-fixtures.json')
    require(len(fixtures)==12 and all(r['passed'] for r in fixtures),'Query fixtures incomplete')
    checkpoint=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
    check_checkpoint(checkpoint)
    run=ROOT/'reward-eligibility-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True,exist_ok=False)
    reader=BattleObserver();api=None;report_address=None;cancel_address=None
    try:
        before=reader.capture();check_restored(load_json(ROOT/'before-native-submit.json'),before)
        require(before['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],'Expected plain map')
        eligibility_before=capture_eligibility(reader)
        require(0<eligibility_before['person_count']<=1024,'Person batch exceeds query bound')
        image=(ROOT/'game-runtime-image.bin').read_bytes();base=reader.memory.base
        for a,z in RANGES:
            require(reader.memory.read(base+a,z-a)==image[a:z],f'Predicate dependency mismatch at {a:X}')
        slot=base+0x12CC4A8+0x28
        require(int.from_bytes(reader.memory.read(slot,8),'little')==base+0x3F9B00,'Update slot already changed')
        def pool_totals():
            return {hex(rva):int.from_bytes(reader.memory.read(base+rva,8),'little')
                    for rva in (0x19E1C20,0x19E1C68,0x201D3D0)}
        pools_before=pool_totals()
        dll=run/f'reward-eligibility-{run.name}.dll';shutil.copyfile(ROOT/'reward_eligibility_probe.dll',dll)
        pe=pefile.PE(str(dll));exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name};pe.close()
        require(set(exports)=={'InstallRewardProbe','CancelRewardProbe','RewardProbeReport','RewardEligibilityReport'},'Unexpected exports')
        save(run/'before.json',before);save(run/'eligibility-before.json',eligibility_before)
        save(run/'metadata.json',{'pid':reader.pid,'base':hex(base),'game_sha256':reader.sha256,'dll_path':str(dll),
             'dll_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'mode':'native-eligibility-query-no-order',
             'fixture_tests':12,'native_reward_handler_calls':0,'inert_module_remains_loaded_until_game_exit':True})
        api=ProcessAPI(reader)
        api.call_adapter(api.load_library_address(),str(dll).encode('utf-16le')+b'\0\0')
        modules=[b for b,p in api.modules() if str(p).lower()==str(dll).lower()]
        require(len(modules)==1,'Eligibility DLL not found after load')
        module=modules[0];report_address=module+exports['RewardProbeReport'];cancel_address=module+exports['CancelRewardProbe']
        def read_report():
            r=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
            require(r['magic']==0x1414C001 and r['version']==1,'Report identity mismatch');return r
        code=api.call_adapter(module+exports['InstallRewardProbe'],struct.pack('<QII',0x53414E1452435031,1,0))
        deadline=time.monotonic()+8;report=read_report()
        while time.monotonic()<deadline and (report['status']<3 or report['active_callbacks']):
            time.sleep(.05);report=read_report()
        if report['status']==1:api.call_adapter(cancel_address);report=read_report()
        save(run/'adapter-report.json',report)
        raw=reader.memory.read(module+exports['RewardEligibilityReport'],8208)
        magic,version,count,calls=struct.unpack_from('<4I',raw)
        require(magic==0x1414E001 and version==1 and count<=1024,'Query report identity/count mismatch')
        values=[{'id':i,'eligible':bool(v),'raw':v} for i,v in struct.iter_unpack('<II',raw[16:16+count*8])]
        save(run/'native-query.json',{'count':count,'calls':calls,'rows':values})
        after=reader.capture();eligibility_after=capture_eligibility(reader);pools_after=pool_totals()
        save(run/'after.json',after);save(run/'eligibility-after.json',eligibility_after)
        require(code==0 and report['status']==3,f'Native query rejected/failed: code={code}, report={report}')
        require(report['slot_restored']==1 and report['protection_restored']==1 and report['active_callbacks']==0,
                'Query callback cleanup incomplete')
        require(int.from_bytes(reader.memory.read(slot,8),'little')==base+0x3F9B00,'Actual update slot not restored')
        require(report['caller']==base+0x50B785 and report['executor_thread']!=report['installer_thread'],'Native callback context mismatch')
        require(report['ctor_calls']==report['append_calls']==report['dtor_calls']==0,'Query unexpectedly constructed a command')
        require(calls==count==eligibility_before['person_count'],'Native batch length mismatch')
        require(eligibility_before==eligibility_after and pools_before==pools_after,'Observed state/pool totals changed')
        require(all(v['raw'] in (0,1) for v in values),'Unexpected predicate result')
        expected=[(p['id'],p['predicate_eligible']) for p in eligibility_before['persons']]
        actual=[(p['id'],p['eligible']) for p in values]
        mismatches=[{'expected':a,'actual':b} for a,b in zip(expected,actual) if a!=b]
        save(run/'comparison.json',{'mismatches':mismatches,'compared':count})
        require(not mismatches,f'Native predicate disagreed with external mirror: {mismatches[:10]}')
        comparison=check_restored(before,after);check_checkpoint(checkpoint)
        own_ids=eligibility_after['own_force_predicate_eligible_ids']
        candidates=[p for p in eligibility_after['persons'] if p['id'] in own_ids]
        result={'result':'PASS','stage':'NATIVE_REWARD_PERSON_ELIGIBILITY_CORRELATED','directory':str(run),
                'fixture_tests':12,'adapter':report,'native_predicate_calls':calls,'persons_compared':count,
                'native_accepted':sum(p['eligible'] for p in values),'native_rejected':sum(not p['eligible'] for p in values),
                'mismatches':0,'task_count':eligibility_after['task_count'],
                'own_force_person_count':eligibility_after['own_force_person_count'],
                'own_force_candidates':candidates,'own_force_rejection_counts':eligibility_after['own_force_rejection_counts'],
                'native_predicate_correlated':True,'full_command_legality_verified':False,
                'reward_handler_calls':0,'domestic_network_execution_enabled':False,'two_client_multiplayer':False,
                'person_and_task_records_unchanged':True,'person_records_sha256':eligibility_after['person_records_sha256'],
                'task_fields_sha256':eligibility_after['task_fields_sha256'],
                'pool_totals_before_after':[pools_before,pools_after],'focused_state_comparison':comparison,
                'checkpoint34_unchanged':True,'manual_game_operations_required':False,'post_test_restore':'NOT_NEEDED',
                'temporary_hook_memory_writes':True,'inert_module_remains_loaded_until_game_exit':True,
                'scope':'Person predicate on this snapshot; not proof of complete UI scope, phase, funding or execution legality'}
        save(run/'result.json',result)
        save(ROOT.parents[1]/'outputs'/'san14-link'/'赏赐资格对照验证.json',result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('own_force_candidates','adapter')},ensure_ascii=True,indent=2))
    except Exception as error:
        failure={'result':'FAIL','error':str(error),'automatic_retry_allowed':False}
        if api and report_address and cancel_address:
            try:
                data=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
                if data['status']==1:api.call_adapter(cancel_address)
                failure['adapter']=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
            except Exception as e:failure['cleanup_error']=str(e)
        save(run/'failure.json',failure);raise
    finally:
        if api:api.close()
        reader.close()

if __name__=='__main__':main()
