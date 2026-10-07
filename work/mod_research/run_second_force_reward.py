"""Development-only fixed second-faction reward pilot; the local player stays Zhang Lu. Dry by default; --execute mutates once.

The persistent execution journal deliberately prevents automatic retries, even
after an uncertain result. Recovery uses the game's load34 UI, never raw writes.
"""
import argparse
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
from authority_reward import capture_context,make_command,validate_reward,PLANNING_STACK
from reward_eligibility import capture_eligibility
from pilot_evidence import check_checkpoint,check_restored,load_json,require
from prepare_eligibility_fingerprints import RANGES as QUERY_RANGES
from prepare_execution_fingerprints import RANGES
from test_second_force_reward_fixture import CASES

CHECKPOINT=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
EX_NAMES=('magic version execute predicate_calls submit_calls submit_returned submit_result postconditions '
          'loyalty_before_0 loyalty_before_1 loyalty_before_2 loyalty_after_0 loyalty_after_1 loyalty_after_2 '
          'gold_before gold_after actions_before actions_after').split()
IDS=(101,264,411)

def capture(reader):
    focused=reader.capture();eligibility=capture_eligibility(reader)
    memory=reader.memory;root=reader.pointer(memory.base+0x1FCA1E0)
    records={}
    groups=(('person',0x148,[p['id'] for p in eligibility['persons']],0x188),
            ('city',0xDAA8,range(52),0xC0),('district',0xDE40,range(52),0x18),
            ('force',0xDCA0,range(52),0x30),('army',0x7DF60,[a['id'] for a in focused['all_active_units']],0x1F0))
    for name,table,ids,length in groups:
        for identity in ids:
            address=reader.pointer(root+table+identity*8)
            records[f'{name}:{identity}']=memory.read(address+0x10,length).hex()
    pools={hex(rva):int.from_bytes(memory.read(memory.base+rva,8),'little') for rva in (0x19E1C20,0x19E1C68,0x201D3D0)}
    require(focused==reader.capture() and eligibility==capture_eligibility(reader),'Game changed during capture')
    return {'focused':focused,'eligibility':eligibility,'records':records,'pools':pools,
            'global_rng':int.from_bytes(memory.read(memory.base+0x18EB8B0,4),'little'),
            'world_rng_fields_hex':memory.read(reader.pointer(root+0x85130)+0x450,16).hex(),
            'record_scope':'571 valid persons +10..198, 52 cities +10..D0, 52 districts +10..28, 52 forces +10..40, active armies +10..200; sampled task fields. No full world/RNG/UI proof.'}

def diff_records(before,after):
    require(before['records'].keys()==after['records'].keys(),'Observed object membership changed')
    result=[]
    for key,hex_before in before['records'].items():
        b=bytes.fromhex(hex_before);a=bytes.fromhex(after['records'][key])
        require(len(a)==len(b),'Record length changed')
        changes=[{'offset':i+0x10,'before':x,'after':y} for i,(x,y) in enumerate(zip(b,a)) if x!=y]
        if changes:result.append({'object':key,'changes':changes})
    return result

def effects(before,after,execute):
    diff=diff_records(before,after)
    require(before['focused']['state_stack']==after['focused']['state_stack']==PLANNING_STACK,'Planning stack changed')
    require(before['eligibility']['date']==after['eligibility']['date'] and before['eligibility']['player']==after['eligibility']['player'],'Date/player changed')
    require(before['eligibility']['task_fields_sha256']==after['eligibility']['task_fields_sha256'],'Task fields changed')
    require(before['focused']['all_active_units']==after['focused']['all_active_units'],'Army semantic state changed')
    require(before['pools']==after['pools'],'Container pool totals changed')
    if not execute:
        require(before==after,'Dry run changed observed state')
        return {'result':'PASS','changes':[]}
    allowed={'city:13':set(range(0x34,0x38)),'district:2':{0x14},**{f'person:{i}':{0x120,0x196} for i in IDS}}
    require({r['object'] for r in diff}==set(allowed),'Unexpected changed object set')
    for row in diff:
        require(all(c['offset'] in allowed[row['object']] for c in row['changes']),f'Unexpected field change: {row}')
    b={p['id']:p for p in before['eligibility']['persons']};a={p['id']:p for p in after['eligibility']['persons']}
    people=[]
    for identity in IDS:
        require(b[identity]['loyalty']<a[identity]['loyalty']<=min(100,b[identity]['loyalty']+9),'Unexpected loyalty result')
        require(a[identity]['flags']==130 and b[identity]['flags']==128,'Unexpected reward flags')
        people.append({'id':identity,'name':a[identity]['name'],'loyalty_before':b[identity]['loyalty'],'loyalty_after':a[identity]['loyalty']})
    city=bytes.fromhex(after['records']['city:13']);district=bytes.fromhex(after['records']['district:2'])
    require(int.from_bytes(city[0x24:0x28],'little')==20504 and district[4]==9,'Wrong resource result')
    return {'result':'PASS','changes':diff,'persons':people,'gold_before':20804,'gold_after':20504,'actions_before':10,'actions_after':9}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');parser.add_argument('--command-file',type=Path);args=parser.parse_args()
    fixtures=load_json(ROOT/'second-force-reward-fixtures.json')
    require([r['case'] for r in fixtures]==list(CASES) and all(r['passed'] for r in fixtures),'Execution fixtures incomplete')
    check_checkpoint(CHECKPOINT);check_checkpoint(ROOT.parent/'mod_test'/'replay-checkpoint-34'/'svdexSC34.s14')
    binary=ROOT/'second_force_reward_pilot.dll';binary_sha=hashlib.sha256(binary.read_bytes()).hexdigest()
    if args.execute:
        dry=load_json(ROOT/'second-force-reward-dry-latest.json')
        require(dry['result']=='PASS' and dry['dll_sha256']==binary_sha and not dry['executed'],'Need dry pass with the same binary')
    run=ROOT/'second-force-reward-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    reader=BattleObserver();api=None;report_address=cancel_address=None
    try:
        before=capture(reader);require(before==capture(reader),'Baseline is not stable')
        check_restored(load_json(ROOT/'before-native-submit.json'),before['focused'])
        context=capture_context(reader,2)
        command=make_command(context,2,list(IDS))
        if args.execute:
            require(args.command_file is not None,'Execution requires the separately authorized fixed command file')
            received=load_json(args.command_file)
            require(received==command,'Fixed command or current authoritative context does not match')
        preflight=validate_reward(command,context,2)
        require(preflight['viewer_force_id']==12 and preflight['authorized_force_id']==2,'Actor/viewer mismatch')
        save(run/'before.json',before);save(run/'preflight.json',preflight)
        if args.execute:
            require(before==load_json(Path(dry['directory'])/'before.json'),'State differs from successful dry run')
        base=reader.memory.base;image=(ROOT/'game-runtime-image.bin').read_bytes()
        for a,z in QUERY_RANGES+RANGES:
            require(reader.memory.read(base+a,z-a)==image[a:z],f'Native body/constants mismatch at {a:X}')
        slot=base+0x12CC4A8+0x28
        require(int.from_bytes(reader.memory.read(slot,8),'little')==base+0x3F9B00,'Update slot already changed')
        dll=run/f'second-force-reward-{run.name}.dll';shutil.copyfile(binary,dll)
        pe=pefile.PE(str(dll));exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name};pe.close()
        require(set(exports)=={'InstallRewardProbe','CancelRewardProbe','RewardProbeReport','RewardExecutionReport'},'Unexpected DLL exports')
        if args.execute:
            with (ROOT/'second-force-reward-once.json').open('x',encoding='utf-8') as stream:
                json.dump({'directory':str(run),'stage':'EXECUTION_ATTEMPT_RESERVED','automatic_retry_allowed':False,'officers':IDS},stream)
        save(run/'metadata.json',{'pid':reader.pid,'base':hex(base),'dll_sha256':binary_sha,'execute':args.execute,
                                 'restore_method':'game native load34 UI','automatic_retry_allowed':False})
        api=ProcessAPI(reader);api.call_adapter(api.load_library_address(),str(dll).encode('utf-16le')+b'\0\0')
        modules=[b for b,p in api.modules() if str(p).lower()==str(dll).lower()];require(len(modules)==1,'Pilot DLL not found')
        module=modules[0];report_address=module+exports['RewardProbeReport'];cancel_address=module+exports['CancelRewardProbe']
        def report():
            data=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
            require(data['magic']==0x1414D001 and data['version']==1,'Pilot report identity mismatch');return data
        code=api.call_adapter(module+exports['InstallRewardProbe'],struct.pack('<QII',0x53414E1452464231,1,int(args.execute)))
        deadline=time.monotonic()+8;r=report()
        while time.monotonic()<deadline and (r['status']<3 or r['active_callbacks']):
            time.sleep(.05);r=report()
        if r['status']==1:api.call_adapter(cancel_address);r=report()
        execution=dict(zip(EX_NAMES,struct.unpack('<18I',reader.memory.read(module+exports['RewardExecutionReport'],72))))
        save(run/'adapter-report.json',r);save(run/'execution-report.json',execution)
        after=capture(reader);save(run/'after.json',after);save(run/'changes.json',diff_records(before,after))
        require(code==0 and r['status']==(4 if args.execute else 3),f'Pilot failed/rejected: {r}; execution={execution}')
        require(execution['magic']==0x1414D002 and execution['version']==1 and execution['execute']==int(args.execute),'Execution report identity mismatch')
        require(r['slot_restored']==r['protection_restored']==r['handle_cleared']==r['owned_slot_cleared']==1 and r['active_callbacks']==0,'Cleanup incomplete')
        require(int.from_bytes(reader.memory.read(slot,8),'little')==base+0x3F9B00,'Actual slot not restored')
        require(r['caller']==base+0x50B785 and r['executor_thread']!=r['installer_thread'],'Wrong native callback context')
        require(r['ctor_calls']==r['dtor_calls']==1 and r['append_calls']==3 and execution['predicate_calls']==6,'Unexpected native call counts')
        require(execution['submit_calls']==int(args.execute),'Unexpected reward handler count')
        if args.execute:require(execution['submit_returned']==execution['submit_result']==execution['postconditions']==1,'Native execution result uncertain')
        comparison=effects(before,after,args.execute);save(run/'comparison.json',comparison);check_checkpoint(CHECKPOINT)
        result={'result':'PASS','directory':str(run),'dll_sha256':binary_sha,'executed':args.execute,
                'stage':'NATIVE_SECOND_FORCE_REWARD_EXECUTED_RESTORE_PENDING' if args.execute else 'NATIVE_SECOND_FORCE_REWARD_DRY_PASS',
                'viewer_force_id':12,'command_force_id':2,'command':command,
                'fixture_tests':len(fixtures),'adapter':r,'execution':execution,'effects':comparison,
                'two_client_multiplayer':False,'domestic_network_execution_enabled':False,'ui_refresh_verified':False,
                'checkpoint34_unchanged':True,'restore_verified':False,'record_scope':before['record_scope'],
                'inert_module_remains_loaded_until_game_exit':True,'automatic_retry_allowed':False}
        save(run/'result.json',result)
        save(ROOT/('second-force-reward-live-latest.json' if args.execute else 'second-force-reward-dry-latest.json'),result)
        print(json.dumps(result,ensure_ascii=True))
    except Exception as error:
        failure={'result':'FAIL','error':str(error),'automatic_retry_allowed':False}
        if api and report_address and cancel_address:
            try:
                r=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
                if r['status']==1:api.call_adapter(cancel_address)
                failure['adapter']=dict(zip(NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
            except Exception as e:failure['cleanup_error']=str(e)
        save(run/'failure.json',failure);raise
    finally:
        if api:api.close()
        reader.close()

if __name__=='__main__':main()
