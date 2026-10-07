"""One version-locked native container rehearsal; never calls the reward handler.

Remote threads only load/install/cancel. Container native functions run once on
the original game update callback. Temporary allocation and a vtable swap are
real memory writes, not a read-only test. No order execution is implemented.
"""
import ctypes as C
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import pefile
from run_autonomous_pilot import ProcessAPI
from battle_observer import BattleObserver
from pilot_evidence import check_checkpoint,check_restored,load_json,require
from prepare_reward_fingerprints import RVAS
from reward_probe_state import capture_reward_state,IDS

REPORT=struct.Struct('<24I9Q')
NAMES=('magic version status error active_callbacks accepted installer_thread executor_thread original_calls '
       'ctor_calls append_calls dtor_calls readback_count slot_id handle_cleared owned_slot_cleared slot_restored '
       'protection_restored exception_code world_guard_unchanged id_0 id_1 id_2 reserved '
       'base caller hook_slot original hook before_nodes after_nodes before_handles after_handles').split()

def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    fixtures=load_json(ROOT/'reward-container-fixtures.json')
    require(len(fixtures)==14 and all(row['passed'] for row in fixtures),'Container fixtures did not all pass')
    check_checkpoint(ROOT.parent/'mod_test'/'replay-checkpoint-34'/'svdexSC34.s14')
    save_path=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
    check_checkpoint(save_path)
    run=ROOT/'reward-container-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True,exist_ok=False)
    reader=BattleObserver();api=None;report_address=None;cancel_address=None
    try:
        before=reader.capture()
        check_restored(load_json(ROOT/'before-native-submit.json'),before)
        require(before['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],
                'Expected plain map with no order dialog')
        reward_before=capture_reward_state(reader)
        require(all(p['basic_checks_passed'] for p in reward_before['candidates']) and
                reward_before['funding_location_matches'] and reward_before['enough_gold_for_batch'] and
                reward_before['enough_actions_for_batch'],'Reward basic preflight failed')
        base=reader.memory.base
        require(int.from_bytes(reader.memory.read(base+0x19E1C30,4),'little')==0x400 and
                int.from_bytes(reader.memory.read(base+0x19E1C70,8),'little')==0x400,
                'Unexpected integer-list pool capacity')
        image=(ROOT/'game-runtime-image.bin').read_bytes()
        for rva in RVAS:
            require(reader.memory.read(base+rva,32)==image[rva:rva+32],f'Runtime prefix mismatch at {rva:X}')
        slot=base+0x12CC4A8+0x28
        require(int.from_bytes(reader.memory.read(slot,8),'little')==base+0x3F9B00,'Update slot already changed')
        # Also compare complete primary function bodies, not just their prefixes.
        for begin,end in ((0x22600,0x22680),(0x83E0,0x8447),(0x171B0,0x172CA),
                          (0x16B90,0x16C45),(0x16D10,0x16E1A)):
            require(reader.memory.read(base+begin,end-begin)==image[begin:end],f'Runtime body mismatch at {begin:X}')
        dll=run/f'reward-container-{run.name}.dll'
        shutil.copyfile(ROOT/'reward_container_probe.dll',dll)
        pe=pefile.PE(str(dll))
        exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        pe.close()
        require(set(exports)=={'InstallRewardProbe','CancelRewardProbe','RewardProbeReport'},'Unexpected DLL exports')
        save(run/'before.json',before);save(run/'reward-before.json',reward_before)
        save(run/'metadata.json',{'pid':reader.pid,'base':hex(base),'game_sha256':reader.sha256,
             'dll_path':str(dll),'dll_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),
             'mode':'native-container-roundtrip-no-order','officer_ids':IDS,'fixture_tests':len(fixtures),
             'temporary_game_memory_writes':True,'native_reward_handler_called':False,
             'inert_module_remains_loaded_until_game_exit':True})
        api=ProcessAPI(reader)
        api.call_adapter(api.load_library_address(),str(dll).encode('utf-16le')+b'\0\0')
        modules=[b for b,p in api.modules() if str(p).lower()==str(dll).lower()]
        require(len(modules)==1,'Container probe module not found after loading')
        module=modules[0];report_address=module+exports['RewardProbeReport'];cancel_address=module+exports['CancelRewardProbe']
        def read_report():
            data=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
            require(data['magic']==0x1414C001 and data['version']==1,'Invalid container probe report')
            return data
        code=api.call_adapter(module+exports['InstallRewardProbe'],struct.pack('<QII',0x53414E1452435031,1,0))
        deadline=time.monotonic()+8
        report=read_report()
        while time.monotonic()<deadline and (report['status']<3 or report['active_callbacks']):
            time.sleep(.05);report=read_report()
        if report['status']==1:
            api.call_adapter(cancel_address);report=read_report()
        save(run/'adapter-report.json',report)
        # Capture effects even for a rejected operation, before asserting success.
        after=reader.capture();reward_after=capture_reward_state(reader)
        save(run/'after.json',after);save(run/'reward-after.json',reward_after)
        require(code==0 and report['status']==3,f'Container rehearsal failed: install={code}, report={report}')
        require(report['slot_restored']==1 and report['protection_restored']==1 and not report['active_callbacks'],
                'Callback cleanup incomplete')
        require(int.from_bytes(reader.memory.read(slot,8),'little')==base+0x3F9B00,'Actual update slot not restored')
        require(report['caller']==base+0x50B785 and report['installer_thread']!=report['executor_thread'],
                'Native update scheduling evidence missing')
        require((report['ctor_calls'],report['append_calls'],report['dtor_calls'])==(1,3,1),'Unexpected native lifecycle counts')
        require(report['readback_count']==3 and [report[f'id_{i}'] for i in range(3)]==IDS,'Readback mismatch')
        require(report['handle_cleared']==1 and report['owned_slot_cleared']==1 and
                report['before_nodes']==report['after_nodes'] and report['before_handles']==report['after_handles'],
                'Pool cleanup mismatch; do not retry automatically')
        require(report['world_guard_unchanged']==1 and reward_before==reward_after,'Reward state changed')
        comparison=check_restored(before,after)
        check_checkpoint(save_path)
        result={'result':'PASS','stage':'NATIVE_REWARD_CONTAINER_ROUNDTRIP_ONLY','directory':str(run),
                'fixture_tests':len(fixtures),'adapter':report,'officer_ids':IDS,
                'reward_handler_calls':0,'full_reward_legality_verified':False,'domestic_network_execution_enabled':False,
                'temporary_memory_writes':True,'two_client_multiplayer':False,
                'reward_state_unchanged':True,'global_person_count':reward_after['global_person_count'],
                'global_person_records_sha256':reward_after['global_person_records_sha256'],
                'gold_before_after':[reward_before['city']['gold'],reward_after['city']['gold']],
                'actions_before_after':[reward_before['district']['action_points'],reward_after['district']['action_points']],
                'loyalty_before_after':[[p['id'],p['loyalty'],q['loyalty']] for p,q in zip(reward_before['candidates'],reward_after['candidates'])],
                'focused_state_comparison':comparison,'checkpoint34_unchanged':True,
                'manual_game_operations_required':False,'post_test_restore':'NOT_NEEDED',
                'scope':reward_after['scope'],'pool_free_list_order_may_change':True,
                'inert_module_remains_loaded_until_game_exit':True}
        save(run/'result.json',result)
        save(ROOT.parents[1]/'outputs'/'san14-link'/'赏赐名单容器验证.json',result)
        print(json.dumps(result,ensure_ascii=True,indent=2))
    except Exception as error:
        failure={'result':'FAIL','error':str(error),'automatic_retry_allowed':False}
        if api and report_address and cancel_address:
            try:
                data=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
                if data['status']==1:api.call_adapter(cancel_address)
                failure['adapter']=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
            except Exception as cleanup_error:failure['cleanup_error']=str(cleanup_error)
        save(run/'failure.json',failure)
        raise
    finally:
        if api:api.close()
        reader.close()

if __name__=='__main__':main()
